from uuid import UUID
from typing import Literal

from pydantic import BaseModel, Field


class LoginInput(BaseModel):
    school_code: str = Field(min_length=1, max_length=40)
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class Message(BaseModel):
    message: str


class OrganizationPublic(BaseModel):
    id: UUID
    name: str
    school_id: UUID | None = None


class GrantPublic(BaseModel):
    role: str
    college_id: UUID | None


class UserPublic(BaseModel):
    id: UUID
    username: str
    display_name: str
    school: OrganizationPublic | None
    college: OrganizationPublic | None
    grants: list[GrantPublic]
    permissions: list[str]
    available_work_roles: list[Literal["student", "teacher", "administrator"]]
    active_work_role: Literal["student", "teacher", "administrator"] | None
    effective_grants: list[GrantPublic]
    student_no: str | None = None
    major_id: UUID | None = None
    gender: str | None = None
    contact: str | None = None
    must_change_password: bool = False
    revision: int = 1


class CourseCreate(BaseModel):
    college_id: UUID
    teacher_id: UUID
    code: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    title: str = Field(min_length=1, max_length=120)
    catalog_id: UUID | None = None


class CoursePublic(BaseModel):
    id: UUID
    school_id: UUID
    college_id: UUID
    catalog_id: UUID
    college_name: str
    code: str
    title: str
    teacher_name: str


class CoursesPublic(BaseModel):
    data: list[CoursePublic]
    count: int


class CourseContext(BaseModel):
    can_create: bool
    colleges: list[OrganizationPublic]
    teachers: list[OrganizationPublic]
