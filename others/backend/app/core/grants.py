"""Shared role-family checks; B must call the locked writer inside its business transaction."""
from uuid import UUID

from sqlmodel import Session, select

from app.domains.core.models import Role, RoleGrant, User


def validate_role_family(roles: set[str]) -> None:
    if not roles.issubset({role.value for role in Role}):
        raise ValueError("未知授权角色")
    if Role.STUDENT in roles and roles - {Role.STUDENT}:
        raise ValueError("学生账号不能兼任教师或管理员，请使用独立账号")


def add_role_grant(db: Session, *, user_id: UUID, role: Role,
                   college_id: UUID | None = None) -> RoleGrant:
    """Locks the parent account, serializing grants even when no RoleGrant row exists yet. No commit."""
    user = db.exec(select(User).where(User.id == user_id).with_for_update()).one()
    grants = list(db.exec(select(RoleGrant).where(RoleGrant.user_id == user_id)).all())
    validate_role_family({grant.role for grant in grants} | {role.value})
    existing = next((g for g in grants if g.role == role and g.college_id == college_id), None)
    if existing:
        return existing
    grant = RoleGrant(user_id=user_id, school_id=user.school_id, role=role, college_id=college_id)
    db.add(grant)
    db.flush()
    return grant
