"""Private B2 lesson publication snapshots. No student route or unlock bypass is exposed."""
from uuid import UUID

from fastapi import HTTPException

from app.domains.content.lessons.models import LessonQuestion
from app.domains.content.lessons.schemas import StudentLesson, StudentReference, TeacherLessonPreview
from app.domains.content.lessons.projection import student_projection
from app.domains.content.lessons.services import checked_lesson, validate_question_links
from app.domains.content.models import SourceChunk
from app.domains.content.questions.assessment import resolve_assessment_questions
from app.domains.content.questions.policy import live_identity, require_teaching_course, require_version
from app.domains.content.questions.schemas import StrictModel, canonical_bytes
from sqlmodel import select


class SceneSnapshot(StrictModel):
    asset_id: UUID
    content_hash: str
    svg: str
    provenance: dict


class SourceCandidate(StrictModel):
    activity_id: str
    material_version_id: UUID
    chunk_id: UUID | None = None
    locator: dict


class LessonPublicationSnapshot(StrictModel):
    lesson_version_id: UUID
    payload_hash: str
    preview: TeacherLessonPreview
    scene: SceneSnapshot
    source_candidates: tuple[SourceCandidate, ...]


def resolve_lesson_publication(db, identity, course_id, version_ids):
    """B2 stores this private bundle, then gates *both* JSON and SVG with its actual task.

    The B2 student response may use only preview.lesson (with current source filtering),
    never the private review, hashes, or ungated scene bytes in this publication bundle.
    """
    current = live_identity(db, identity)
    course = require_teaching_course(db, current, course_id)
    if (not 1 <= len(version_ids) <= 100 or any(not isinstance(item, UUID) for item in version_ids)
            or len(set(version_ids)) != len(version_ids)):
        raise HTTPException(422, "须指定1至100个互不重复的固定关卡版本UUID")
    result, used = [], 0
    for version_id in version_ids:
        version, parent, target = require_version(db, current, "lesson", version_id, published_only=True, course=course)
        if parent.retired:
            raise HTTPException(409, "关卡已停用，不能用于新学习任务")
        content, asset, sources = checked_lesson(db, version)
        validate_question_links(db, current, content, target, "固定关卡用于本班正式学习任务")
        linked = db.exec(select(LessonQuestion).where(LessonQuestion.lesson_version_id == version.id)).all()
        if linked:
            resolve_assessment_questions(db, current, course.id, tuple(dict.fromkeys(row.question_version_id for row in linked)))
        # Source references require per-learner current authorization; the publication template defaults to none.
        public = student_projection(content, parent.id, version.id)
        item = LessonPublicationSnapshot(lesson_version_id=version.id, payload_hash=version.payload_hash,
            preview=TeacherLessonPreview(lesson=public, review=content.scoring),
            scene=SceneSnapshot(asset_id=asset.id, content_hash=asset.content_hash, svg=asset.svg, provenance=asset.provenance),
            source_candidates=tuple(SourceCandidate(activity_id=activity_id, material_version_id=ref.material_version_id,
                chunk_id=ref.chunk_id, locator=ref.locator) for activity_id, refs in sources.items() for ref in refs))
        used += len(canonical_bytes(item))
        if used > 16 * 1024 * 1024:
            raise HTTPException(413, "学习任务内容快照超过16MiB")
        result.append(item)
    return tuple(result)


def student_lesson_from_snapshot(db, identity, snapshot: LessonPublicationSnapshot) -> StudentLesson:
    """B2 calls only after loading its own authorized task snapshot, never user-posted bundles.

    Retained private provenance is filtered using the learner's current material rights.
    No task/unlock grant is created by this helper and no private scoring field is returned.
    """
    from app.domains.content.access import require_version as require_material
    current = live_identity(db, identity)
    grouped = {}
    for candidate in snapshot.source_candidates:
        try:
            version, material, _projection = require_material(db, current, candidate.material_version_id)
        except HTTPException as error:
            if error.status_code != 403:
                raise
            continue
        locator = candidate.locator
        if candidate.chunk_id is not None:
            chunk = db.get(SourceChunk, candidate.chunk_id)
            if chunk is None or chunk.material_version_id != version.id or chunk.locator != locator:
                raise HTTPException(409, "保留来源页段不匹配")
        kind, position = locator.get("kind"), locator.get("position")
        ref = StudentReference(material_id=material.id, version_id=version.id,
            page=position if kind in {"page", "slide"} else None,
            paragraph=str(position) if kind == "paragraph" else None)
        grouped.setdefault(candidate.activity_id, []).append(ref)
    activities = []
    for activity in snapshot.preview.lesson.activities:
        activities.append(activity.model_copy(update={"source_refs": tuple(grouped.get(activity.id, ()))}))
    return snapshot.preview.lesson.model_copy(update={"activities": tuple(activities)})
