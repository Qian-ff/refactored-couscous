"""Real PG service scenarios. Run only after A publishes the C-02 migration."""
from datetime import timedelta
from uuid import UUID

import pytest
from fastapi import HTTPException
from sqlmodel import select

from app.domains.core.auth import Identity
from app.domains.core.models import LoginSession, RoleGrant, User
from app.domains.content.access import require_version
from app.domains.content.models import ContentJob, MaterialVersion, now
from app.domains.content.schemas import (
    LibraryCreate, ReviewDecision, ReviewSubmit, RevisionInput, TextMaterialCreate,
)
from app.domains.content.services import (
    create_library, create_text_version, decide_review, publish_review, retire_publication, submit_review, warnings_hash,
)


def identity(db, username, work_role):
    user = db.exec(select(User).where(User.username == username)).one()
    login = LoginSession(user_id=user.id, expires_at=now() + timedelta(hours=1), default_work_role=work_role)
    db.add(login)
    db.flush()
    grants = list(db.exec(select(RoleGrant).where(RoleGrant.user_id == user.id)).all())
    return Identity(user, grants, login, work_role)


def school_library(db, admin):
    result = create_library(db, admin, LibraryCreate(scope="school", parent_id=admin.user.school_id,
                                                    title="Synthetic C02", audience="all"), "c02-library-key")
    return UUID(result["library_id"])


def completed_fixture(db, created):
    # Trusted fixture for publication tests; not parser or sandbox completion evidence.
    version = db.get(MaterialVersion, UUID(created["version_id"]))
    version.extraction_state = "succeeded"
    version.parser_version = "synthetic-fixture/1"
    job = db.get(ContentJob, UUID(created["job_id"]))
    job.state = "succeeded"
    job.stop_confirmed = True
    job.reserved_bytes = 0
    db.add(version)
    db.add(job)
    db.flush()
    return version


def test_submit_only_teacher_cannot_create_school_library(db):
    teacher = identity(db, "teacher", "teacher")
    with pytest.raises(HTTPException) as denied:
        create_library(db, teacher, LibraryCreate(scope="school", parent_id=teacher.user.school_id,
                                                  title="Forbidden"), "c02-no-management")
    assert denied.value.status_code == 403


def test_fixed_publication_does_not_expose_new_draft_and_retire_revokes(db):
    admin = identity(db, "admin", "administrator")
    teacher = identity(db, "teacher", "teacher")
    student = identity(db, "student", "student")
    library_id = school_library(db, admin)
    request = TextMaterialCreate(library_id=library_id, title="Synthetic material", text="Original knowledge")
    created = create_text_version(db, teacher, request, "c02-text-create", 10 * 1024**3)
    assert create_text_version(db, teacher, request, "c02-text-create", 10 * 1024**3) == created
    version = completed_fixture(db, created)
    with pytest.raises(HTTPException):
        require_version(db, student, version.id)
    review = submit_review(db, teacher, ReviewSubmit(version_id=version.id, target_library_id=library_id,
                           authorization_statement="Synthetic original, authorized for this teaching scope"), "c02-review-submit")
    decide_review(db, admin, UUID(review["review_id"]), ReviewDecision(
        revision=1, decision="approved", warning_hash=warnings_hash(version),
        warnings_acknowledged=True, original_authorized=True), "c02-review-approve")
    published = publish_review(db, admin, UUID(review["review_id"]), RevisionInput(revision=2), "c02-publish")
    assert require_version(db, student, version.id)[0].id == version.id
    draft = create_text_version(db, teacher, TextMaterialCreate(
        library_id=library_id, material_id=UUID(created["material_id"]), title=request.title, text="New draft"),
        "c02-second-version", 10 * 1024**3)
    with pytest.raises(HTTPException):
        require_version(db, student, UUID(draft["version_id"]))
    retire_publication(db, admin, UUID(published["publication_id"]), RevisionInput(revision=1), "c02-retire")
    with pytest.raises(HTTPException):
        require_version(db, student, version.id)


def test_same_idempotency_key_different_text_is_conflict(db):
    admin = identity(db, "admin", "administrator")
    teacher = identity(db, "teacher", "teacher")
    library_id = school_library(db, admin)
    request = TextMaterialCreate(library_id=library_id, title="Synthetic", text="First")
    create_text_version(db, teacher, request, "c02-same-key", 10 * 1024**3)
    with pytest.raises(HTTPException) as conflict:
        create_text_version(db, teacher, request.model_copy(update={"text": "Different"}),
                            "c02-same-key", 10 * 1024**3)
    assert conflict.value.status_code == 409
