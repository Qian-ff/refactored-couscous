"""Tenant consistency is enforced by both PostgreSQL foreign keys and API authorization."""
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Column, ForeignKeyConstraint, Index, JSON, UniqueConstraint, text
from sqlmodel import Field, SQLModel


def now() -> datetime:
    return datetime.now(UTC)


class Role(StrEnum):
    PLATFORM_ADMIN = "platform_admin"
    SCHOOL_ADMIN = "school_admin"
    COLLEGE_ADMIN = "college_admin"
    TEACHER = "teacher"
    STUDENT = "student"


class School(SQLModel, table=True):
    __tablename__ = "school"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    code: str = Field(unique=True, max_length=40)
    name: str = Field(max_length=120)
    is_active: bool = True
    revision: int = 1


class College(SQLModel, table=True):
    __tablename__ = "college"
    __table_args__ = (UniqueConstraint("school_id", "code"), UniqueConstraint("id", "school_id"))
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    school_id: UUID = Field(foreign_key="school.id", index=True)
    code: str = Field(max_length=40)
    name: str = Field(max_length=120)
    is_active: bool = True
    revision: int = 1


class Major(SQLModel, table=True):
    __tablename__ = "major"
    __table_args__ = (
        UniqueConstraint("school_id", "college_id", "code"),
        UniqueConstraint("id", "school_id", "college_id"),
        ForeignKeyConstraint(["college_id", "school_id"], ["college.id", "college.school_id"]),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    school_id: UUID = Field(foreign_key="school.id", index=True)
    college_id: UUID
    code: str = Field(max_length=40)
    name: str = Field(max_length=120)
    is_active: bool = True
    revision: int = 1


class User(SQLModel, table=True):
    __tablename__ = "app_user"
    __table_args__ = (
        UniqueConstraint("school_id", "username"), UniqueConstraint("id", "school_id"),
        UniqueConstraint("school_id", "student_no"),
        ForeignKeyConstraint(["college_id", "school_id"], ["college.id", "college.school_id"]),
        ForeignKeyConstraint(["major_id", "school_id", "college_id"], ["major.id", "major.school_id", "major.college_id"]),
        CheckConstraint("school_id IS NOT NULL OR college_id IS NULL"),
        CheckConstraint("major_id IS NULL OR (school_id IS NOT NULL AND college_id IS NOT NULL)"),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    school_id: UUID | None = Field(default=None, foreign_key="school.id", index=True)
    college_id: UUID | None = Field(default=None)
    username: str = Field(max_length=80, index=True)
    display_name: str = Field(max_length=80)
    hashed_password: str
    is_active: bool = True
    student_no: str | None = Field(default=None, max_length=80)
    major_id: UUID | None = None
    gender: str | None = Field(default=None, max_length=20)
    contact: str | None = Field(default=None, max_length=120)
    must_change_password: bool = False
    revision: int = 1


class RoleGrant(SQLModel, table=True):
    __tablename__ = "role_grant"
    __table_args__ = (
        ForeignKeyConstraint(["user_id", "school_id"], ["app_user.id", "app_user.school_id"]),
        ForeignKeyConstraint(["college_id", "school_id"], ["college.id", "college.school_id"]),
        CheckConstraint("(role = 'platform_admin' AND school_id IS NULL AND college_id IS NULL) OR (role <> 'platform_admin' AND school_id IS NOT NULL)"),
        CheckConstraint("role <> 'college_admin' OR college_id IS NOT NULL"),
        UniqueConstraint("user_id", "role", "college_id"),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="app_user.id", index=True)
    school_id: UUID | None = Field(default=None)
    role: str = Field(max_length=30)
    college_id: UUID | None = Field(default=None)


class CourseCatalog(SQLModel, table=True):
    __tablename__ = "course_catalog"
    __table_args__ = (
        UniqueConstraint("school_id", "code"), UniqueConstraint("id", "school_id"),
        ForeignKeyConstraint(["college_id", "school_id"], ["college.id", "college.school_id"]),
        ForeignKeyConstraint(["owner_id", "school_id"], ["app_user.id", "app_user.school_id"]),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    school_id: UUID = Field(foreign_key="school.id", index=True)
    college_id: UUID
    owner_id: UUID | None = None
    code: str = Field(max_length=40)
    title: str = Field(max_length=120)
    created_at: datetime = Field(default_factory=now)
    archived: bool = False
    revision: int = 1


class Course(SQLModel, table=True):
    __tablename__ = "course"
    __table_args__ = (
        UniqueConstraint("school_id", "code"), UniqueConstraint("id", "school_id"),
        UniqueConstraint("id", "school_id", "college_id", "catalog_id", name="uq_course_content_parent"),
        UniqueConstraint("join_code_hash"),
        ForeignKeyConstraint(["college_id", "school_id"], ["college.id", "college.school_id"]),
        ForeignKeyConstraint(["catalog_id", "school_id"], ["course_catalog.id", "course_catalog.school_id"]),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    school_id: UUID = Field(foreign_key="school.id", index=True)
    college_id: UUID
    catalog_id: UUID = Field(index=True)
    code: str = Field(max_length=40)
    title: str = Field(max_length=120)
    created_at: datetime = Field(default_factory=now)
    archived: bool = False
    join_approval: bool = False
    leave_approval: bool = False
    join_code_hash: str | None = Field(default=None, max_length=64)
    join_code_expires_at: datetime | None = None
    revision: int = 1


class CourseStaff(SQLModel, table=True):
    __tablename__ = "course_staff"
    __table_args__ = (
        UniqueConstraint("course_id", "user_id"),
        ForeignKeyConstraint(["course_id", "school_id"], ["course.id", "course.school_id"]),
        ForeignKeyConstraint(["user_id", "school_id"], ["app_user.id", "app_user.school_id"]),
        Index("uq_course_active_primary", "course_id", unique=True,
              postgresql_where=text("is_primary AND is_active")),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    school_id: UUID
    course_id: UUID = Field(index=True)
    user_id: UUID = Field(index=True)
    is_primary: bool = False
    is_active: bool = True


class Enrollment(SQLModel, table=True):
    __tablename__ = "enrollment"
    __table_args__ = (
        UniqueConstraint("course_id", "user_id"),
        ForeignKeyConstraint(["course_id", "school_id"], ["course.id", "course.school_id"]),
        ForeignKeyConstraint(["user_id", "school_id"], ["app_user.id", "app_user.school_id"]),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    school_id: UUID
    course_id: UUID = Field(index=True)
    user_id: UUID = Field(index=True)
    status: str = Field(default="active", max_length=20)


class LoginSession(SQLModel, table=True):
    __tablename__ = "login_session"
    __table_args__ = (UniqueConstraint("id", "user_id", name="uq_login_session_owner"),)
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="app_user.id", index=True)
    expires_at: datetime
    revoked: bool = False
    default_work_role: str | None = Field(default=None, max_length=20)


class EnrollmentRequest(SQLModel, table=True):
    __tablename__ = "enrollment_request"
    __table_args__ = (
        ForeignKeyConstraint(["course_id", "school_id"], ["course.id", "course.school_id"]),
        ForeignKeyConstraint(["user_id", "school_id"], ["app_user.id", "app_user.school_id"]),
        CheckConstraint("kind IN ('join','leave')"),
        CheckConstraint("status IN ('pending','approved','rejected','canceled')"),
        Index("uq_pending_enrollment_request", "course_id", "user_id", "kind", unique=True,
              postgresql_where=text("status = 'pending'")),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    school_id: UUID
    course_id: UUID = Field(index=True)
    user_id: UUID = Field(index=True)
    kind: str = Field(max_length=12)
    status: str = Field(default="pending", max_length=12)
    created_at: datetime = Field(default_factory=now)
    decided_at: datetime | None = None
    decided_by: UUID | None = Field(default=None, foreign_key="app_user.id")


class AccountInvitation(SQLModel, table=True):
    __tablename__ = "account_invitation"
    __table_args__ = (
        ForeignKeyConstraint(["college_id", "school_id"], ["college.id", "college.school_id"]),
        ForeignKeyConstraint(["major_id", "school_id", "college_id"], ["major.id", "major.school_id", "major.college_id"]),
        CheckConstraint("used_count >= 0 AND max_uses > 0 AND used_count <= max_uses"),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    school_id: UUID = Field(foreign_key="school.id", index=True)
    college_id: UUID
    major_id: UUID | None = None
    code_hash: str = Field(unique=True, max_length=64)
    expires_at: datetime
    max_uses: int = 1
    used_count: int = 0
    revoked: bool = False
    created_by: UUID = Field(foreign_key="app_user.id")


class CoreAuditEvent(SQLModel, table=True):
    __tablename__ = "core_audit_event"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    school_id: UUID | None = Field(default=None, foreign_key="school.id", index=True)
    actor_id: UUID | None = Field(default=None, foreign_key="app_user.id")
    work_role: str = Field(max_length=24)
    operation: str = Field(max_length=120)
    entity_id: UUID | None = None
    details: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    created_at: datetime = Field(default_factory=now)


class CommandReceipt(SQLModel, table=True):
    __tablename__ = "command_receipt"
    __table_args__ = (UniqueConstraint("subject", "work_role", "operation", "key"),)
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    subject: str = Field(max_length=100)
    work_role: str = Field(max_length=24)
    operation: str = Field(max_length=120)
    key: str = Field(max_length=128)
    request_hash: str = Field(max_length=64)
    result: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    created_at: datetime = Field(default_factory=now)
