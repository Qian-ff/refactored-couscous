"""Question commands. Immutable version reads never serialize SQLModel objects to students."""
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete, func
from sqlmodel import select

from app.domains.content.access import require_library
from app.domains.content.models import Library, now
from app.domains.content.questions.budget import ContentBudget
from app.domains.content.questions.models import (
    Question, QuestionDraft, QuestionDraftSource, QuestionPublication, QuestionReview, QuestionSource, QuestionVersion,
)
from app.domains.content.questions.policy import copy_source, draft_query, has_retained_public_grant, public_source_ids, require_draft, require_parent, require_version, review_manager, staff
from app.domains.content.questions.schemas import DraftContent, QuestionPayload, SourcePointer, canonical_bytes, fingerprint
from app.domains.content.questions.sources import check_publication, resolve_sources, retained_sources
from app.domains.content.services import execute_command, locked, require_key
from app.domains.core.commands import check_revision, touch


def version_sources(db, version_id):
    rows = db.exec(select(QuestionSource).where(QuestionSource.question_version_id == version_id).order_by(QuestionSource.id)).all()
    return retained_sources(db, rows)


def snapshot_hash(payload, provenance, copied_from, sources):
    return fingerprint({"payload": payload, "provenance": provenance,
                        "copied_from_version_id": str(copied_from) if copied_from else None,
                        "sources": sorted([{"version_id": str(row.material_version_id),
                            "chunk_id": str(row.chunk_id) if row.chunk_id else None, "locator": row.locator}
                            for row in sources], key=lambda item: (item["version_id"], item["chunk_id"] or ""))})


def checked_version(db, version):
    payload = QuestionPayload.model_validate(version.payload)
    sources = version_sources(db, version.id)
    if snapshot_hash(version.payload, version.provenance, version.copied_from_version_id, sources) != version.payload_hash:
        raise HTTPException(409, "固定题目内容指纹不匹配")
    return payload, sources


def duplicate(db, identity, library_id, payload, except_question=None):
    query = draft_query(identity, "question").where(Question.library_id == library_id,
        Question.retired.is_(False), QuestionDraft.duplicate_hash == payload.duplicate_hash())
    if except_question is not None:
        query = query.where(Question.id != except_question)
    if db.exec(query).first() is not None:
        raise HTTPException(409, "有权题库内已有相同题干和选项，请核对重复或答案冲突")


def _sources_for_draft(db, identity, pointers, copied_from=None):
    inherited = {}
    if copied_from:
        # Copying creates an independent draft. Retained provenance is not a new material read grant.
        original = db.get(QuestionVersion, copied_from)
        if original is None:
            raise HTTPException(409, "复制来源固定版本不可用")
        checked_version(db, original)
        inherited = {(row.material_version_id, row.chunk_id): row for row in version_sources(db, original.id)}
    result = []
    for pointer in pointers:
        key = (pointer.material_version_id, pointer.chunk_id)
        result.append(inherited[key] if key in inherited else resolve_sources(db, identity, [pointer])[0])
    return result


def check_lineage(db, version_id, target, statement):
    """Copied drafts cannot launder the immutable source's license or original school boundary."""
    seen = set()
    while version_id is not None:
        if version_id in seen or len(seen) >= 32:
            raise HTTPException(409, "复制来源链无效或超过32层")
        seen.add(version_id)
        version = db.get(QuestionVersion, version_id)
        if version is None:
            raise HTTPException(409, "复制来源固定版本不可用")
        _payload, sources = checked_version(db, version)
        parent = db.get(Question, version.question_id)
        check_publication(version.provenance, db.get(Library, parent.library_id), target, statement, sources,
                          reusing=True, public_origin=has_retained_public_grant(db, "question", version.id),
                          public_source_ids=public_source_ids(db, "question", version.copied_from_version_id))
        version_id = version.copied_from_version_id


def _replace_sources(db, question_id, sources):
    db.execute(delete(QuestionDraftSource).where(QuestionDraftSource.question_id == question_id))
    for source in sources:
        db.add(QuestionDraftSource(question_id=question_id, material_version_id=source.material_version_id, chunk_id=source.chunk_id))


