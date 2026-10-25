"""Staff authoring/preview candidate; B2 owns official student JSON and SVG authorization."""
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Response

from app.domains.content.lessons import queries, services
from app.domains.content.lessons.schemas import LessonChange, LessonCreate, SceneCreate, TeacherLessonPreview
from app.domains.content.lessons.views import DraftView, VersionView
from app.domains.content.questions import lifecycle, queries as common
from app.domains.content.questions.http import CommandKey, Environment, Keyword, Limit, Offset, StaffIdentity
from app.domains.content.questions.schemas import CopyOrReference, Decision, ParentChange, Revision, Submit
from app.domains.content.questions.views import BankView, CommandResult, Page, PublicationView, ReviewView
from app.domains.core.auth import Db

router = APIRouter(prefix="/content/lessons", tags=["content-lessons"])


@router.get("/banks", response_model=Page[BankView])
def banks(db: Db, identity: StaffIdentity, q: Keyword = "", offset: Offset = 0, limit: Limit = 50, include_inactive: bool = False):
    return common.banks(db, identity, q, offset, limit, include_inactive, kind="lesson")


@router.post("/scenes", response_model=CommandResult, response_model_exclude_none=True, status_code=201)
def create_scene(db: Db, identity: StaffIdentity, env: Environment, body: SceneCreate, key: CommandKey):
    return services.create_scene(db, identity, body, key, env.budget)


@router.get("/drafts", response_model=Page[DraftView])
def drafts(db: Db, identity: StaffIdentity, q: Keyword = "", offset: Offset = 0, limit: Limit = 50, library_id: UUID | None = None):
    return queries.drafts(db, identity, q, offset, limit, library_id)


@router.get("/drafts/{lesson_id}", response_model=DraftView)
def draft(db: Db, identity: StaffIdentity, lesson_id: UUID):
    return queries.draft_view(db, identity, lesson_id)


@router.post("/drafts", response_model=CommandResult, response_model_exclude_none=True, status_code=201)
def create(db: Db, identity: StaffIdentity, env: Environment, body: LessonCreate, key: CommandKey):
    return services.create_lesson(db, identity, body, key, env.budget)


@router.patch("/drafts/{lesson_id}", response_model=CommandResult, response_model_exclude_none=True)
def change(db: Db, identity: StaffIdentity, env: Environment, lesson_id: UUID, body: LessonChange, key: CommandKey):
    return services.change_lesson(db, identity, lesson_id, body, key, env.budget)


@router.post("/drafts/{lesson_id}/discard", response_model=CommandResult, response_model_exclude_none=True)
def discard(db: Db, identity: StaffIdentity, lesson_id: UUID, body: Revision, key: CommandKey):
    return services.discard_lesson(db, identity, lesson_id, body, key)


@router.patch("/{lesson_id}/retirement", response_model=CommandResult, response_model_exclude_none=True)
def retire(db: Db, identity: StaffIdentity, lesson_id: UUID, body: ParentChange, key: CommandKey):
    return lifecycle.change_parent(db, identity, "lesson", lesson_id, body, key)


@router.get("/versions", response_model=Page[VersionView])
def versions(db: Db, identity: StaffIdentity, q: Keyword = "", offset: Offset = 0, limit: Limit = 50,
             library_id: UUID | None = None, lesson_id: UUID | None = None):
    return queries.versions(db, identity, q, offset, limit, library_id, lesson_id)


@router.get("/versions/{version_id}", response_model=VersionView)
def version(db: Db, identity: StaffIdentity, version_id: UUID, library_id: UUID | None = None):
    return queries.version_view(db, identity, version_id, library_id)


@router.get("/versions/{version_id}/preview", response_model=TeacherLessonPreview)
def preview(db: Db, identity: StaffIdentity, version_id: UUID, library_id: UUID | None = None):
    return queries.preview(db, identity, version_id, library_id)


def svg_response(data):
    svg, _hash = data
    return Response(content=svg, media_type="image/svg+xml", headers={"Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff", "Content-Security-Policy": "sandbox; default-src 'none'",
        "Content-Disposition": 'inline; filename="labconnect-scene.svg"'})


SVG_RESPONSE = {200: {"content": {"image/svg+xml": {"schema": {"type": "string", "format": "binary"}}}}}


@router.get("/versions/{version_id}/preview/scene", response_class=Response, responses=SVG_RESPONSE)
def preview_scene(db: Db, identity: StaffIdentity, version_id: UUID, library_id: UUID | None = None):
    return svg_response(queries.preview_asset(db, identity, version_id, library_id))


@router.get("/drafts/{lesson_id}/scene", response_class=Response, responses=SVG_RESPONSE)
def draft_scene(db: Db, identity: StaffIdentity, lesson_id: UUID):
    return svg_response(queries.draft_asset(db, identity, lesson_id))


@router.post("/drafts/{lesson_id}/submit", response_model=CommandResult, response_model_exclude_none=True)
def submit(db: Db, identity: StaffIdentity, env: Environment, lesson_id: UUID, body: Submit, key: CommandKey):
    return services.submit_lesson(db, identity, lesson_id, body, key, env.budget)


@router.get("/reviews", response_model=Page[ReviewView])
def reviews(db: Db, identity: StaffIdentity, offset: Offset = 0, limit: Limit = 50, library_id: UUID | None = None,
            state: Literal["submitted", "approved", "rejected"] | None = None):
    return common.reviews(db, identity, offset, limit, library_id, state, kind="lesson")


@router.get("/reviews/{review_id}", response_model=ReviewView)
def review(db: Db, identity: StaffIdentity, review_id: UUID):
    return common.review_view(db, identity, review_id, kind="lesson")


@router.post("/reviews/{review_id}/decision", response_model=CommandResult, response_model_exclude_none=True)
def decide(db: Db, identity: StaffIdentity, env: Environment, review_id: UUID, body: Decision, key: CommandKey):
    return services.decide_lesson(db, identity, review_id, body, key, env.budget)


@router.post("/reviews/{review_id}/publish", response_model=CommandResult, response_model_exclude_none=True)
def publish(db: Db, identity: StaffIdentity, env: Environment, review_id: UUID, body: Revision, key: CommandKey):
    return services.publish_lesson(db, identity, review_id, body, key, env.budget)


@router.get("/publications", response_model=Page[PublicationView])
def publications(db: Db, identity: StaffIdentity, library_id: UUID, offset: Offset = 0, limit: Limit = 50):
    return common.publications(db, identity, library_id, offset, limit, kind="lesson")


@router.post("/publications/{publication_id}/retire", response_model=CommandResult, response_model_exclude_none=True)
def unpublish(db: Db, identity: StaffIdentity, publication_id: UUID, body: Revision, key: CommandKey):
    return lifecycle.retire_publication(db, identity, "lesson", publication_id, body, key)


@router.post("/copies", response_model=CommandResult, response_model_exclude_none=True, status_code=201)
def copy(db: Db, identity: StaffIdentity, env: Environment, body: CopyOrReference, key: CommandKey):
    return services.copy_lesson(db, identity, body, key, env.budget)


@router.post("/references", response_model=CommandResult, response_model_exclude_none=True, status_code=201)
def reference(db: Db, identity: StaffIdentity, env: Environment, body: CopyOrReference, key: CommandKey):
    return services.reference_lesson(db, identity, body, key, env.budget)
