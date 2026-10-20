"""A-owned AI configuration primitives. C owns school persistence, admin operations and inference."""
import base64
from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator

from app.core.config import ROOT


class ProviderNotConfigured(RuntimeError):
    pass


class ProviderSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    protocol: Literal["openai-chat"] = "openai-chat"
    base_url: str
    model: str = Field(min_length=1, max_length=120)
    timeout_seconds: int = Field(default=45, ge=1, le=120)
    max_output_tokens: int = Field(default=2048, ge=1, le=16384)

    @field_validator("base_url")
    @classmethod
    def endpoint(cls, value):
        parts = urlsplit(value)
        if (parts.scheme != "https" or not parts.hostname or parts.username or parts.password
                or parts.query or parts.fragment):
            raise ValueError("AI 接口须为不含凭据、查询参数或片段的 HTTPS 地址")
        if parts.port is not None and not 1 <= parts.port <= 65535:
            raise ValueError("无效接口端口")
        return value.rstrip("/")


class EncryptedProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    revision: UUID
    spec: ProviderSpec
    ciphertext: str = Field(repr=False)

    def public_status(self) -> dict:
        return {"revision": str(self.revision), "spec": self.spec.model_dump(),
                "key_present": bool(self.ciphertext), "key_mask": "********" if self.ciphertext else ""}


class SchoolProviderSelection(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    school_id: UUID
    revision: UUID
    mode: Literal["unconfigured", "platform", "school"] = "unconfigured"
    profile: EncryptedProfile | None = None
    tested_revision: UUID | None = None
    enabled: bool = False

    @model_validator(mode="after")
    def complete_profile(self):
        if (self.mode == "school") != (self.profile is not None):
            raise ValueError("本校模式必须绑定完整独立配置，平台模式不得混入本校地址或密钥")
        if self.profile and self.profile.revision != self.revision:
            raise ValueError("配置版本不一致")
        if self.enabled and (self.mode == "unconfigured" or self.tested_revision != self.revision):
            raise ValueError("必须先由服务端测试当前版本，再启用")
        return self


@dataclass(frozen=True)
class ProviderSnapshot:
    revision: str
    source: Literal["platform", "school"]
    spec: ProviderSpec
    api_key: SecretStr


def shared_root() -> Path:
    return Path(os.environ.get("LABCONNECT_SHARED_ROOT", str(ROOT)))


def master_key() -> bytes:
    path = shared_root() / "others/runtime/ai-master.key"
    try:
        key = path.read_bytes()
    except FileNotFoundError as error:
        raise ProviderNotConfigured("服务端加密主密钥尚未配置") from error
    if len(key) != 32:
        raise ProviderNotConfigured("服务端加密主密钥格式错误")
    return key


def seal_key(api_key: str, *, scope: str, revision: UUID, key: bytes) -> str:
    if not api_key.strip():
        raise ValueError("接口密钥不能为空")
    nonce = os.urandom(12)
    aad = f"labconnect/ai/{scope}/{revision}".encode()
    return "v1:" + base64.urlsafe_b64encode(nonce + AESGCM(key).encrypt(nonce, api_key.encode(), aad)).decode()


def open_key(ciphertext: str, *, scope: str, revision: UUID, key: bytes) -> SecretStr:
    if not ciphertext.startswith("v1:"):
        raise ValueError("不支持的密钥封装版本")
    raw = base64.b64decode(ciphertext[3:], altchars=b"-_", validate=True)
    aad = f"labconnect/ai/{scope}/{revision}".encode()
    return SecretStr(AESGCM(key).decrypt(raw[:12], raw[12:], aad).decode())


def platform_profile() -> EncryptedProfile:
    try:
        raw = (shared_root() / "others/runtime/platform-ai.json").read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise ProviderNotConfigured("平台默认 AI 尚未配置") from error
    return EncryptedProfile.model_validate_json(raw)


def resolve_provider(school_id: UUID, selection: SchoolProviderSelection, *, key: bytes | None = None,
                     platform: EncryptedProfile | None = None) -> ProviderSnapshot:
    """Capture once per new job. Never merge a school endpoint with platform credentials."""
    if selection.school_id != school_id:
        raise PermissionError("无权使用其他学校的 AI 配置")
    if not selection.enabled or selection.tested_revision != selection.revision or selection.mode == "unconfigured":
        raise ProviderNotConfigured("学校尚未选择并启用 AI 接口")
    profile = selection.profile if selection.mode == "school" else (platform or platform_profile())
    scope = str(school_id) if selection.mode == "school" else "platform"
    secret = open_key(profile.ciphertext, scope=scope, revision=profile.revision, key=key or master_key())
    return ProviderSnapshot(str(profile.revision), selection.mode, profile.spec, secret)


def can_manage_school_provider(identity, school_id: UUID) -> bool:
    from app.domains.core.models import Role
    return identity.has(Role.SCHOOL_ADMIN) and identity.user.school_id == school_id


def store_platform_profile(api_key: str, spec: ProviderSpec, revision: UUID) -> None:
    """Local A setup only; no HTTP mutation endpoint. C must persist audited school settings separately."""
    directory = shared_root() / "others/runtime"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "ai-master.key"
    if not path.exists():
        with path.open("xb") as handle:
            handle.write(os.urandom(32))
    profile = EncryptedProfile(revision=revision, spec=spec,
        ciphertext=seal_key(api_key, scope="platform", revision=revision, key=master_key()))
    temporary = directory / ("platform-ai-" + str(revision) + ".tmp")
    temporary.write_text(json.dumps(profile.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")
    temporary.replace(directory / "platform-ai.json")
