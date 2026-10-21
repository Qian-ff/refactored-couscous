from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import get_db
from app.core.grants import validate_role_family
from app.domains.core.models import LoginSession, Role, RoleGrant, School, User

Db = Annotated[Session, Depends(get_db)]
bearer = HTTPBearer(auto_error=False)


WORK_ROLES = {
    "student": {Role.STUDENT},
    "teacher": {Role.TEACHER},
    "administrator": {Role.PLATFORM_ADMIN, Role.SCHOOL_ADMIN, Role.COLLEGE_ADMIN},
}


def available_work_roles(grants: list[RoleGrant]) -> list[str]:
    validate_role_family({g.role for g in grants})
    return [work for work, roles in WORK_ROLES.items() if any(g.role in roles for g in grants)]


def default_work_role(grants: list[RoleGrant]) -> str | None:
    available = available_work_roles(grants)
    return "teacher" if "teacher" in available else (available[0] if available else None)


@dataclass
class Account:
    user: User
    all_grants: list[RoleGrant]
    login: LoginSession


@dataclass
class Identity(Account):
    work_role: str | None

    @property
    def grants(self) -> list[RoleGrant]:
        return [g for g in self.all_grants if g.role in WORK_ROLES.get(self.work_role, set())]

    def has(self, role: Role) -> bool:
        return any(g.role == role and g.school_id == self.user.school_id for g in self.grants)

    def manages(self, college_id: UUID, school_id: UUID) -> bool:
        if self.has(Role.PLATFORM_ADMIN):
            return True
        if self.user.school_id != school_id:
            return False
        return self.has(Role.SCHOOL_ADMIN) or any(
            g.role == Role.COLLEGE_ADMIN and g.college_id == college_id and g.school_id == school_id
            for g in self.grants
        )

    def can_create(self, college_id: UUID, school_id: UUID) -> bool:
        return self.manages(college_id, school_id) or (
            self.has(Role.TEACHER) and self.user.school_id == school_id and self.user.college_id == college_id
        )


def get_account(db: Db, credential: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> Account:
    denied = HTTPException(status_code=401, detail="登录已失效，请重新登录", headers={"WWW-Authenticate": "Bearer"})
    if credential is None:
        raise denied
    try:
        data = jwt.decode(credential.credentials, settings.SECRET_KEY, algorithms=["HS256"], options={"require": ["exp", "sub", "jti"]})
        user_id, session_id = UUID(data["sub"]), UUID(data["jti"])
    except (jwt.InvalidTokenError, ValueError, TypeError, KeyError):
        raise denied
    login = db.get(LoginSession, session_id)
    user = db.get(User, user_id)
    if (login is None or login.revoked or login.user_id != user_id or user is None or not user.is_active
            or login.expires_at.replace(tzinfo=UTC) <= datetime.now(UTC)):
        raise denied
    if user.school_id:
        school = db.get(School, user.school_id)
        if school is None or not school.is_active:
            raise denied
    # Grants are fetched on every request: token claims never freeze an old role.
    grants = list(db.exec(select(RoleGrant).where(RoleGrant.user_id == user.id)).all())
    return Account(user, grants, login)


CurrentAccount = Annotated[Account, Depends(get_account)]


def get_identity(account: CurrentAccount, db: Db,
                 work_role: Annotated[str | None, Header(alias="X-Work-Role")] = None) -> Identity:
    try:
        available = available_work_roles(account.all_grants)
    except ValueError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    if account.login.default_work_role is None and available:
        account.login.default_work_role = default_work_role(account.all_grants)
        db.add(account.login)
        db.commit()
    selected = work_role if work_role is not None else account.login.default_work_role
    if selected is not None and selected not in available:
        raise HTTPException(status_code=403, detail="当前工作身份未授权或已撤销，请重新选择身份或登录")
    return Identity(account.user, account.all_grants, account.login, selected)


AccountIdentity = Annotated[Identity, Depends(get_identity)]


def get_business_identity(identity: AccountIdentity) -> Identity:
    if identity.user.must_change_password:
        raise HTTPException(status_code=403, detail="请先修改临时密码")
    return identity


CurrentIdentity = Annotated[Identity, Depends(get_business_identity)]
