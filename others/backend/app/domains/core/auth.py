from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import get_db
from app.domains.core.models import LoginSession, Role, RoleGrant, User

Db = Annotated[Session, Depends(get_db)]
bearer = HTTPBearer(auto_error=False)


@dataclass
class Identity:
    user: User
    grants: list[RoleGrant]
    login: LoginSession

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


def get_identity(db: Db, credential: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> Identity:
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
    # Grants are fetched on every request: token claims never freeze an old role.
    grants = list(db.exec(select(RoleGrant).where(RoleGrant.user_id == user.id)).all())
    return Identity(user, grants, login)


CurrentIdentity = Annotated[Identity, Depends(get_identity)]
