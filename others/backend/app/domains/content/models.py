"""C-02 candidate tables; importing this module does not create or migrate tables."""
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, CheckConstraint, Column, DateTime, ForeignKeyConstraint, Index, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


def now():
    return datetime.now(UTC)


def timestamp():
    return Field(default_factory=now, sa_column=Column(DateTime(timezone=True), nullable=False))


class Library(SQLModel, table=True):
    __tablename__ = "content_library"
    __table_args__ = (
        CheckConstraint("(scope='platform_public' AND school_id IS NULL AND college_id IS NULL AND catalog_id IS NULL AND course_id IS NULL) OR "
                        "(scope='school' AND school_id IS NOT NULL AND college_id IS NULL AND catalog_id IS NULL AND course_id IS NULL) OR "
                        "(scope='college' AND school_id IS NOT NULL AND college_id IS NOT NULL AND catalog_id IS NULL AND course_id IS NULL) OR "
                        "(scope='catalog' AND school_id IS NOT NULL AND college_id IS NOT NULL AND catalog_id IS NOT NULL AND course_id IS NULL) OR "
                        "(scope='course' AND school_id IS NOT NULL AND college_id IS NOT NULL AND catalog_id IS NOT NULL AND course_id IS NOT NULL)", name="ck_content_library_scope"),
        CheckConstraint("audience IN ('all','staff')", name="ck_content_library_audience"),
        ForeignKeyConstraint(["college_id", "school_id"], ["college.id", "college.school_id"]),
        ForeignKeyConstraint(["catalog_id", "school_id"], ["course_catalog.id", "course_catalog.school_id"]),
        ForeignKeyConstraint(["course_id", "school_id"], ["course.id", "course.school_id"]),
        Index("ix_content_library_scope", "scope", "school_id", "college_id", "catalog_id", "course_id"),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    scope: str = Field(max_length=24)
    school_id: UUID | None = Field(default=None, foreign_key="school.id")
    college_id: UUID | None = None
    catalog_id: UUID | None = None
    course_id: UUID | None = None
    audience: str = Field(default="staff", max_length=8)
    title: str = Field(max_length=200)
    creator_id: UUID = Field(foreign_key="app_user.id")
    revision: int = 1
    active: bool = True
    created_at: datetime = timestamp()


class Material(SQLModel, table=True):
    __tablename__ = "content_material"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    library_id: UUID = Field(foreign_key="content_library.id", index=True)
    creator_id: UUID = Field(foreign_key="app_user.id")
    title: str = Field(max_length=200)
    revision: int = 1
    retired: bool = False
    created_at: datetime = timestamp()


class ContentUpload(SQLModel, table=True):
    __tablename__ = "content_upload"
    __table_args__ = (
        CheckConstraint("state IN ('created','receiving','sealed','canceled','expired','failed')", name="ck_content_upload_state"),
        CheckConstraint("expected_bytes > 0 AND expected_bytes <= 20971520 AND reserved_bytes >= 0 AND retained_bytes >= 0", name="ck_content_upload_bytes"),
        CheckConstraint("work_role IN ('teacher','administrator')", name="ck_content_upload_role"),
        Index("ix_content_upload_owner_state", "owner_id", "state"),
        Index("ix_content_upload_expiry", "state", "expires_at"),
        Index("uq_content_upload_owner_active", "owner_id", unique=True,
              postgresql_where=text("state IN ('created','receiving')")),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    library_id: UUID = Field(foreign_key="content_library.id", index=True)
    material_id: UUID | None = Field(default=None, foreign_key="content_material.id")
    owner_id: UUID = Field(foreign_key="app_user.id")
    login_session_id: UUID = Field(foreign_key="login_session.id")
    work_role: str = Field(max_length=20)
    school_id: UUID | None = Field(default=None, foreign_key="school.id", index=True)
    original_name: str = Field(max_length=240)
    title: str = Field(max_length=200)
    source_metadata: dict = Field(default_factory=dict, sa_column=Column(JSONB, nullable=False))
    format: str = Field(max_length=8)
    encoding: str = Field(default="utf-8", max_length=12)
    mime: str = Field(max_length=150)
    expected_bytes: int = Field(sa_column=Column(BigInteger, nullable=False))
    expected_hash: str = Field(max_length=64)
    file_key: str = Field(max_length=100, unique=True)
    state: str = Field(default="created", max_length=16)
    generation: int = 1
    lease_owner: UUID | None = None
    lease_until: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    reserved_bytes: int = Field(default=0, sa_column=Column(BigInteger, nullable=False))
    retained_bytes: int = Field(default=0, sa_column=Column(BigInteger, nullable=False))
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    sealed_version_id: UUID | None = Field(default=None, foreign_key="content_material_version.id")
    error_code: str | None = Field(default=None, max_length=40)
    created_at: datetime = timestamp()


class MaterialVersion(SQLModel, table=True):
    __tablename__ = "content_material_version"
    __table_args__ = (
        UniqueConstraint("material_id", "version_no", name="uq_content_material_version"),
        CheckConstraint("version_no > 0", name="ck_content_version_number"),
        CheckConstraint("retained_bytes >= 0", name="ck_content_version_bytes"),
        CheckConstraint("(input_kind='file' AND upload_id IS NOT NULL AND input_text IS NULL) OR "
                        "(input_kind='text' AND upload_id IS NULL AND input_text IS NOT NULL)", name="ck_content_version_input"),
        CheckConstraint("extraction_state IN ('queued','running','succeeded','failed','canceled')", name="ck_content_version_state"),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    material_id: UUID = Field(foreign_key="content_material.id", index=True)
    version_no: int
    input_kind: str = Field(max_length=8)
    upload_id: UUID | None = Field(default=None, foreign_key="content_upload.id")
    input_text: str | None = Field(default=None, sa_column=Column(Text))
    content_hash: str = Field(max_length=64)
    parser_version: str | None = Field(default=None, max_length=200)
    extraction_state: str = Field(default="queued", max_length=16)
    source_metadata: dict = Field(default_factory=dict, sa_column=Column(JSONB, nullable=False))
    warnings: list[str] = Field(default_factory=list, sa_column=Column(JSONB, nullable=False))
    allow_cloud: bool = False
    retained_bytes: int = Field(default=0, sa_column=Column(BigInteger, nullable=False))
    created_by: UUID = Field(foreign_key="app_user.id")
    created_at: datetime = timestamp()


class SourceChunk(SQLModel, table=True):
    __tablename__ = "content_source_chunk"
    __table_args__ = (
        UniqueConstraint("material_version_id", "ordinal", name="uq_content_chunk_ordinal"),
        CheckConstraint("ordinal > 0 AND char_length(text) <= 8192", name="ck_content_chunk_bounds"),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    material_version_id: UUID = Field(foreign_key="content_material_version.id", index=True)
    ordinal: int
    locator: dict = Field(sa_column=Column(JSONB, nullable=False))
    text: str = Field(sa_column=Column(Text, nullable=False))
    text_hash: str = Field(max_length=64)


class MaterialReview(SQLModel, table=True):
    __tablename__ = "content_material_review"
    __table_args__ = (
        CheckConstraint("state IN ('submitted','approved','rejected')", name="ck_content_review_state"),
        UniqueConstraint("id", "version_id", "target_library_id", name="uq_content_review_binding"),
        Index("ix_content_review_queue", "target_library_id", "state", "submitted_at", "id"),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    version_id: UUID = Field(foreign_key="content_material_version.id")
    target_library_id: UUID = Field(foreign_key="content_library.id")
    state: str = Field(default="submitted", max_length=12)
    submitter_id: UUID = Field(foreign_key="app_user.id")
    reviewer_id: UUID | None = Field(default=None, foreign_key="app_user.id")
    warning_hash: str = Field(max_length=64)
    original_authorized: bool = False
    authorization_statement: str = Field(sa_column=Column(Text, nullable=False))
    reason: str | None = Field(default=None, max_length=1000)
    revision: int = 1
    submitted_at: datetime = timestamp()
    decided_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))


class MaterialPublication(SQLModel, table=True):
    __tablename__ = "content_material_publication"
    __table_args__ = (
        ForeignKeyConstraint(["review_id", "version_id", "target_library_id"],
                             ["content_material_review.id", "content_material_review.version_id",
                              "content_material_review.target_library_id"], name="fk_content_publication_review"),
        UniqueConstraint("review_id", name="uq_content_publication_review"),
        Index("ix_content_publication_target", "target_library_id", "active", "version_id"),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    review_id: UUID
    version_id: UUID = Field(foreign_key="content_material_version.id")
    target_library_id: UUID = Field(foreign_key="content_library.id")
    active: bool = True
    published_by: UUID = Field(foreign_key="app_user.id")
    published_at: datetime = timestamp()
    retired_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    revision: int = 1


class ContentJob(SQLModel, table=True):
    __tablename__ = "content_job"
    __table_args__ = (
        CheckConstraint("state IN ('queued','running','succeeded','failed','canceled')", name="ck_content_job_state"),
        CheckConstraint("work_role IN ('teacher','administrator')", name="ck_content_job_role"),
        CheckConstraint("generation > 0 AND reserved_bytes >= 0", name="ck_content_job_generation"),
        Index("uq_content_job_version_active", "version_id", unique=True,
              postgresql_where=text("state IN ('queued','running')")),
        Index("ix_content_job_owner_state", "owner_id", "work_role", "state", "created_at", "id"),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    owner_id: UUID = Field(foreign_key="app_user.id")
    login_session_id: UUID = Field(foreign_key="login_session.id")
    work_role: str = Field(max_length=20)
    school_id: UUID | None = Field(default=None, foreign_key="school.id", index=True)
    library_id: UUID = Field(foreign_key="content_library.id")
    version_id: UUID = Field(foreign_key="content_material_version.id", index=True)
    state: str = Field(default="queued", max_length=16)
    stage: str = Field(default="queued", max_length=30)
    generation: int = 1
    lease_owner: UUID | None = None
    execution_id: UUID | None = None
    lease_until: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    heartbeat_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    stop_confirmed: bool = False
    reserved_bytes: int = Field(default=33554432, sa_column=Column(BigInteger, nullable=False))
    error_code: str | None = Field(default=None, max_length=40)
    created_at: datetime = timestamp()
    started_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    finished_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
