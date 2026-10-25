"""Private B2 authoring interface. Never mount these scoring DTOs as student HTTP responses."""
from uuid import UUID

from fastapi import HTTPException

from app.domains.content.background_identity import load_identity
from app.domains.content.questions.policy import require_teaching_course, require_version
from app.domains.content.questions.schemas import QuestionPayload, StrictModel, canonical_bytes
from app.domains.content.questions.services import checked_version


class AssessmentQuestion(StrictModel):
    question_id: UUID
    question_version_id: UUID
    payload_hash: str
    payload: QuestionPayload


def resolve_assessment_questions(db, identity, course_id, version_ids):
    """B2 calls inside its publication transaction, then persists its own immutable grading snapshot.

    An existing exam scores its own snapshot; retirement never rewrites that snapshot.
    HTTP handlers must never let a student choose a `purpose` to call this interface.
    """
    current = load_identity(db, identity.user.id, identity.login.id, identity.work_role)
    course = require_teaching_course(db, current, course_id)
    if not 1 <= len(version_ids) <= 1000 or any(not isinstance(value, UUID) for value in version_ids):
        raise HTTPException(422, "须指定1至1000个固定版本UUID")
    if len(set(version_ids)) != len(version_ids):
        raise HTTPException(422, "固定版本不能重复")
    result, used = [], 0
    for version_id in version_ids:
        version, parent, _projection = require_version(db, current, "question", version_id,
                                                      published_only=True, course=course)
        if parent.retired:
            raise HTTPException(409, "题目已停用，不能用于新考核")
        payload, _sources = checked_version(db, version)
        item = AssessmentQuestion(question_id=parent.id, question_version_id=version.id,
                                  payload_hash=version.payload_hash, payload=payload)
        used += len(canonical_bytes(item))
        if used > 16 * 1024 * 1024:
            raise HTTPException(413, "考核内容快照超过16MiB")
        result.append(item)
    return tuple(result)
