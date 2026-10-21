"""Explicit first operator setup; never seeds fixtures or resets an existing password."""
import json
import os
import re

from sqlalchemy import text
from sqlmodel import Session, select

from app.core.db import engine
from app.core.grants import add_role_grant
from app.core.security import get_password_hash
from app.domains.core.models import Role, RoleGrant, User


def bootstrap(db: Session, username: str, password: str) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,80}", username):
        raise ValueError("Operator username must contain 3-80 letters, digits, dots, underscores or hyphens")
    db.execute(text("SELECT pg_advisory_xact_lock(684207663103)"))
    existing = db.exec(select(User).where(User.school_id.is_(None), User.username == username)).first()
    operators = list(db.exec(select(RoleGrant).where(RoleGrant.role == Role.PLATFORM_ADMIN)).all())
    if existing is not None:
        if any(g.user_id == existing.id for g in operators) and existing.is_active:
            return {"created": False, "username": username, "password_reset": False}
        raise ValueError("This username is already used by a different or inactive account")
    if operators:
        raise ValueError("An operator already exists; manage additional accounts through the authenticated API")
    if not 20 <= len(password) <= 256 or any(x in password.lower() for x in ("replace_", "change_me")):
        raise ValueError("A newly generated operator password of 20-256 characters is required")
    user = User(username=username, display_name="平台运维", school_id=None,
                hashed_password=get_password_hash(password), must_change_password=True)
    db.add(user)
    db.flush()
    add_role_grant(db, user_id=user.id, role=Role.PLATFORM_ADMIN)
    return {"created": True, "username": username, "must_change_password": True, "password_reset": False}


def main():
    with Session(engine) as db:
        result = bootstrap(db, os.environ.get("LABCONNECT_BOOTSTRAP_USERNAME", ""),
                           os.environ.get("LABCONNECT_BOOTSTRAP_PASSWORD", ""))
        db.commit()
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    main()
