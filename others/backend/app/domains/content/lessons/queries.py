"""Staff editing/preview only. B2 owns every official student task and asset response."""
from fastapi import HTTPException
from sqlalchemy import func
from sqlmodel import select

from app.domains.content.access import descriptor, require_version as require_material
from app.domains.content.lessons.models import Lesson, LessonDraft, LessonVersion
from app.domains.content.lessons.projection import student_projection
from app.domains.content.lessons.schemas import LessonContent, StudentReference, TeacherLessonPreview
from app.domains.content.lessons.services import checked_asset, checked_lesson
from app.domains.content.lessons.views import DraftView, VersionView
from app.domains.content.questions.policy import draft_query, require_draft, require_version, staff, version_query
from app.domains.content.questions.queries import bounds, keyword
from app.domains.content.questions.views import Page
from app.domains.content.models import SourceChunk
from app.domains.core.policy import resource_access


def _readable_pointer(db, identity, pointer):
    try:
        version, material, _projection = require_material(db, identity, pointer.material_version_id)
    except HTTPException as error:
        if error.status_code != 403:
            raise
        return None
    locator = getattr(pointer, "locator", {})
    if pointer.chunk_id is not None:
        chunk = db.get(SourceChunk, pointer.chunk_id)
        if chunk is None or chunk.material_version_id != version.id:
            raise HTTPException(409, "来源页段与固定版本不匹配")
        locator = chunk.locator
    kind, position = locator.get("kind"), locator.get("position")
    return StudentReference(material_id=material.id, version_id=version.id,
        page=position if kind in {"page", "slide"} else None, paragraph=str(position) if kind == "paragraph" else None)


def draft_view(db, identity, lesson_id):
    row, parent, library = require_draft(db, identity, "lesson", lesson_id)
    content = LessonContent.model_validate(row.content)
    checked_asset(db, row.scene_asset_id)
    # The copied draft is readable, but retained provenance does not disclose inaccessible material IDs.
    activities = []
    for activity in content.activities:
        refs = tuple(pointer for pointer in activity.sources if _readable_pointer(db, identity, pointer) is not None)
        activities.append(activity.model_copy(update={"sources": refs}))
    content = content.model_copy(update={"activities": tuple(activities)})
    access = resource_access(db, identity, descriptor(library, creator_id=parent.creator_id))
    return DraftView(lesson_id=parent.id, library_id=library.id, revision=row.revision, parent_revision=parent.revision,
                     retired=parent.retired, can_edit=not parent.retired and (
                         access.review or (access.submit and parent.creator_id == identity.user.id)),
                     content=content, updated_at=row.updated_at)


def version_view(db, identity, version_id, library_id=None):
    version, parent, projection = require_version(db, identity, "lesson", version_id, library_id)
    content, _asset, _sources = checked_lesson(db, version)
    return VersionView(lesson_id=parent.id, version_id=version.id, library_id=projection.id,
                       version_no=version.version_no, title=content.title, required=content.required, created_at=version.created_at)


def preview(db, identity, version_id, library_id=None):
    version, parent, _projection = require_version(db, identity, "lesson", version_id, library_id)
    content, _asset, sources = checked_lesson(db, version)
    readable = {}
    for activity_id, refs in sources.items():
        readable[activity_id] = tuple(value for row in refs if (value := _readable_pointer(db, identity, row)) is not None)
    return TeacherLessonPreview(lesson=student_projection(content, parent.id, version.id, readable), review=content.scoring)


def preview_asset(db, identity, version_id, library_id=None):
    version, _parent, _projection = require_version(db, identity, "lesson", version_id, library_id)
    _content, asset, _sources = checked_lesson(db, version)
    return asset.svg.encode("utf-8"), asset.content_hash


def draft_asset(db, identity, lesson_id):
    row, _parent, _library = require_draft(db, identity, "lesson", lesson_id)
    asset = checked_asset(db, row.scene_asset_id)
    return asset.svg.encode("utf-8"), asset.content_hash


def drafts(db, identity, q="", offset=0, limit=50, library_id=None):
    staff(identity)
    bounds(q, "", offset, limit)
    query = draft_query(identity, "lesson")
    if library_id is not None:
        query = query.where(Lesson.library_id == library_id)
    if q:
        query = query.where(LessonDraft.content["title"].astext.ilike(keyword(q), escape="\\"))
    total = db.exec(select(func.count()).select_from(query.subquery())).one()
    rows = db.exec(query.order_by(LessonDraft.updated_at.desc(), LessonDraft.lesson_id).offset(offset).limit(limit)).all()
    return Page[DraftView](items=tuple(draft_view(db, identity, row.lesson_id) for row in rows), total=total, offset=offset, limit=limit)


def versions(db, identity, q="", offset=0, limit=50, library_id=None, lesson_id=None):
    staff(identity)
    bounds(q, "", offset, limit)
    query = version_query(identity, "lesson", library_id)
    if lesson_id is not None:
        query = query.where(LessonVersion.lesson_id == lesson_id)
    if q:
        query = query.where(LessonVersion.content["title"].astext.ilike(keyword(q), escape="\\"))
    total = db.exec(select(func.count()).select_from(query.subquery())).one()
    rows = db.exec(query.order_by(LessonVersion.created_at.desc(), LessonVersion.id).offset(offset).limit(limit)).all()
    return Page[VersionView](items=tuple(version_view(db, identity, row.id, library_id) for row in rows), total=total, offset=offset, limit=limit)
