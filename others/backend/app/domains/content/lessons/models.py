"""Immutable lesson/scene candidates, separate from B2 attempts and progress."""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, CheckConstraint, Column, DateTime, ForeignKeyConstraint, Index, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.domains.content.models import timestamp


class SceneAsset(SQLModel, table=True):
    __tablename__ = "content_scene_asset"
    __table_args__ = (
        CheckConstraint("retained_bytes >= 0 AND octet_length(svg) <= 262144", name="ck_scene_asset_budget"),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    library_id: UUID = Field(foreign_key="content_library.id", index=True)
    svg: str = Field(sa_column=Column(Text, nullable=False))
    content_hash: str = Field(max_length=64)
    provenance: dict = Field(sa_column=Column(JSONB, nullable=False))
    view_box: list = Field(sa_column=Column(JSONB, nullable=False))
    creator_id: UUID = Field(foreign_key="app_user.id")
    created_at: datetime = timestamp()
    retained_bytes: int = Field(default=0, sa_column=Column(BigInteger, nullable=False))


class Lesson(SQLModel, table=True):
    __tablename__ = "content_lesson"
    __table_args__ = (CheckConstraint("revision > 0", name="ck_lesson_revision"),)
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    library_id: UUID = Field(foreign_key="content_library.id", index=True)
    creator_id: UUID = Field(foreign_key="app_user.id")
    revision: int = 1
    retired: bool = False
    created_at: datetime = timestamp()


class LessonDraft(SQLModel, table=True):
    __tablename__ = "content_lesson_draft"
    __table_args__ = (CheckConstraint("revision > 0 AND retained_bytes >= 0", name="ck_lesson_draft_budget"),)
    lesson_id: UUID = Field(primary_key=True, foreign_key="content_lesson.id")
    revision: int = 1
    content: dict = Field(sa_column=Column(JSONB, nullable=False))
    scene_asset_id: UUID = Field(foreign_key="content_scene_asset.id")
    copied_from_version_id: UUID | None = Field(default=None, foreign_key="content_lesson_version.id")
    updated_by: UUID = Field(foreign_key="app_user.id")
    updated_at: datetime = timestamp()
    retained_bytes: int = Field(default=0, sa_column=Column(BigInteger, nullable=False))


class LessonVersion(SQLModel, table=True):
    __tablename__ = "content_lesson_version"
    __table_args__ = (
        UniqueConstraint("lesson_id", "version_no", name="uq_lesson_version_number"),
        UniqueConstraint("lesson_id", "draft_revision", name="uq_lesson_frozen_revision"),
        CheckConstraint("version_no > 0 AND draft_revision > 0 AND retained_bytes >= 0", name="ck_lesson_version_budget"),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    lesson_id: UUID = Field(foreign_key="content_lesson.id", index=True)
    version_no: int
    draft_revision: int
    content: dict = Field(sa_column=Column(JSONB, nullable=False))
    scene_asset_id: UUID = Field(foreign_key="content_scene_asset.id")
    copied_from_version_id: UUID | None = Field(default=None, foreign_key="content_lesson_version.id")
    payload_hash: str = Field(max_length=64)
    created_by: UUID = Field(foreign_key="app_user.id")
    created_at: datetime = timestamp()
    retained_bytes: int = Field(default=0, sa_column=Column(BigInteger, nullable=False))


class LessonDraftSource(SQLModel, table=True):
    __tablename__ = "content_lesson_draft_source"
    __table_args__ = (UniqueConstraint("lesson_id", "activity_id", "material_version_id", "chunk_id",
                                     name="uq_lesson_draft_source", postgresql_nulls_not_distinct=True),)
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    lesson_id: UUID = Field(foreign_key="content_lesson_draft.lesson_id", index=True)
    activity_id: str = Field(max_length=64)
    material_version_id: UUID = Field(foreign_key="content_material_version.id")
    chunk_id: UUID | None = Field(default=None, foreign_key="content_source_chunk.id")


class LessonSource(SQLModel, table=True):
    __tablename__ = "content_lesson_source"
    __table_args__ = (UniqueConstraint("lesson_version_id", "activity_id", "material_version_id", "chunk_id",
                                     name="uq_lesson_source", postgresql_nulls_not_distinct=True),)
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    lesson_version_id: UUID = Field(foreign_key="content_lesson_version.id", index=True)
    activity_id: str = Field(max_length=64)
    material_version_id: UUID = Field(foreign_key="content_material_version.id")
    chunk_id: UUID | None = Field(default=None, foreign_key="content_source_chunk.id")
    locator: dict = Field(sa_column=Column(JSONB, nullable=False))


class LessonDraftQuestion(SQLModel, table=True):
    __tablename__ = "content_lesson_draft_question"
    __table_args__ = (UniqueConstraint("lesson_id", "activity_id", name="uq_lesson_draft_question"),)
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    lesson_id: UUID = Field(foreign_key="content_lesson_draft.lesson_id", index=True)
    activity_id: str = Field(max_length=64)
    question_version_id: UUID = Field(foreign_key="content_question_version.id")


class LessonQuestion(SQLModel, table=True):
    __tablename__ = "content_lesson_question"
    __table_args__ = (UniqueConstraint("lesson_version_id", "activity_id", name="uq_lesson_question"),)
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    lesson_version_id: UUID = Field(foreign_key="content_lesson_version.id", index=True)
    activity_id: str = Field(max_length=64)
    question_version_id: UUID = Field(foreign_key="content_question_version.id")


class LessonDraftQuestionOrigin(SQLModel, table=True):
    __tablename__ = "content_lesson_draft_question_origin"
    __table_args__ = (UniqueConstraint("lesson_id", "activity_id", "question_version_id", name="uq_lesson_draft_question_origin"),)
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    lesson_id: UUID = Field(foreign_key="content_lesson_draft.lesson_id", index=True)
    activity_id: str = Field(max_length=64)
    question_version_id: UUID = Field(foreign_key="content_question_version.id")


class LessonQuestionOrigin(SQLModel, table=True):
    __tablename__ = "content_lesson_question_origin"
    __table_args__ = (UniqueConstraint("lesson_version_id", "activity_id", "question_version_id", name="uq_lesson_question_origin"),)
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    lesson_version_id: UUID = Field(foreign_key="content_lesson_version.id", index=True)
    activity_id: str = Field(max_length=64)
    question_version_id: UUID = Field(foreign_key="content_question_version.id")


class LessonReview(SQLModel, table=True):
    __tablename__ = "content_lesson_review"
    __table_args__ = (
        CheckConstraint("state IN ('submitted','approved','rejected')", name="ck_lesson_review_state"),
        UniqueConstraint("id", "version_id", "target_library_id", name="uq_lesson_review_binding"),
        Index("ix_lesson_review_queue", "target_library_id", "state", "submitted_at", "id"),
        Index("uq_lesson_review_pending", "version_id", "target_library_id", unique=True,
              postgresql_where=text("state = 'submitted'")),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    version_id: UUID = Field(foreign_key="content_lesson_version.id")
    target_library_id: UUID = Field(foreign_key="content_library.id")
    state: str = Field(default="submitted", max_length=12)
    submitter_id: UUID = Field(foreign_key="app_user.id")
    reviewer_id: UUID | None = Field(default=None, foreign_key="app_user.id")
    authorization_statement: str = Field(max_length=2000)
    reason: str | None = Field(default=None, max_length=2000)
    revision: int = 1
    submitted_at: datetime = timestamp()
    decided_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))


class LessonPublication(SQLModel, table=True):
    __tablename__ = "content_lesson_publication"
    __table_args__ = (
        ForeignKeyConstraint(["review_id", "version_id", "target_library_id"],
                             ["content_lesson_review.id", "content_lesson_review.version_id",
                              "content_lesson_review.target_library_id"], name="fk_lesson_publication_review"),
        UniqueConstraint("review_id", name="uq_lesson_publication_review"),
        Index("ix_lesson_publication_target", "target_library_id", "active", "version_id"),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    review_id: UUID
    version_id: UUID = Field(foreign_key="content_lesson_version.id")
    target_library_id: UUID = Field(foreign_key="content_library.id")
    active: bool = True
    published_by: UUID = Field(foreign_key="app_user.id")
    published_at: datetime = timestamp()
    retired_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    revision: int = 1
