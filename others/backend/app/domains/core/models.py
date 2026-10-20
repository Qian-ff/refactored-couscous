"""Tenant consistency is enforced by both PostgreSQL foreign keys and API authorization."""
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint
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


class College(SQLModel, table=True):
    __tablename__ = "college"
    __table_args__ = (UniqueConstraint("school_id", "code"), UniqueConstraint("id", "school_id"))
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    school_id: UUID = Field(foreign_key="school.id", index=True)
    code: str = Field(max_length=40)
    name: str = Field(max_length=120)


class User(SQLModel, table=True):
    __tablename__ = "app_user"
    __table_args__ = (
        UniqueConstraint("school_id", "username"), UniqueConstraint("id", "school_id"),
        ForeignKeyConstraint(["college_id", "school_id"], ["college.id", "college.school_id"]),
        CheckConstraint("school_id IS NOT NULL OR college_id IS NULL"),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    school_id: UUID | None = Field(default=None, foreign_key="school.id", index=True)
    college_id: UUID | None = Field(default=None)
    username: str = Field(max_length=80, index=True)
    display_name: str = Field(max_length=80)
    hashed_password: str
    is_active: bool = True


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


class Course(SQLModel, table=True):
    __tablename__ = "course"
    __table_args__ = (
        UniqueConstraint("school_id", "code"), UniqueConstraint("id", "school_id"),
        ForeignKeyConstraint(["college_id", "school_id"], ["college.id", "college.school_id"]),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    school_id: UUID = Field(foreign_key="school.id", index=True)
    college_id: UUID
    code: str = Field(max_length=40)
    title: str = Field(max_length=120)
    created_at: datetime = Field(default_factory=now)


class CourseStaff(SQLModel, table=True):
    __tablename__ = "course_staff"
    __table_args__ = (
        UniqueConstraint("course_id", "user_id"),
        ForeignKeyConstraint(["course_id", "school_id"], ["course.id", "course.school_id"]),
        ForeignKeyConstraint(["user_id", "school_id"], ["app_user.id", "app_user.school_id"]),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    school_id: UUID
    course_id: UUID = Field(index=True)
    user_id: UUID = Field(index=True)
    is_primary: bool = False


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
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="app_user.id", index=True)
    expires_at: datetime
    revoked: bool = False