def _insert_draft(db, identity, library, content, sources, *, copied_from=None):
    duplicate(db, identity, library.id, content.payload)
    parent = Question(library_id=library.id, creator_id=identity.user.id)
    db.add(parent)
    db.flush()
    payload, provenance = content.payload.model_dump(mode="json"), content.provenance.model_dump(mode="json")
    draft = QuestionDraft(question_id=parent.id, payload=payload, provenance=provenance,
                          copied_from_version_id=copied_from, duplicate_hash=content.payload.duplicate_hash(),
                          updated_by=identity.user.id,
                          retained_bytes=len(canonical_bytes({"payload": payload, "provenance": provenance})) + len(sources) * 256)
    db.add(draft)
    db.flush()
    _replace_sources(db, parent.id, sources)
    return parent, draft


def create_question(db, identity, request, key, budget=ContentBudget()):
    staff(identity)
    require_key(key)
    initial = require_library(db, identity, request.library_id, "submit")

    def action():
        library = require_library(db, identity, request.library_id, "submit")
        sources = resolve_sources(db, identity, request.sources)
        parent, draft = _insert_draft(db, identity, library, request, sources)
        budget.admit(db, library.school_id)
        return {"question_id": str(parent.id), "revision": draft.revision}

    return execute_command(db, identity, initial.school_id, "content.question.create", key,
                           request.model_dump(mode="json"), action,
                           lambda: require_library(db, identity, request.library_id, "submit"),
                           lambda result: require_draft(db, identity, "question", UUID(result["question_id"])))


def change_question(db, identity, question_id, request, key, budget=ContentBudget()):
    staff(identity)
    require_key(key)
    _draft, _parent, initial = require_draft(db, identity, "question", question_id, edit=True)

    def action():
        _current, parent, library = require_draft(db, identity, "question", question_id, edit=True)
        draft = locked(db, QuestionDraft, question_id)
        check_revision(draft, request.revision)
        duplicate(db, identity, library.id, request.payload, question_id)
        sources = _sources_for_draft(db, identity, request.sources, draft.copied_from_version_id)
        draft.payload, draft.provenance = request.payload.model_dump(mode="json"), request.provenance.model_dump(mode="json")
        draft.updated_by, draft.updated_at = identity.user.id, now()
        draft.retained_bytes = len(canonical_bytes({"payload": draft.payload, "provenance": draft.provenance})) + len(sources) * 256
        touch(draft)
        db.add(draft)
        _replace_sources(db, parent.id, sources)
        budget.admit(db, library.school_id)
        return {"question_id": str(parent.id), "revision": draft.revision}

    return execute_command(db, identity, initial.school_id, "content.question.change", key,
                           {"id": str(question_id), **request.model_dump(mode="json")}, action,
                           lambda: require_draft(db, identity, "question", question_id, edit=True))


def discard_draft(db, identity, question_id, request, key):
    staff(identity)
    require_key(key)
    _parent, initial = require_parent(db, identity, "question", question_id, edit=True)

    def authorize():
        # Replays retain authorization even after the mutable draft has been removed.
        require_parent(db, identity, "question", question_id, edit=True)

    def action():
        draft = locked(db, QuestionDraft, question_id)
        check_revision(draft, request.revision)
        _replace_sources(db, question_id, [])
        db.delete(draft)
        return {"question_id": str(question_id), "draft_discarded": True}

    return execute_command(db, identity, initial.school_id, "content.question.discard", key,
                           {"id": str(question_id), **request.model_dump()}, action, authorize)


def _freeze(db, identity, parent, draft):
    pointers = db.exec(select(QuestionDraftSource).where(QuestionDraftSource.question_id == parent.id).order_by(QuestionDraftSource.id)).all()
    sources = _sources_for_draft(db, identity, pointers, draft.copied_from_version_id)
    QuestionPayload.model_validate(draft.payload)
    digest = snapshot_hash(draft.payload, draft.provenance, draft.copied_from_version_id, sources)
    previous = db.exec(select(QuestionVersion).where(QuestionVersion.question_id == parent.id,
                                                   QuestionVersion.draft_revision == draft.revision)).first()
    if previous:
        if previous.payload_hash != digest:
            raise HTTPException(409, "已冻结修订不可改写")
        return previous, sources
    latest = db.exec(select(func.coalesce(func.max(QuestionVersion.version_no), 0)).where(QuestionVersion.question_id == parent.id)).one()
    version = QuestionVersion(question_id=parent.id, version_no=int(latest) + 1, draft_revision=draft.revision,
                              payload=draft.payload, provenance=draft.provenance, copied_from_version_id=draft.copied_from_version_id,
                              payload_hash=digest, created_by=identity.user.id,
                              retained_bytes=len(canonical_bytes({"payload": draft.payload, "provenance": draft.provenance})) + len(sources) * 256)
    db.add(version)
    db.flush()
    for source in sources:
        db.add(QuestionSource(question_version_id=version.id, material_version_id=source.material_version_id,
                              chunk_id=source.chunk_id, locator=source.locator))
    return version, sources


