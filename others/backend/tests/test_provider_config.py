from uuid import uuid4

from cryptography.exceptions import InvalidTag
import pytest
from pydantic import ValidationError

from app.core.providers import (EncryptedProfile, ProviderNotConfigured, ProviderSpec,
    SchoolProviderSelection, can_manage_school_provider, open_key, resolve_provider, seal_key)
from app.domains.core.auth import Identity
from app.models import LoginSession, Role, RoleGrant, User

SPEC = ProviderSpec(base_url="https://api.deepseek.com", model="deepseek-flash")


def profile(scope, revision, key, secret="fixture-secret"):
    return EncryptedProfile(revision=revision, spec=SPEC,
                            ciphertext=seal_key(secret, scope=scope, revision=revision, key=key))


def test_encrypted_key_bound_to_school_and_revision_and_never_returned_in_status():
    key, school, revision = b"k" * 32, uuid4(), uuid4()
    record = profile(str(school), revision, key)
    assert open_key(record.ciphertext, scope=str(school), revision=revision, key=key).get_secret_value() == "fixture-secret"
    with pytest.raises(InvalidTag):
        open_key(record.ciphertext, scope=str(uuid4()), revision=revision, key=key)
    with pytest.raises(InvalidTag):
        open_key(record.ciphertext, scope=str(school), revision=uuid4(), key=key)
    assert "fixture-secret" not in str(record.public_status()) + repr(record)
    assert "ciphertext" not in record.public_status()


def test_school_must_choose_and_cannot_inherit_platform_secret_into_changed_endpoint():
    key, school, revision = b"k" * 32, uuid4(), uuid4()
    platform = profile("platform", uuid4(), key, "platform-secret")
    with pytest.raises(ProviderNotConfigured):
        resolve_provider(school, SchoolProviderSelection(school_id=school, revision=revision), key=key, platform=platform)
    with pytest.raises(ValidationError):
        SchoolProviderSelection(school_id=school, revision=revision, mode="school", enabled=True, tested_revision=revision)
    with pytest.raises(ValidationError):
        SchoolProviderSelection(school_id=school, revision=revision, mode="platform", profile=platform)
    selected = SchoolProviderSelection(school_id=school, revision=revision, mode="platform",
                                       enabled=True, tested_revision=revision)
    assert resolve_provider(school, selected, key=key, platform=platform).api_key.get_secret_value() == "platform-secret"
    with pytest.raises(PermissionError):
        resolve_provider(uuid4(), selected, key=key, platform=platform)
    local = SchoolProviderSelection(school_id=school, revision=revision, mode="school",
        profile=profile(str(school), revision, key, "school-secret"), enabled=True, tested_revision=revision)
    snapshot = resolve_provider(school, local, key=key, platform=platform)
    assert snapshot.api_key.get_secret_value() == "school-secret"
    assert "school-secret" not in repr(snapshot)


def test_changed_version_requires_new_server_test_and_old_snapshot_is_immutable():
    key, school, revision = b"k" * 32, uuid4(), uuid4()
    with pytest.raises(ValidationError):
        SchoolProviderSelection(school_id=school, revision=revision, mode="platform",
                                 enabled=True, tested_revision=uuid4())
    selected = SchoolProviderSelection(school_id=school, revision=revision, mode="platform",
                                       enabled=True, tested_revision=revision)
    first = resolve_provider(school, selected, key=key, platform=profile("platform", uuid4(), key, "old"))
    second = resolve_provider(school, selected, key=key, platform=profile("platform", uuid4(), key, "new"))
    assert first.api_key.get_secret_value() == "old"
    assert second.api_key.get_secret_value() == "new"


def test_school_admin_only_in_active_admin_identity_can_manage_school_profile():
    school = uuid4()
    user = User(school_id=school, username="fixture", display_name="fixture", hashed_password="not-login")
    grants = [RoleGrant(user_id=user.id, school_id=school, role=role) for role in (Role.SCHOOL_ADMIN, Role.TEACHER)]
    login = LoginSession(user_id=user.id)
    assert can_manage_school_provider(Identity(user, grants, login, "administrator"), school)
    assert not can_manage_school_provider(Identity(user, grants, login, "teacher"), school)
    assert not can_manage_school_provider(Identity(user, grants, login, "administrator"), uuid4())
    college = RoleGrant(user_id=user.id, school_id=school, college_id=uuid4(), role=Role.COLLEGE_ADMIN)
    assert not can_manage_school_provider(Identity(user, [college], login, "administrator"), school)
