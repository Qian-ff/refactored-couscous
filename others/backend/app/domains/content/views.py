"""Public white-list projections; never serialize the persistence models directly."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.domains.content.schemas import Scope, SourceMetadata


class Page[T](BaseModel):
    items: list[T]
    total: int
    offset: int
    limit: int


class LibraryView(BaseModel):
    id: UUID
    title: str
    scope: Scope
    audience: Literal["all", "staff"]
    revision: int
    active: bool
    can_submit: bool
    can_review: bool
    can_manage: bool = False


class SubmitTarget(BaseModel):
    id: UUID
    title: str
    scope: Scope
    can_submit: Literal[True] = True


class ReviewView(BaseModel):
    id: UUID
    version_id: UUID
    target_library_id: UUID
    state: str
    revision: int
    warning_hash: str
    original_authorized: bool
    authorization_statement: str
    reason: str | None
    submitted_at: datetime
    decided_at: datetime | None
    can_decide: bool = False
    can_publish: bool = False


class PublicationView(BaseModel):
    id: UUID
    version_id: UUID
    target_library_id: UUID
    review_id: UUID
    active: bool
    revision: int
    published_at: datetime
    retired_at: datetime | None
    can_retire: bool = False


class VersionActions(BaseModel):
    edit_material: bool = False
    retire_material: bool = False
    create_version: bool = False
    submit_review: bool = False
    preview: bool = False
    download: bool = False


class TargetBinding(BaseModel):
    target_library_id: UUID
    review: ReviewView | None = None
    active_publication: PublicationView | None = None


class SearchMatch(BaseModel):
    kind: Literal["chunk", "input_text", "title", "filename"]
    snippet: str = Field(max_length=240)
    chunk_id: UUID | None = None
    ordinal: int | None = None
    locator: dict | None = None


class VersionView(BaseModel):
    material_id: UUID
    version_id: UUID
    library_id: UUID
    title: str
    version_no: int
    input_kind: Literal["file", "text"]
    extraction_state: Literal["queued", "running", "succeeded", "failed", "canceled"]
    original_name: str | None
    file_bytes: int | None
    content_hash: str
    parser_version: str | None
    created_at: datetime
    warnings: list[str]
    warning_hash: str
    source_metadata: SourceMetadata | None = None
    material_revision: int | None = None
    actions: VersionActions = Field(default_factory=VersionActions)
    binding: TargetBinding | None = None
    file_type: Literal["pdf", "pptx", "docx", "txt", "text"] | None = None
    course_id: UUID | None = None
    course_code: str | None = None
    course_title: str | None = None
    search_match: SearchMatch | None = None


class ChunkView(BaseModel):
    id: UUID
    ordinal: int
    locator: dict
    text: str
    text_hash: str


class ChunkPage(BaseModel):
    version_id: UUID
    items: list[ChunkView]
    total: int
    next_ordinal: int | None


class CommandResult(BaseModel):
    library_id: UUID | None = None
    material_id: UUID | None = None
    version_id: UUID | None = None
    upload_id: UUID | None = None
    review_id: UUID | None = None
    publication_id: UUID | None = None
    job_id: UUID | None = None


class UploadView(BaseModel):
    upload_id: UUID
    state: str
    expected_bytes: int
    expires_at: datetime
    error_code: str | None
    version_id: UUID | None = None
    material_id: UUID | None = None


class JobView(BaseModel):
    job_id: UUID
    version_id: UUID
    state: str
    stage: str
    error_code: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class Capabilities(BaseModel):
    parser_available: bool
    storage_available: bool
    max_file_bytes: int = 20971520
    max_text_bytes: int = 1048576
    formats: list[str] = Field(default_factory=lambda: ["pdf", "pptx", "docx", "txt"])
