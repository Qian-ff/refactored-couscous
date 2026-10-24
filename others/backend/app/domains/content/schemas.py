"""Validated C-02 inputs; SQLModel persistence objects are never public DTOs."""
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

Scope = Literal["platform_public", "school", "college", "catalog", "course"]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceMetadata(Input):
    origin: Literal["upload", "open_seed", "derived"] = "upload"
    author: str | None = Field(default=None, max_length=200)
    original_url: str | None = Field(default=None, max_length=1000)
    license: str | None = Field(default=None, max_length=200)
    license_url: str | None = Field(default=None, max_length=1000)
    acquired_date: str | None = Field(default=None, max_length=30)
    source_version: str | None = Field(default=None, max_length=200)
    adapted: bool = False
    public_reuse_allowed: bool = False

    @field_validator("original_url", "license_url")
    @classmethod
    def safe_url(cls, value):
        if value is not None:
            from urllib.parse import urlsplit
            parsed = urlsplit(value)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError("来源链接须为不含凭据的HTTPS地址")
        return value


class LibraryCreate(Input):
    scope: Scope
    parent_id: UUID | None = None
    title: str = Field(min_length=1, max_length=200)
    audience: Literal["all", "staff"] = "staff"

    @field_validator("title")
    @classmethod
    def nonblank(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("名称不能为空")
        return value


class LibraryChange(Input):
    revision: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    active: bool | None = None

    @field_validator("title")
    @classmethod
    def nonblank(cls, value):
        return LibraryCreate.nonblank(value) if value is not None else None


class TextMaterialCreate(Input):
    library_id: UUID
    material_id: UUID | None = None
    title: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=1048576)
    source_metadata: SourceMetadata = Field(default_factory=SourceMetadata)

    @field_validator("title")
    @classmethod
    def nonblank(cls, value):
        return LibraryCreate.nonblank(value)

    @field_validator("text")
    @classmethod
    def bounded_text(cls, value):
        if not value.strip() or "\x00" in value or len(value.encode("utf-8")) > 1048576:
            raise ValueError("知识点应为非空文字，UTF-8字节不超过1MiB")
        return value


class ReviewSubmit(Input):
    version_id: UUID
    target_library_id: UUID
    authorization_statement: str = Field(min_length=1, max_length=2000)

    @field_validator("authorization_statement")
    @classmethod
    def nonblank(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("须说明整份原件的使用授权")
        return value


class ReviewDecision(Input):
    revision: int = Field(ge=1)
    decision: Literal["approved", "rejected"]
    reason: str | None = Field(default=None, max_length=1000)
    warning_hash: str | None = Field(default=None, pattern="^[0-9a-f]{64}$")
    warnings_acknowledged: bool = False
    original_authorized: bool = False


class RevisionInput(Input):
    revision: int = Field(ge=1)


class PublicationCreate(RevisionInput):
    review_id: UUID


class MaterialChange(Input):
    revision: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    retired: bool | None = None

    @field_validator("title")
    @classmethod
    def nonblank(cls, value):
        return LibraryCreate.nonblank(value) if value is not None else None


class UploadCreate(Input):
    library_id: UUID
    material_id: UUID | None = None
    title: str = Field(min_length=1, max_length=200)
    original_name: str = Field(min_length=1, max_length=240)
    format: Literal["pdf", "pptx", "docx", "txt"]
    encoding: Literal["utf-8", "gb18030"] = "utf-8"
    expected_bytes: int = Field(gt=0, le=20971520)
    expected_hash: str = Field(pattern="^[0-9a-f]{64}$")
    source_metadata: SourceMetadata = Field(default_factory=SourceMetadata)

    @field_validator("title")
    @classmethod
    def title_nonblank(cls, value):
        return LibraryCreate.nonblank(value)

    @field_validator("original_name")
    @classmethod
    def safe_filename(cls, value):
        if any(ord(c) < 32 or c in '/\\:' for c in value) or value in {".", ".."}:
            raise ValueError("文件名不可含路径或控制字符")
        return value

    @classmethod
    def validate_file(cls, request):
        if request.original_name.rsplit(".", 1)[-1].lower() != request.format:
            raise ValueError("文件扩展名与格式不一致")
        if request.format == "txt" and request.expected_bytes > 1048576:
            raise ValueError("TXT文件最多1MiB")
        return request

    def model_post_init(self, _context):
        self.validate_file(self)
