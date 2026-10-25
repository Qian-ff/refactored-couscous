"""Reload the initiating real login/role for streaming and background tasks; no JWT storage."""
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlmodel import select

from app.domains.core.auth import Identity, available_work_roles
from app.domains.core.models import LoginSession, RoleGrant, School, User


def load_identity(db, owner_id: UUID, login_id: UUID, work_role: str):
    user, login = db.get(User, owner_id), db.get(LoginSession, login_id)
    if (user is None or login is None or login.user_id != owner_id or not user.is_active
            or login.revoked or login.expires_at.replace(tzinfo=UTC) <= datetime.now(UTC)
            or user.must_change_password):
        raise HTTPException(401, "ACCESS_REVOKED")
    if user.school_id is not None:
        school = db.get(School, user.school_id)
        if school is None or not school.is_active:
            raise HTTPException(401, "ACCESS_REVOKED")
    grants = list(db.exec(select(RoleGrant).where(RoleGrant.user_id == owner_id)).all())
    try:
        if work_role not in available_work_roles(grants):
            raise HTTPException(403, "ACCESS_REVOKED")
    except ValueError as error:
        raise HTTPException(403, "ACCESS_REVOKED") from error
    return Identity(user, grants, login, work_role)
