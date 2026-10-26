"""Bounded question inputs. Private scoring payloads are never student DTOs."""
import hashlib
import json
import unicodedata
from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domains.content.schemas import SourceMetadata

ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def clean_text(value: str) -> str:
    value = value.strip()
    if not value or any(ord(char) < 32 and char not in "\n\t" for char in value):
        raise ValueError("须为非空文字，不能含控制字符")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError("须为有效Unicode文字") from None
    return value


def canonical_bytes(value) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def fingerprint(value) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


class Provenance(SourceMetadata):
    origin: Literal["upload", "open_seed", "derived"] = "derived"
    source_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    teaching_reuse_allowed: bool = Field(default=False, strict=True)

    @field_validator("author", "license", "source_version")
    @classmethod
    def valid_text(cls, value):
        return clean_text(value) if value is not None else None

    @field_validator("acquired_date")
    @classmethod
    def real_date(cls, value):
        if value is not None:
            if date.fromisoformat(value).isoformat() != value:
                raise ValueError("获取日期须为YYYY-MM-DD")
        return value


class Option(StrictModel):
    id: str = Field(pattern=ID_PATTERN)
    label: str = Field(min_length=1, max_length=1000)

    _label = field_validator("label")(clean_text)


class SourcePointer(StrictModel):
    material_version_id: UUID
    chunk_id: UUID | None = None


class QuestionPayload(StrictModel):
    kind: Literal["single", "multiple", "true_false", "scenario"]
    stem: str = Field(min_length=1, max_length=4000)
    options: tuple[Option, ...] = Field(min_length=2, max_length=8)
    answer_ids: tuple[str, ...] = Field(min_length=1, max_length=8)
    explanation: str = Field(min_length=1, max_length=8000)
    knowledge_points: tuple[str, ...] = Field(min_length=1, max_length=10)
    difficulty: Literal["easy", "medium", "hard"]

    _text = field_validator("stem", "explanation")(clean_text)

    @field_validator("knowledge_points")
    @classmethod
    def points(cls, value):
        result = tuple(clean_text(item) for item in value)
        if any(len(item) > 100 for item in result) or len(set(result)) != len(result):
            raise ValueError("知识点不能重复且每项不超过100字符")
        return result

    @model_validator(mode="after")
    def valid_answers(self):
        ids = [option.id for option in self.options]
        labels = [unicodedata.normalize("NFKC", option.label).casefold() for option in self.options]
        if len(set(ids)) != len(ids) or len(set(labels)) != len(labels):
            raise ValueError("选项ID和文字不能重复")
        if len(set(self.answer_ids)) != len(self.answer_ids) or not set(self.answer_ids) <= set(ids):
            raise ValueError("答案须唯一且指向真实选项")
        if self.kind == "multiple":
            if len(self.answer_ids) < 2:
                raise ValueError("多选题须至少两个正确选项")
        elif len(self.answer_ids) != 1:
            raise ValueError("此题型须恰有一个正确选项")
        if self.kind == "true_false" and set(ids) != {"true", "false"}:
            raise ValueError("判断题只使用true/false两个固定选项")
        if len(canonical_bytes(self)) > 32768:
            raise ValueError("单题规范化载荷不能超过32KiB")
        return self

    def duplicate_hash(self):
        def normalize(text):
            return " ".join(unicodedata.normalize("NFKC", text).casefold().split())
        # Detect conflicting answer keys for the same prompt/options rather than treating them as new questions.
        return fingerprint({"kind": self.kind, "stem": normalize(self.stem),
                            "options": sorted(normalize(option.label) for option in self.options)})


class DraftContent(StrictModel):
    payload: QuestionPayload
    sources: tuple[SourcePointer, ...] = Field(default=(), max_length=20)
    provenance: Provenance = Field(default_factory=Provenance)

    @model_validator(mode="after")
    def unique_sources(self):
        refs = [(item.material_version_id, item.chunk_id) for item in self.sources]
        if len(set(refs)) != len(refs):
            raise ValueError("来源不能重复")
        return self


class QuestionCreate(DraftContent):
    library_id: UUID


class QuestionChange(DraftContent):
    revision: int = Field(ge=1, strict=True)


class Revision(StrictModel):
    revision: int = Field(ge=1, strict=True)


class ParentChange(Revision):
    retired: bool = Field(strict=True)


class Submit(Revision):
    target_library_id: UUID
    authorization_statement: str = Field(min_length=1, max_length=2000)

    _statement = field_validator("authorization_statement")(clean_text)


class Decision(Revision):
    decision: Literal["approved", "rejected"]
    reason: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def reject_reason(self):
        if self.decision == "rejected" and (not self.reason or not self.reason.strip()):
            raise ValueError("拒绝须说明原因")
        return self


class CopyOrReference(StrictModel):
    source_version_id: UUID
    target_library_id: UUID
    authorization_statement: str = Field(min_length=1, max_length=2000)

    _statement = field_validator("authorization_statement")(clean_text)
