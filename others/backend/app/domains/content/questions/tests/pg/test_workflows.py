"""Run after A2 installs the migration. Semantic fixtures do not verify production quota or sandbox."""
from datetime import timedelta
from uuid import UUID

import pytest
from fastapi import HTTPException
from sqlalchemy import func
from sqlmodel import select

from app.domains.core.auth import Identity
from app.domains.core.models import LoginSession, RoleGrant, User, now
from app.domains.content.access import require_library
from app.domains.content.schemas import LibraryCreate
from app.domains.content.services import create_library
from app.domains.content.questions.budget import ContentBudget
from app.domains.content.questions.lifecycle import retire_publication
from app.domains.content.questions.models import Question, QuestionReview, QuestionVersion
from app.domains.content.questions.policy import require_version
from app.domains.content.questions.queries import drafts, version_view
from app.domains.content.questions.schemas import CopyOrReference, Decision, Provenance, QuestionChange, QuestionCreate, Revision, Submit
from app.domains.content.questions.services import change_question, copy_question, create_question, decide_question, discard_draft, publish_question, submit_question
from app.domains.content.questions.tests.unit.test_schema import sample_question

# Isolates authorization/version semantics on real PG. A2's public tests must supply real unified accounting.
SEMANTIC_BUDGET = ContentBudget(lambda _db, _school: None)


def identity(db, username, work_role):
    user = db.exec(select(User).where(User.username == username)).one()
    login = LoginSession(user_id=user.id, expires_at=now() + timedelta(hours=1), default_work_role=work_role)
    db.add(login)
    db.flush()
    grants = list(db.exec(select(RoleGrant).where(RoleGrant.user_id == user.id)).all())
    return Identity(user, grants, login, work_role)


def bank(db, admin, *, public=False):
    result = create_library(db, admin, LibraryCreate(scope="platform_public" if public else "school",
        parent_id=None if public else admin.user.school_id, title="C1 synthetic bank", audience="all"), "c1-bank-create")
    return UUID(result["library_id"])


def publication(db, author, reviewer, library_id, *, public=False):
    provenance = Provenance(license="Synthetic teaching grant", teaching_reuse_allowed=True,
        public_reuse_allowed=public, license_url="https://example.test/synthetic-license" if public else None)
    created = create_question(db, author, QuestionCreate(library_id=library_id, payload=sample_question(), provenance=provenance),
                              "c1-question-create", SEMANTIC_BUDGET)
    submitted = submit_question(db, author, UUID(created["question_id"]), Submit(revision=1,
        target_library_id=library_id, authorization_statement="Synthetic functional test approval, not professional review"),
        "c1-question-submit", SEMANTIC_BUDGET)
    decide_question(db, reviewer, UUID(submitted["review_id"]), Decision(revision=1, decision="approved"),
                    "c1-question-approve", SEMANTIC_BUDGET)
    published = publish_question(db, reviewer, UUID(submitted["review_id"]), Revision(revision=2),
                                 "c1-question-publish", SEMANTIC_BUDGET)
    return created, submitted, published


def test_absent_accounting_rolls_back_all_question_writes(db):
    admin, teacher = identity(db, "admin", "administrator"), identity(db, "teacher", "teacher")
    library_id = bank(db, admin)
    before = db.exec(select(func.count()).select_from(Question)).one()
    with pytest.raises(HTTPException) as unavailable:
        create_question(db, teacher, QuestionCreate(library_id=library_id, payload=sample_question()), "c1-no-budget")
    assert unavailable.value.status_code == 503
    assert db.exec(select(func.count()).select_from(Question)).one() == before


def test_frozen_question_is_unchanged_by_draft_edit_and_students_get_no_bank_answers(db):
    admin, teacher = identity(db, "admin", "administrator"), identity(db, "teacher", "teacher")
    student = identity(db, "student", "student")
    library_id = bank(db, admin)
    created, submitted, _published = publication(db, teacher, admin, library_id)
    version_id = UUID(submitted["version_id"])
    old = version_view(db, teacher, version_id).model_dump(mode="json")
    changed = QuestionChange(revision=1, payload={**sample_question(), "stem": "改后的新草稿"}, provenance=Provenance())
    first = change_question(db, teacher, UUID(created["question_id"]), changed, "c1-edit-new-draft", SEMANTIC_BUDGET)
    assert change_question(db, teacher, UUID(created["question_id"]), changed, "c1-edit-new-draft", SEMANTIC_BUDGET) == first
    assert version_view(db, teacher, version_id).model_dump(mode="json") == old
    with pytest.raises(HTTPException):
        version_view(db, student, version_id)
    with pytest.raises(HTTPException):
        drafts(db, student)


