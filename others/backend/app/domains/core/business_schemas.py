from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import Header
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from app.domains.core.models import Role

CommandKey = Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=128)]
Code = Annotated[str, Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")]
Name = Annotated[str, Field(min_length=1, max_length=120)]
Gender = Literal["male", "female", "other", "unspecified"]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="after")
    @classmethod
    def reject_blank(cls, value):
        if isinstance(value, str) and not value.strip():
            raise ValueError("内容不能仅包含空格")
        return value


class OrganizationInput(Input):
    school_id: UUID | None = None
    college_id: UUID | None = None
    code: Code
    name: Name


class OrganizationPatch(Input):
    revision: int = Field(ge=1)
    name: Name | None = None
    is_active: bool | None = None


class GrantInput(Input):
    role: Role
    college_id: UUID | None = None


class AccountCreate(Input):
    school_id: UUID
    college_id: UUID
    major_id: UUID | None = None
    username: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_.@-]+$")
    display_name: str = Field(min_length=1, max_length=80)
    student_no: str | None = Field(default=None, min_length=1, max_length=80)
    gender: Gender | None = None
    contact: str | None = Field(default=None, max_length=120)
    temporary_password: SecretStr = Field(min_length=8, max_length=256)
    grants: list[GrantInput] = Field(min_length=1, max_length=20)


class AccountPatch(Input):
    revision: int = Field(ge=1)
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    college_id: UUID | None = None
    major_id: UUID | None = None
    student_no: str | None = Field(default=None, min_length=1, max_length=80)
    gender: Gender | None = None
    contact: str | None = Field(default=None, max_length=120)
    is_active: bool | None = None


class ProfilePatch(Input):
    revision: int = Field(ge=1)
    gender: Gender | None = None
    contact: str | None = Field(default=None, max_length=120)


class PasswordChange(Input):
    old_password: SecretStr = Field(min_length=1, max_length=256)
    new_password: SecretStr = Field(min_length=8, max_length=256)


class PasswordReset(Input):
    temporary_password: SecretStr = Field(min_length=8, max_length=256)


class InvitationCreate(Input):
    school_id: UUID
    college_id: UUID
    major_id: UUID | None = None
    expires_at: datetime
    max_uses: int = Field(default=1, ge=1, le=500)


class Registration(Input):
    school_code: Code
    invitation_code: str = Field(min_length=16, max_length=100)
    username: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_.@-]+$")
    display_name: str = Field(min_length=1, max_length=80)
    student_no: str = Field(min_length=1, max_length=80)
    major_id: UUID | None = None
    gender: Gender | None = None
    contact: str | None = Field(default=None, max_length=120)
    password: SecretStr = Field(min_length=8, max_length=256)


class CatalogInput(Input):
    college_id: UUID
    owner_id: UUID
    code: Code
    title: Name


class CatalogPatch(Input):
    revision: int = Field(ge=1)
    title: Name | None = None
    owner_id: UUID | None = None
    archived: bool | None = None


class CourseSettings(Input):
    revision: int = Field(ge=1)
    title: Name | None = None
    join_approval: bool | None = None
    leave_approval: bool | None = None


class RevisionInput(Input):
    revision: int = Field(ge=1)


class StaffInput(RevisionInput):
    teacher_id: UUID


class InviteInput(RevisionInput):
    expires_at: datetime


class MemberInput(Input):
    username: str = Field(min_length=1, max_length=80)


class JoinInput(Input):
    invitation_code: str = Field(min_length=16, max_length=100)


class RequestDecision(Input):
    approve: bool


class CsvInput(Input):
    kind: Literal["accounts", "roster"]
    school_id: UUID
    course_id: UUID | None = None
    csv: str = Field(max_length=1_048_576)


class CsvCommit(CsvInput):
    preview_digest: str = Field(min_length=64, max_length=64)


class OrganizationView(BaseModel):
    id: UUID
    school_id: UUID | None = None
    college_id: UUID | None = None
    code: str
    name: str
    is_active: bool
    revision: int


class AccountView(BaseModel):
    id: UUID
    school_id: UUID | None
    college_id: UUID | None
    major_id: UUID | None
    username: str
    display_name: str
    student_no: str | None
    gender: str | None
    contact: str | None
    is_active: bool
    must_change_password: bool
    revision: int
    grants: list[GrantInput]


class CatalogView(BaseModel):
    id: UUID
    school_id: UUID
    college_id: UUID
    owner_id: UUID | None
    code: str
    title: str
    archived: bool
    revision: int


class ClassManagementView(BaseModel):
    id: UUID
    school_id: UUID
    college_id: UUID
    catalog_id: UUID
    code: str
    title: str
    archived: bool
    revision: int
    join_approval: bool
    leave_approval: bool
    can_manage_staff: bool
    can_manage_members: bool


class MemberView(BaseModel):
    id: UUID
    username: str
    display_name: str
    student_no: str | None
    college_id: UUID | None
    status: str


class StaffView(BaseModel):
    user_id: UUID
    display_name: str
    is_primary: bool
    is_active: bool


class RequestView(BaseModel):
    id: UUID
    course_id: UUID
    user_id: UUID
    display_name: str
    kind: str
    status: str
    created_at: datetime
    decided_at: datetime | None


class InvitationView(BaseModel):
    id: UUID
    school_id: UUID
    college_id: UUID
    major_id: UUID | None
    expires_at: datetime
    max_uses: int
    used_count: int
    revoked: bool


class Page[T](BaseModel):
    data: list[T]
    count: int


class CsvPreview(BaseModel):
    valid: bool
    row_count: int
    digest: str
    errors: list[dict]


class CsvResult(BaseModel):
    count: int
    ids: list[UUID]


class InvitationIssued(InvitationView):
    code: str


class InvitationContextView(BaseModel):
    school_id: UUID
    school_name: str
    college_id: UUID
    college_name: str
    majors: list[OrganizationView]


class CsvTemplateView(BaseModel):
    kind: str
    csv: str
    encoding: str
    instructions: str


class JoinCodeIssued(BaseModel):
    course_id: UUID
    code: str
    expires_at: datetime
    revision: int


class EnrollmentResult(BaseModel):
    course_id: UUID
    status: str
    request_id: UUID | None = None