def submit_question(db, identity, question_id, request, key, budget=ContentBudget()):
    staff(identity)
    require_key(key)
    initial = require_library(db, identity, request.target_library_id, "submit")

    def authorize():
        require_library(db, identity, request.target_library_id, "submit")
        require_draft(db, identity, "question", question_id, edit=True)

    def action():
        _current, parent, source = require_draft(db, identity, "question", question_id, edit=True)
        draft = locked(db, QuestionDraft, question_id)
        check_revision(draft, request.revision)
        version, sources = _freeze(db, identity, parent, draft)
        target = require_library(db, identity, request.target_library_id, "submit")
        check_publication(version.provenance, source, target, request.authorization_statement, sources,
                          reusing=source.id != target.id or draft.copied_from_version_id is not None,
                          public_origin=has_retained_public_grant(db, "question", version.id),
                          public_source_ids=public_source_ids(db, "question", version.copied_from_version_id))
        check_lineage(db, draft.copied_from_version_id, target, request.authorization_statement)
        review = QuestionReview(version_id=version.id, target_library_id=target.id, submitter_id=identity.user.id,
                                authorization_statement=request.authorization_statement)
        db.add(review)
        budget.admit(db, target.school_id)
        # Frozen input belongs to the source school, while the review is attributed to the target scope.
        if source.school_id != target.school_id:
            budget.admit(db, source.school_id)
        return {"question_id": str(parent.id), "version_id": str(version.id), "review_id": str(review.id)}

    return execute_command(db, identity, initial.school_id, "content.question.submit", key,
                           {"id": str(question_id), **request.model_dump(mode="json")}, action, authorize)


def decide_question(db, identity, review_id, request, key, budget=ContentBudget()):
    staff(identity)
    require_key(key)
    _review, initial = review_manager(db, identity, "question", review_id)

    def action():
        _review, target = review_manager(db, identity, "question", review_id)
        review = locked(db, QuestionReview, review_id)
        check_revision(review, request.revision)
        if review.state != "submitted":
            raise HTTPException(409, "审核已决定，请新增提审记录")
        if request.decision == "approved":
            version, parent, _projection = require_version(db, identity, "question", review.version_id)
            _payload, sources = checked_version(db, version)
            source = db.get(Library, parent.library_id)
            check_publication(version.provenance, source, target, review.authorization_statement, sources,
                              reusing=source.id != target.id or version.copied_from_version_id is not None,
                              public_origin=has_retained_public_grant(db, "question", version.id),
                              public_source_ids=public_source_ids(db, "question", version.copied_from_version_id))
            check_lineage(db, version.copied_from_version_id, target, review.authorization_statement)
        review.state, review.reason = request.decision, request.reason
        review.reviewer_id, review.decided_at = identity.user.id, now()
        touch(review)
        db.add(review)
        budget.admit(db, target.school_id)
        return {"review_id": str(review.id), "state": review.state, "revision": review.revision}

    return execute_command(db, identity, initial.school_id, "content.question.decide", key,
                           {"id": str(review_id), **request.model_dump()}, action,
                           lambda: review_manager(db, identity, "question", review_id))