def test_copy_needs_no_source_submit_right_and_remains_independent_after_source_retirement(db):
    platform = identity(db, "platform", "administrator")
    admin_b, teacher_b = identity(db, "admin_b", "administrator"), identity(db, "teacher_b", "teacher")
    public_id, target_id = bank(db, platform, public=True), bank(db, admin_b)
    _created, submitted, published = publication(db, platform, platform, public_id, public=True)
    with pytest.raises(HTTPException):
        require_library(db, teacher_b, public_id, "submit")
    request = CopyOrReference(source_version_id=UUID(submitted["version_id"]), target_library_id=target_id,
                              authorization_statement="Synthetic licensed reuse")
    copied = copy_question(db, teacher_b, request, "c1-copy-shared", SEMANTIC_BUDGET)
    retire_publication(db, platform, "question", UUID(published["publication_id"]), Revision(revision=1), "c1-retire-source")
    change_question(db, teacher_b, UUID(copied["question_id"]), QuestionChange(revision=1,
        payload={**sample_question(), "stem": "本校独立草稿"}, provenance=Provenance(license="Synthetic grant", teaching_reuse_allowed=True)),
        "c1-edit-copy-after-retire", SEMANTIC_BUDGET)
    parent_id = UUID(copied["question_id"])
    assert db.exec(select(QuestionReview).join(QuestionVersion, QuestionReview.version_id == QuestionVersion.id).where(
        QuestionVersion.question_id == parent_id)).first() is None


def test_discard_replay_does_not_resurrect_a_draft(db):
    admin, teacher = identity(db, "admin", "administrator"), identity(db, "teacher", "teacher")
    library_id = bank(db, admin)
    created = create_question(db, teacher, QuestionCreate(library_id=library_id, payload=sample_question()),
                              "c1-discard-create", SEMANTIC_BUDGET)
    question_id = UUID(created["question_id"])
    first = discard_draft(db, teacher, question_id, Revision(revision=1), "c1-discard-replay")
    assert discard_draft(db, teacher, question_id, Revision(revision=1), "c1-discard-replay") == first
    assert drafts(db, teacher).total == 0


def test_cross_school_direct_reference_is_not_a_publication_permission(db):
    admin, teacher = identity(db, "admin", "administrator"), identity(db, "teacher", "teacher")
    admin_b = identity(db, "admin_b", "administrator")
    a, b = bank(db, admin), bank(db, admin_b)
    _created, submitted, _published = publication(db, teacher, admin, a)
    with pytest.raises(HTTPException):
        require_version(db, admin_b, "question", UUID(submitted["version_id"]), b, published_only=True)


def test_cross_school_copy_from_an_approved_public_binding_keeps_the_original_private_school_hidden(db):
    admin, teacher = identity(db, "admin", "administrator"), identity(db, "teacher", "teacher")
    platform = identity(db, "platform", "administrator")
    admin_b, teacher_b = identity(db, "admin_b", "administrator"), identity(db, "teacher_b", "teacher")
    private_id, public_id, target_id = bank(db, admin), bank(db, platform, public=True), bank(db, admin_b)
    request = QuestionCreate(library_id=private_id, payload=sample_question(), provenance=Provenance(
        license="Synthetic public reuse", teaching_reuse_allowed=True, public_reuse_allowed=True,
        license_url="https://example.test/license"))
    created = create_question(db, teacher, request, "c1-shared-private-create", SEMANTIC_BUDGET)
    submitted = submit_question(db, platform, UUID(created["question_id"]), Submit(revision=1,
        target_library_id=public_id, authorization_statement="Synthetic public authorization"), "c1-shared-public-submit", SEMANTIC_BUDGET)
    decide_question(db, platform, UUID(submitted["review_id"]), Decision(revision=1, decision="approved"),
                    "c1-shared-public-decide", SEMANTIC_BUDGET)
    publish_question(db, platform, UUID(submitted["review_id"]), Revision(revision=2), "c1-shared-public-publish", SEMANTIC_BUDGET)
    copied = copy_question(db, teacher_b, CopyOrReference(source_version_id=UUID(submitted["version_id"]),
        target_library_id=target_id, authorization_statement="Synthetic public reuse"), "c1-shared-cross-copy", SEMANTIC_BUDGET)
    assert UUID(copied["question_id"]) != UUID(created["question_id"])
    assert version_view(db, teacher_b, UUID(submitted["version_id"])).library_id == public_id
