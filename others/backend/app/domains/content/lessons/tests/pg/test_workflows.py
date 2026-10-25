"""Real PG candidates, pending A2 migration. Not a real quota/sandbox evidence substitute."""
from uuid import UUID

import pytest
from fastapi import HTTPException
from sqlmodel import select

from app.domains.content.lessons.models import LessonDraftQuestionOrigin
from app.domains.content.lessons.queries import draft_asset, preview, preview_asset
from app.domains.content.lessons.schemas import LessonChange, LessonCreate, SceneCreate
from app.domains.content.lessons.services import change_lesson, create_lesson, create_scene, decide_lesson, publish_lesson, submit_lesson
from app.domains.content.lessons.tests.unit.test_content import sample_lesson
from app.domains.content.lessons.tests.unit.test_scenes import SAFE
from app.domains.content.questions.schemas import Decision, Provenance, Revision, Submit
from app.domains.content.questions.tests.pg.test_workflows import SEMANTIC_BUDGET, bank, identity, publication
from app.domains.content.questions.tests.unit.test_schema import sample_question


def scene(db, teacher, library_id, *, public=False):
    metadata = Provenance(license="Synthetic fixture teaching grant", teaching_reuse_allowed=True,
        public_reuse_allowed=public, license_url="https://example.test/license" if public else None)
    result = create_scene(db, teacher, SceneCreate(library_id=library_id, svg=SAFE, provenance=metadata),
                          "c1-scene-create", SEMANTIC_BUDGET)
    return UUID(result["asset_id"])


def lesson(db, teacher, library_id, asset_id):
    content = sample_lesson()
    content["scene"]["svg_asset_id"] = str(asset_id)
    content["provenance"] = Provenance(license="Synthetic fixture teaching grant", teaching_reuse_allowed=True).model_dump()
    created = create_lesson(db, teacher, LessonCreate(library_id=library_id, content=content),
                            "c1-lesson-create", SEMANTIC_BUDGET)
    return created, content


def test_approved_fixed_lesson_preview_and_asset_survive_new_draft_edits(db):
    admin, teacher = identity(db, "admin", "administrator"), identity(db, "teacher", "teacher")
    student = identity(db, "student", "student")
    library_id = bank(db, admin)
    asset_id = scene(db, teacher, library_id)
    created, raw = lesson(db, teacher, library_id, asset_id)
    lesson_id = UUID(created["lesson_id"])
    submitted = submit_lesson(db, teacher, lesson_id, Submit(revision=1, target_library_id=library_id,
        authorization_statement="Synthetic functional approval only"), "c1-lesson-submit", SEMANTIC_BUDGET)
    review_id, version_id = UUID(submitted["review_id"]), UUID(submitted["version_id"])
    decide_lesson(db, admin, review_id, Decision(revision=1, decision="approved"), "c1-lesson-decide", SEMANTIC_BUDGET)
    publish_lesson(db, admin, review_id, Revision(revision=2), "c1-lesson-publish", SEMANTIC_BUDGET)
    old = preview(db, teacher, version_id).model_dump(mode="json")
    raw["title"] = "独立的新草稿"
    change_lesson(db, teacher, lesson_id, LessonChange(revision=1, content=raw), "c1-lesson-edit", SEMANTIC_BUDGET)
    assert preview(db, teacher, version_id).model_dump(mode="json") == old
    assert preview_asset(db, teacher, version_id)[0] == draft_asset(db, teacher, lesson_id)[0]
    with pytest.raises(HTTPException):
        preview(db, student, version_id)
    with pytest.raises(HTTPException):
        preview_asset(db, student, version_id)


def test_unlinking_a_private_question_keeps_its_license_origin_and_cannot_launder_to_public(db):
    admin, teacher = identity(db, "admin", "administrator"), identity(db, "teacher", "teacher")
    platform = identity(db, "platform", "administrator")
    library_id, public_id = bank(db, admin), bank(db, platform, public=True)
    _q_created, q_submitted, _q_published = publication(db, teacher, admin, library_id)
    asset_id = scene(db, teacher, library_id, public=True)
    raw = sample_lesson()
    raw["scene"]["svg_asset_id"] = str(asset_id)
    question = sample_question()
    raw["activities"][0].update(prompt=question["stem"], options=question["options"], question_version_id=q_submitted["version_id"])
    raw["scoring"][0].update(correct_ids=question["answer_ids"], explanation=question["explanation"])
    created = create_lesson(db, teacher, LessonCreate(library_id=library_id, content=raw), "c1-origin-create", SEMANTIC_BUDGET)
    lesson_id = UUID(created["lesson_id"])
    raw["activities"][0]["question_version_id"] = None
    raw["provenance"] = Provenance(license="Synthetic public grant", teaching_reuse_allowed=True,
        public_reuse_allowed=True, license_url="https://example.test/license").model_dump()
    change_lesson(db, teacher, lesson_id, LessonChange(revision=1, content=raw), "c1-origin-unlink", SEMANTIC_BUDGET)
    assert db.exec(select(LessonDraftQuestionOrigin).where(LessonDraftQuestionOrigin.lesson_id == lesson_id)).one().question_version_id == UUID(q_submitted["version_id"])
    with pytest.raises(HTTPException) as denied:
        submit_lesson(db, platform, lesson_id, Submit(revision=2, target_library_id=public_id,
            authorization_statement="Synthetic test cannot override the question license"), "c1-origin-public", SEMANTIC_BUDGET)
    assert denied.value.status_code == 409
