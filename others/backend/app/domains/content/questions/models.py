"""C1 candidate tables. A registers and migrates these; importing never creates tables."""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, CheckConstraint, Column, DateTime, ForeignKeyConstraint, Index, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.domains.content.models import timestamp


class Question(SQLModel, table=True):
    __tablename__ = "content_question"
    __table_args__ = (CheckConstraint("revision > 0", name="ck_question_revision"),)
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    library_id: UUID = Field(foreign_key="content_library.id", index=True)
    creator_id: UUID = Field(foreign_key="app_user.id")
    revision: int = 1
    retired: bool = False
    created_at: datetime = timestamp()


class QuestionDraft(SQLModel, table=True):
    __tablename__ = "content_question_draft"
    __table_args__ = (
        CheckConstraint("revision > 0 AND retained_bytes >= 0", name="ck_question_draft_budget"),
        Index("ix_question_draft_duplicate", "duplicate_hash"),
    )
    question_id: UUID = Field(primary_key=True, foreign_key="content_question.id")
    revision: int = 1
    payload: dict = Field(sa_column=Column(JSONB, nullable=False))
    provenance: dict = Field(sa_column=Column(JSONB, nullable=False))
    copied_from_version_id: UUID | None = Field(default=None, foreign_key="content_question_version.id")
    duplicate_hash: str = Field(max_length=64)
    updated_by: UUID = Field(foreign_key="app_user.id")
    updated_at: datetime = timestamp()
    retained_bytes: int = Field(default=0, sa_column=Column(BigInteger, nullable=False))


class QuestionDraftSource(SQLModel, table=True):
    __tablename__ = "content_question_draft_source"
    __table_args__ = (UniqueConstraint("question_id", "material_version_id", "chunk_id",
                                     name="uq_question_draft_source", postgresql_nulls_not_distinct=True),)
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    question_id: UUID = Field(foreign_key="content_question_draft.question_id", index=True)
    material_version_id: UUID = Field(foreign_key="content_material_version.id")
    chunk_id: UUID | None = Field(default=None, foreign_key="content_source_chunk.id")


class QuestionVersion(SQLModel, table=True):
    __tablename__ = "content_question_version"
    __table_args__ = (
        UniqueConstraint("question_id", "version_no", name="uq_question_version_number"),
        UniqueConstraint("question_id", "draft_revision", name="uq_question_frozen_revision"),
        CheckConstraint("version_no > 0 AND draft_revision > 0 AND retained_bytes >= 0", name="ck_question_version_budget"),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    question_id: UUID = Field(foreign_key="content_question.id", index=True)
    version_no: int
    draft_revision: int
    payload: dict = Field(sa_column=Column(JSONB, nullable=False))
    provenance: dict = Field(sa_column=Column(JSONB, nullable=False))
    copied_from_version_id: UUID | None = Field(default=None, foreign_key="content_question_version.id")
    payload_hash: str = Field(max_length=64)
    created_by: UUID = Field(foreign_key="app_user.id")
    created_at: datetime = timestamp()
    retained_bytes: int = Field(default=0, sa_column=Column(BigInteger, nullable=False))


class QuestionSource(SQLModel, table=True):
    __tablename__ = "content_question_source"
    __table_args__ = (UniqueConstraint("question_version_id", "material_version_id", "chunk_id",
                                     name="uq_question_source", postgresql_nulls_not_distinct=True),)
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    question_version_id: UUID = Field(foreign_key="content_question_version.id", index=True)
    material_version_id: UUID = Field(foreign_key="content_material_version.id")
    chunk_id: UUID | None = Field(default=None, foreign_key="content_source_chunk.id")
    locator: dict = Field(sa_column=Column(JSONB, nullable=False))


class QuestionReview(SQLModel, table=True):
    __tablename__ = "content_question_review"
    __table_args__ = (
        CheckConstraint("state IN ('submitted','approved','rejected')", name="ck_question_review_state"),
        UniqueConstraint("id", "version_id", "target_library_id", name="uq_question_review_binding"),
        Index("ix_question_review_queue", "target_library_id", "state", "submitted_at", "id"),
        Index("uq_question_review_pending", "version_id", "target_library_id", unique=True,
              postgresql_where=text("state = 'submitted'")),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    version_id: UUID = Field(foreign_key="content_question_version.id")
    target_library_id: UUID = Field(foreign_key="content_library.id")
    state: str = Field(default="submitted", max_length=12)
    submitter_id: UUID = Field(foreign_key="app_user.id")
    reviewer_id: UUID | None = Field(default=None, foreign_key="app_user.id")
    authorization_statement: str = Field(max_length=2000)
    reason: str | None = Field(default=None, max_length=2000)
    revision: int = 1
    submitted_at: datetime = timestamp()
    decided_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))


