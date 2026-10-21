"""Real PostgreSQL operator bootstrap regressions; existing accounts must stay untouched."""
import pytest
from sqlalchemy import delete
from sqlmodel import select

from app.cloud_bootstrap import bootstrap
from app.core.security import verify_password
from app.domains.core.models import Role, RoleGrant, User


def test_first_operator_is_idempotent_without_password_reset(db):
    db.exec(delete(RoleGrant).where(RoleGrant.role == Role.PLATFORM_ADMIN))
    db.flush()
    created = bootstrap(db, "cloud-owner", "cloud-bootstrap-integration-password-1")
    assert created["created"] is True
    user = db.exec(select(User).where(User.username == "cloud-owner")).one()
    assert user.must_change_password and user.school_id is None
    password_hash = user.hashed_password
    repeated = bootstrap(db, "cloud-owner", "different-valid-password-not-to-be-applied")
    assert repeated["created"] is False and repeated["password_reset"] is False
    assert user.hashed_password == password_hash
    assert verify_password("cloud-bootstrap-integration-password-1", password_hash)[0]
    with pytest.raises(ValueError, match="operator already exists"):
        bootstrap(db, "another-cloud-owner", "cloud-bootstrap-integration-password-2")


def test_existing_fixture_operator_cannot_be_silently_replaced(db):
    with pytest.raises(ValueError, match="operator already exists"):
        bootstrap(db, "cloud-owner", "cloud-bootstrap-integration-password-1")
    db.exec(delete(RoleGrant).where(RoleGrant.role == Role.PLATFORM_ADMIN))
    db.flush()
    with pytest.raises(ValueError, match="already used"):
        bootstrap(db, "platform", "cloud-bootstrap-integration-password-1")
    with pytest.raises(ValueError, match="20-256"):
        bootstrap(db, "cloud-owner", "88888888")
