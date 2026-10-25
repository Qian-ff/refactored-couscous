"""Explicit staff-only projections; students never receive QuestionPayload."""
from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.domains.content.questions.schemas import Provenance, QuestionPayload, StrictModel


class Page[T](StrictModel):
    items: tuple[T, ...]
    total: int
    offset: int
    limit: int


class SourceView(StrictModel):
    material_id: UUID
    material_version_id: UUID
    chunk_id: UUID | None = None
    locator: dict


class DraftView(StrictModel):
    question_id: UUID
    library_id: UUID
    revision: int
    parent_revision: int
    retired: bool
    can_edit: bool
    payload: QuestionPayload
    provenance: Provenance
    sources: tuple[SourceView, ...]
    updated_at: datetime


class VersionView(StrictModel):
    question_id: UUID
    version_id: UUID
    library_id: UUID
    version_no: int
    payload: QuestionPayload
    provenance: Provenance
    sources: tuple[SourceView, ...]
    created_at: datetime


class BankView(StrictModel):
    id: UUID
    title: str
    scope: str
    audience: str
    active: bool
    revision: int
    can_submit: bool
    can_review: bool


class ReviewView(StrictModel):
    id: UUID
    version_id: UUID
    target_library_id: UUID
    state: str
    revision: int
    authorization_statement: str
    reason: str | None
    submitted_at: datetime
    decided_at: datetime | None


class PublicationView(StrictModel):
    id: UUID
    version_id: UUID
    target_library_id: UUID
    active: bool
    revision: int
    published_at: datetime
    retired_at: datetime | None


class CommandResult(StrictModel):
    question_id: UUID | None = None
    lesson_id: UUID | None = None
    version_id: UUID | None = None
    review_id: UUID | None = None
    publication_id: UUID | None = None
    asset_id: UUID | None = None
    revision: int | None = Field(default=None, ge=1)
    state: str | None = None
    retired: bool | None = None
    active: bool | None = None
    draft_discarded: bool | None = None