class QuestionPublication(SQLModel, table=True):
    __tablename__ = "content_question_publication"
    __table_args__ = (
        ForeignKeyConstraint(["review_id", "version_id", "target_library_id"],
                             ["content_question_review.id", "content_question_review.version_id",
                              "content_question_review.target_library_id"], name="fk_question_publication_review"),
        UniqueConstraint("review_id", name="uq_question_publication_review"),
        Index("ix_question_publication_target", "target_library_id", "active", "version_id"),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    review_id: UUID
    version_id: UUID = Field(foreign_key="content_question_version.id")
    target_library_id: UUID = Field(foreign_key="content_library.id")
    active: bool = True
    published_by: UUID = Field(foreign_key="app_user.id")
    published_at: datetime = timestamp()
    retired_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    revision: int = 1


class ImportBatch(SQLModel, table=True):
    __tablename__ = "content_question_import_batch"
    __table_args__ = (
        CheckConstraint("state IN ('pending','invalid','ready','committed','expired','canceled','failed')", name="ck_question_batch_state"),
        CheckConstraint("work_role IN ('teacher','administrator')", name="ck_question_batch_role"),
        CheckConstraint("revision > 0 AND retained_bytes >= 0 AND row_count BETWEEN 0 AND 1000", name="ck_question_batch_budget"),
        ForeignKeyConstraint(["login_session_id", "actor_id"], ["login_session.id", "login_session.user_id"],
                             name="fk_question_batch_session_owner"),
        Index("ix_question_batch_actor", "actor_id", "work_role", "created_at", "id"),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    library_id: UUID = Field(foreign_key="content_library.id")
    actor_id: UUID = Field(foreign_key="app_user.id")
    login_session_id: UUID = Field(foreign_key="login_session.id")
    work_role: str = Field(max_length=20)
    input_hash: str = Field(max_length=64)
    preview_hash: str | None = Field(default=None, max_length=64)
    state: str = Field(default="pending", max_length=12)
    revision: int = 1
    row_count: int = 0
    normalized_rows: list = Field(default_factory=list, sa_column=Column(JSONB, nullable=False))
    errors: list = Field(default_factory=list, sa_column=Column(JSONB, nullable=False))
    retained_bytes: int = Field(default=0, sa_column=Column(BigInteger, nullable=False))
    created_at: datetime = timestamp()
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    committed_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))


class ImportCreatedQuestion(SQLModel, table=True):
    __tablename__ = "content_question_import_result"
    __table_args__ = (UniqueConstraint("batch_id", "row_number", name="uq_question_import_row"),)
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    batch_id: UUID = Field(foreign_key="content_question_import_batch.id", index=True)
    row_number: int
    question_id: UUID = Field(foreign_key="content_question.id")


class TransferTask(SQLModel, table=True):
    __tablename__ = "content_question_transfer_task"
    __table_args__ = (
        CheckConstraint("kind IN ('import','export') AND format IN ('csv','xlsx')", name="ck_question_transfer_kind"),
        CheckConstraint("state IN ('created','receiving','queued','running','succeeded','failed','canceled','expired')", name="ck_question_transfer_state"),
        CheckConstraint("generation > 0 AND reserved_bytes >= 0 AND retained_bytes >= 0", name="ck_question_transfer_budget"),
        CheckConstraint("work_role IN ('teacher','administrator')", name="ck_question_transfer_role"),
        CheckConstraint("expected_bytes BETWEEN 0 AND 16777216 AND result_bytes BETWEEN 0 AND 16777216", name="ck_question_transfer_bytes"),
        CheckConstraint("kind='export' OR (expected_bytes > 0 AND expected_bytes <= CASE WHEN format='csv' THEN 1048576 ELSE 5242880 END)", name="ck_question_import_bytes"),
        CheckConstraint("(kind='import' AND batch_id IS NOT NULL) OR (kind='export' AND batch_id IS NULL)", name="ck_question_transfer_batch"),
        ForeignKeyConstraint(["login_session_id", "owner_id"], ["login_session.id", "login_session.user_id"],
                             name="fk_question_transfer_session_owner"),
        UniqueConstraint("batch_id", name="uq_question_transfer_batch"),
        Index("ix_question_transfer_queue", "state", "created_at", "id"),
        Index("uq_question_transfer_receiving", "owner_id", unique=True,
              postgresql_where=text("kind='import' AND state IN ('created','receiving')")),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    batch_id: UUID | None = Field(default=None, foreign_key="content_question_import_batch.id")
    kind: str = Field(max_length=8)
    format: str = Field(max_length=4)
    library_id: UUID = Field(foreign_key="content_library.id")
    school_id: UUID | None = Field(default=None, foreign_key="school.id")
    owner_id: UUID = Field(foreign_key="app_user.id")
    login_session_id: UUID = Field(foreign_key="login_session.id")
    work_role: str = Field(max_length=20)
    input_hash: str = Field(max_length=64)
    expected_bytes: int = Field(default=0, sa_column=Column(BigInteger, nullable=False))
    file_key: str = Field(max_length=100, unique=True)
    result_hash: str | None = Field(default=None, max_length=64)
    result_bytes: int = Field(default=0, sa_column=Column(BigInteger, nullable=False))
    state: str = Field(default="created", max_length=12)
    stage: str = Field(default="created", max_length=30)
    generation: int = 1
    execution_id: UUID | None = Field(default=None, unique=True)
    lease_owner: UUID | None = None
    lease_until: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    stop_confirmed: bool = False
    reserved_bytes: int = Field(default=33554432, sa_column=Column(BigInteger, nullable=False))
    retained_bytes: int = Field(default=0, sa_column=Column(BigInteger, nullable=False))
    error_code: str | None = Field(default=None, max_length=40)
    created_at: datetime = timestamp()
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    finished_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))


class ExportVersion(SQLModel, table=True):
    __tablename__ = "content_question_export_version"
    __table_args__ = (UniqueConstraint("task_id", "version_id", name="uq_question_export_version"),)
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    task_id: UUID = Field(foreign_key="content_question_transfer_task.id", index=True)
    version_id: UUID = Field(foreign_key="content_question_version.id")
    ordinal: int