def publish_question(db, identity, review_id, request, key, budget=ContentBudget()):
    staff(identity)
    require_key(key)
    _review, initial = review_manager(db, identity, "question", review_id)

    def action():
        _review, target = review_manager(db, identity, "question", review_id)
        review = locked(db, QuestionReview, review_id)
        check_revision(review, request.revision)
        if review.state != "approved":
            raise HTTPException(409, "须先批准确切题目版本")
        version, parent, _projection = require_version(db, identity, "question", review.version_id)
        _payload, sources = checked_version(db, version)
        if parent.retired:
            raise HTTPException(409, "题目已停用，不能新发布")
        source = db.get(Library, parent.library_id)
        check_publication(version.provenance, source, target, review.authorization_statement, sources,
                          reusing=source.id != target.id or version.copied_from_version_id is not None,
                          public_origin=has_retained_public_grant(db, "question", version.id),
                          public_source_ids=public_source_ids(db, "question", version.copied_from_version_id))
        check_lineage(db, version.copied_from_version_id, target, review.authorization_statement)
        previous = db.exec(select(QuestionPublication).where(QuestionPublication.review_id == review.id)).first()
        if previous:
            if not previous.active:
                raise HTTPException(409, "旧发布已停用，须重新提审")
            return {"publication_id": str(previous.id), "version_id": str(previous.version_id)}
        publication = QuestionPublication(review_id=review.id, version_id=version.id, target_library_id=target.id,
                                          published_by=identity.user.id)
        db.add(publication)
        budget.admit(db, target.school_id)
        return {"publication_id": str(publication.id), "version_id": str(version.id)}

    return execute_command(db, identity, initial.school_id, "content.question.publish", key,
                           {"id": str(review_id), **request.model_dump()}, action,
                           lambda: review_manager(db, identity, "question", review_id))


def copy_question(db, identity, request, key, budget=ContentBudget()):
    staff(identity)
    require_key(key)
    initial = require_library(db, identity, request.target_library_id, "submit")

    def authorize():
        target = require_library(db, identity, request.target_library_id, "submit")
        copy_source(db, identity, "question", request.source_version_id, target)

    def action():
        target = require_library(db, identity, request.target_library_id, "submit")
        version, parent, projection = copy_source(db, identity, "question", request.source_version_id, target)
        if parent.retired:
            raise HTTPException(409, "源题目已停用")
        payload, sources = checked_version(db, version)
        target = require_library(db, identity, request.target_library_id, "submit")
        check_publication(version.provenance, db.get(Library, parent.library_id), target,
                          request.authorization_statement, sources, reusing=True, public_origin=projection.scope == "platform_public",
                          public_source_ids=public_source_ids(db, "question", version.copied_from_version_id))
        check_lineage(db, version.copied_from_version_id, target, request.authorization_statement)
        content = DraftContent(payload=payload, provenance=version.provenance,
                               sources=tuple(SourcePointer(material_version_id=row.material_version_id, chunk_id=row.chunk_id) for row in sources))
        new_parent, draft = _insert_draft(db, identity, target, content, sources, copied_from=version.id)
        budget.admit(db, target.school_id)
        return {"question_id": str(new_parent.id), "revision": draft.revision}

    return execute_command(db, identity, initial.school_id, "content.question.copy", key,
                           request.model_dump(mode="json"), action, authorize,
                           lambda result: require_draft(db, identity, "question", UUID(result["question_id"])))


def reference_question(db, identity, request, key, budget=ContentBudget()):
    staff(identity)
    require_key(key)
    initial = require_library(db, identity, request.target_library_id, "submit")

    def action():
        target = require_library(db, identity, request.target_library_id, "submit")
        version, parent, projection = copy_source(db, identity, "question", request.source_version_id, target)
        if parent.retired:
            raise HTTPException(409, "源题目已停用")
        _payload, sources = checked_version(db, version)
        target = require_library(db, identity, request.target_library_id, "submit")
        check_publication(version.provenance, db.get(Library, parent.library_id), target,
                          request.authorization_statement, sources, reusing=True, public_origin=projection.scope == "platform_public",
                          public_source_ids=public_source_ids(db, "question", version.copied_from_version_id))
        check_lineage(db, version.copied_from_version_id, target, request.authorization_statement)
        review = QuestionReview(version_id=version.id, target_library_id=target.id, submitter_id=identity.user.id,
                                authorization_statement=request.authorization_statement)
        db.add(review)
        budget.admit(db, target.school_id)
        return {"version_id": str(version.id), "review_id": str(review.id)}

    return execute_command(db, identity, initial.school_id, "content.question.reference", key,
                           request.model_dump(mode="json"), action,
                           lambda: require_library(db, identity, request.target_library_id, "submit"))
