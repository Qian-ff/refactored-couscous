"""Lesson authoring and fixed versions. Formal tasks/progress are exclusively B2."""
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete, func
from sqlmodel import select

from app.domains.content.access import descriptor, require_library
from app.domains.content.models import Library, now
from app.domains.content.lessons.models import (
    Lesson, LessonDraft, LessonDraftQuestion, LessonDraftQuestionOrigin, LessonDraftSource, LessonPublication, LessonQuestion, LessonQuestionOrigin,
    LessonReview, LessonSource, LessonVersion, SceneAsset,
)
from app.domains.content.lessons.scenes import UnsafeScene, validate_svg
from app.domains.content.lessons.schemas import Choice, LessonContent
from app.domains.content.questions.budget import ContentBudget
from app.domains.content.questions.models import Question, QuestionVersion
from app.domains.content.questions.policy import copy_source, has_retained_public_grant, locked_draft, public_source_ids, require_draft, require_parent, require_version, review_manager, staff, version_query
from app.domains.content.questions.schemas import canonical_bytes, fingerprint
from app.domains.content.questions.services import check_lineage as check_question_lineage, checked_version as checked_question
from app.domains.content.questions.sources import check_publication, resolve_sources, retained_sources
from app.domains.content.services import execute_command, locked, require_key
from app.domains.core.commands import check_revision, touch
from app.domains.core.policy import resource_access


def checked_asset(db, asset_id):
    asset = db.get(SceneAsset, asset_id)
    if asset is None:
        raise HTTPException(409, "固定场景资产不存在")
    try:
        safe = validate_svg(asset.svg)
    except UnsafeScene:
        raise HTTPException(409, "固定SVG资产不安全") from None
    if safe.sha256 != asset.content_hash or tuple(asset.view_box) != safe.view_box:
        raise HTTPException(409, "固定场景资产指纹不匹配")
    return asset


def authoring_asset(db, identity, asset_id, retained_asset_id=None):
    staff(identity)
    asset = checked_asset(db, asset_id)
    if asset.id == retained_asset_id:
        return asset
    library = db.get(Library, asset.library_id, populate_existing=True)
    if library.active and resource_access(db, identity, descriptor(library, creator_id=asset.creator_id)).read:
        return asset
    readable = version_query(identity, "lesson", published_only=True).where(LessonVersion.scene_asset_id == asset.id)
    if db.exec(readable.limit(1)).first() is None:
        raise HTTPException(403, "场景资产不存在或无权选用")
    return asset


def validate_question_binding(activity, score, payload):
    expected = "multiple" if payload.kind == "multiple" else "single"
    if (activity.selection != expected or activity.prompt != payload.stem
            or {item.id: item.label for item in activity.options} != {item.id: item.label for item in payload.options}
            or set(score.correct_ids) != set(payload.answer_ids) or score.explanation != payload.explanation):
        raise HTTPException(409, "关卡题目引用必须匹配固定版本的题干、选项及评分；独立改编请取消题库引用")


def validate_question_links(db, identity, content, target, statement, *, enforce_target=True):
    scores = {item.activity_id: item for item in content.scoring}
    result = []
    for activity in content.activities:
        if not isinstance(activity, Choice) or activity.question_version_id is None:
            continue
        if enforce_target:
            version, parent, projection = require_version(db, identity, "question", activity.question_version_id,
                                                          published_only=True, target_library=target)
        else:
            version, parent, projection = copy_source(db, identity, "question", activity.question_version_id, target)
        if parent.retired:
            raise HTTPException(409, "引用题目已停用，不能用于新关卡版本")
        payload, sources = checked_question(db, version)
        validate_question_binding(activity, scores[activity.id], payload)
        check_publication(version.provenance, db.get(Library, parent.library_id), target, statement, sources,
                          reusing=True, public_origin=projection.scope == "platform_public",
                          public_source_ids=public_source_ids(db, "question", version.copied_from_version_id))
        check_question_lineage(db, version.copied_from_version_id, target, statement)
        result.append((activity.id, version.id))
    return result


def version_sources(db, version_id):
    rows = db.exec(select(LessonSource).where(LessonSource.lesson_version_id == version_id).order_by(LessonSource.id)).all()
    grouped = {}
    for row in rows:
        grouped.setdefault(row.activity_id, []).extend(retained_sources(db, [row]))
    return grouped


def asset_has_public_grant(db, asset_id):
    return db.exec(select(LessonPublication.id).join(LessonReview, LessonReview.id == LessonPublication.review_id).join(
        LessonVersion, LessonVersion.id == LessonPublication.version_id).join(
        Library, Library.id == LessonPublication.target_library_id).where(
        LessonVersion.scene_asset_id == asset_id, LessonReview.version_id == LessonVersion.id,
        LessonReview.target_library_id == Library.id, LessonReview.state == "approved",
        Library.scope == "platform_public").limit(1)).first() is not None


def snapshot_hash(content, copied_from, asset, sources, origins):
    return fingerprint({"content": content, "copied_from_version_id": str(copied_from) if copied_from else None,
        "asset_hash": asset.content_hash, "question_origins": sorted((activity_id, str(question_id)) for activity_id, question_id in origins),
        "sources": sorted([
            {"activity_id": activity_id, "version_id": str(row.material_version_id),
             "chunk_id": str(row.chunk_id) if row.chunk_id else None, "locator": row.locator}
            for activity_id, items in sources.items() for row in items],
            key=lambda item: (item["activity_id"], item["version_id"], item["chunk_id"] or ""))})


def checked_lesson(db, version):
    content = LessonContent.model_validate(version.content)
    if content.scene.svg_asset_id != version.scene_asset_id:
        raise HTTPException(409, "场景资产绑定不匹配")
    asset, sources = checked_asset(db, version.scene_asset_id), version_sources(db, version.id)
    expected_sources = {(activity.id, ref.material_version_id, ref.chunk_id) for activity in content.activities for ref in activity.sources}
    refs = db.exec(select(LessonQuestion).where(LessonQuestion.lesson_version_id == version.id)).all()
    expected_questions = {activity.id: activity.question_version_id for activity in content.activities
                          if isinstance(activity, Choice) and activity.question_version_id is not None}
    if len(refs) != len(expected_questions) or {ref.activity_id: ref.question_version_id for ref in refs} != expected_questions:
        raise HTTPException(409, "固定题目绑定不匹配")
    scores = {item.activity_id: item for item in content.scoring}
    for activity in content.activities:
        if isinstance(activity, Choice) and activity.question_version_id is not None:
            question = db.get(QuestionVersion, activity.question_version_id)
            if question is None:
                raise HTTPException(409, "固定题目版本不可用")
            payload, question_sources = checked_question(db, question)
            validate_question_binding(activity, scores[activity.id], payload)
            expected_sources.update((activity.id, ref.material_version_id, ref.chunk_id) for ref in question_sources)
    actual_sources = {(activity_id, ref.material_version_id, ref.chunk_id) for activity_id, refs in sources.items() for ref in refs}
    origins = version_origins(db, version.id)
    if not set(expected_questions.items()) <= set(origins):
        raise HTTPException(409, "固定题目来源谱系缺失")
    if expected_sources != actual_sources or snapshot_hash(version.content, version.copied_from_version_id, asset, sources, origins) != version.payload_hash:
        raise HTTPException(409, "固定关卡快照指纹不匹配")
    return content, asset, sources


def version_origins(db, version_id):
    rows = db.exec(select(LessonQuestionOrigin).where(LessonQuestionOrigin.lesson_version_id == version_id).limit(1001)).all()
    if len(rows) > 1000:
        raise HTTPException(409, "关卡题目来源超过1000项")
    return [(row.activity_id, row.question_version_id) for row in rows]


def check_question_origins(db, origins, target, statement):
    for _activity_id, version_id in origins:
        question = db.get(QuestionVersion, version_id)
        if question is None:
            raise HTTPException(409, "关卡题目来源不可用")
        _payload, refs = checked_question(db, question)
        owner = db.get(Question, question.question_id)
        check_publication(question.provenance, db.get(Library, owner.library_id), target, statement, refs,
            reusing=True, public_origin=has_retained_public_grant(db, "question", question.id),
            public_source_ids=public_source_ids(db, "question", question.copied_from_version_id))
        check_question_lineage(db, question.copied_from_version_id, target, statement)


def check_lineage(db, copied_from, target, statement):
    seen = set()
    while copied_from is not None:
        if copied_from in seen or len(seen) >= 32:
            raise HTTPException(409, "关卡复制来源链无效或超过32层")
        seen.add(copied_from)
        version = db.get(LessonVersion, copied_from)
        if version is None:
            raise HTTPException(409, "关卡复制来源不可用")
        content, asset, sources = checked_lesson(db, version)
        parent = db.get(Lesson, version.lesson_id)
        check_publication(content.provenance.model_dump(mode="json"), db.get(Library, parent.library_id), target,
                          statement, [source for rows in sources.values() for source in rows], reusing=True,
                          public_origin=has_retained_public_grant(db, "lesson", version.id),
                          public_source_ids=public_source_ids(db, "lesson", version.copied_from_version_id))
        check_publication(asset.provenance, db.get(Library, asset.library_id), target, statement,
                          reusing=asset.library_id != target.id, public_origin=asset_has_public_grant(db, asset.id))
        check_question_origins(db, version_origins(db, version.id), target, statement)
        copied_from = version.copied_from_version_id


def _context(db, identity, content, library, *, existing_asset_id=None, copied_from=None):
    inherited = {}
    if copied_from:
        version = db.get(LessonVersion, copied_from)
        if version is None:
            raise HTTPException(409, "关卡复制来源不可用")
        _original, _asset, inherited = checked_lesson(db, version)
    inherited_sources = {(row.material_version_id, row.chunk_id): row for refs in inherited.values() for row in refs}
    asset = authoring_asset(db, identity, content.scene.svg_asset_id, existing_asset_id)
    questions = validate_question_links(db, identity, content, library, "固定题目用于经审核的教学关卡", enforce_target=False)
    question_sources = {}
    for activity_id, question_id in questions:
        question = db.get(QuestionVersion, question_id)
        _payload, refs = checked_question(db, question)
        question_sources[activity_id] = {(ref.material_version_id, ref.chunk_id): ref for ref in refs}
    sources = {}
    for activity in content.activities:
        refs = dict(question_sources.get(activity.id, {}))
        for pointer in activity.sources:
            key = (pointer.material_version_id, pointer.chunk_id)
            if key not in refs:
                refs[key] = inherited_sources[key] if key in inherited_sources else resolve_sources(db, identity, [pointer])[0]
        sources[activity.id] = list(refs.values())
    return asset, sources, questions


def _replace_draft_links(db, lesson_id, sources, questions, inherited_origins=()):
    db.execute(delete(LessonDraftSource).where(LessonDraftSource.lesson_id == lesson_id))
    db.execute(delete(LessonDraftQuestion).where(LessonDraftQuestion.lesson_id == lesson_id))
    for activity_id, refs in sources.items():
        for ref in refs:
            db.add(LessonDraftSource(lesson_id=lesson_id, activity_id=activity_id,
                                     material_version_id=ref.material_version_id, chunk_id=ref.chunk_id))
    for activity_id, version_id in questions:
        db.add(LessonDraftQuestion(lesson_id=lesson_id, activity_id=activity_id, question_version_id=version_id))
    existing = db.exec(select(LessonDraftQuestionOrigin).where(LessonDraftQuestionOrigin.lesson_id == lesson_id).limit(1001)).all()
    old = {(row.activity_id, row.question_version_id) for row in existing}
    added = set(questions) | set(inherited_origins)
    if len(old | added) > 1000:
        raise HTTPException(409, "关卡题目来源超过1000项，请建立独立新关卡")
    for activity_id, version_id in added - old:
        db.add(LessonDraftQuestionOrigin(lesson_id=lesson_id, activity_id=activity_id, question_version_id=version_id))
    return len(old | added)


def create_scene(db, identity, request, key, budget=ContentBudget()):
    staff(identity)
    require_key(key)
    initial = require_library(db, identity, request.library_id, "submit")
    try:
        safe = validate_svg(request.svg)
    except UnsafeScene:
        raise HTTPException(422, "UNSAFE_SVG") from None

    def action():
        library = require_library(db, identity, request.library_id, "submit")
        metadata = request.provenance.model_dump(mode="json")
        asset = SceneAsset(library_id=library.id, svg=safe.svg, content_hash=safe.sha256,
                           provenance=metadata, view_box=list(safe.view_box), creator_id=identity.user.id,
                           retained_bytes=len(safe.svg.encode("utf-8")) + len(canonical_bytes(metadata)))
        db.add(asset)
        budget.admit(db, library.school_id)
        return {"asset_id": str(asset.id)}

    return execute_command(db, identity, initial.school_id, "content.scene.create", key, request.model_dump(mode="json"),
                           action, lambda: require_library(db, identity, request.library_id, "submit"),
                           lambda result: authoring_asset(db, identity, UUID(result["asset_id"])))


def _insert(db, identity, library, content, asset, sources, questions, copied_from=None):
    parent = Lesson(library_id=library.id, creator_id=identity.user.id)
    db.add(parent)
    db.flush()
    value = content.model_dump(mode="json")
    draft = LessonDraft(lesson_id=parent.id, content=value, scene_asset_id=asset.id, copied_from_version_id=copied_from,
                        updated_by=identity.user.id, retained_bytes=len(canonical_bytes(value)) +
                        sum(len(refs) for refs in sources.values()) * 256 + len(questions) * 128)
    db.add(draft)
    db.flush()
    inherited = version_origins(db, copied_from) if copied_from else ()
    count = _replace_draft_links(db, parent.id, sources, questions, inherited)
    draft.retained_bytes += count * 128
    db.add(draft)
    return parent, draft


def create_lesson(db, identity, request, key, budget=ContentBudget()):
    staff(identity)
    require_key(key)
    initial = require_library(db, identity, request.library_id, "submit")

    def action():
        library = require_library(db, identity, request.library_id, "submit")
        asset, sources, questions = _context(db, identity, request.content, library)
        parent, draft = _insert(db, identity, library, request.content, asset, sources, questions)
        budget.admit(db, library.school_id)
        return {"lesson_id": str(parent.id), "revision": draft.revision}

    return execute_command(db, identity, initial.school_id, "content.lesson.create", key, request.model_dump(mode="json"),
                           action, lambda: require_library(db, identity, request.library_id, "submit"),
                           lambda result: require_draft(db, identity, "lesson", UUID(result["lesson_id"])))


def change_lesson(db, identity, lesson_id, request, key, budget=ContentBudget()):
    staff(identity)
    require_key(key)
    _draft, _parent, initial = require_draft(db, identity, "lesson", lesson_id, edit=True)

    def action():
        _current, parent, library = require_draft(db, identity, "lesson", lesson_id, edit=True)
        draft = locked_draft(db, "lesson", lesson_id)
        check_revision(draft, request.revision)
        asset, sources, questions = _context(db, identity, request.content, library,
                                            existing_asset_id=draft.scene_asset_id, copied_from=draft.copied_from_version_id)
        draft.content, draft.scene_asset_id = request.content.model_dump(mode="json"), asset.id
        draft.updated_by, draft.updated_at = identity.user.id, now()
        draft.retained_bytes = len(canonical_bytes(draft.content)) + sum(len(refs) for refs in sources.values()) * 256 + len(questions) * 128
        touch(draft)
        db.add(draft)
        count = _replace_draft_links(db, parent.id, sources, questions)
        draft.retained_bytes += count * 128
        db.add(draft)
        budget.admit(db, library.school_id)
        return {"lesson_id": str(parent.id), "revision": draft.revision}

    return execute_command(db, identity, initial.school_id, "content.lesson.change", key,
                           {"id": str(lesson_id), **request.model_dump(mode="json")}, action,
                           lambda: require_draft(db, identity, "lesson", lesson_id, edit=True))


def discard_lesson(db, identity, lesson_id, request, key):
    staff(identity)
    require_key(key)
    _parent, initial = require_parent(db, identity, "lesson", lesson_id, edit=True)

    def action():
        draft = locked_draft(db, "lesson", lesson_id)
        check_revision(draft, request.revision)
        _replace_draft_links(db, lesson_id, {}, [])
        db.execute(delete(LessonDraftQuestionOrigin).where(LessonDraftQuestionOrigin.lesson_id == lesson_id))
        db.delete(draft)
        return {"lesson_id": str(lesson_id), "draft_discarded": True}

    return execute_command(db, identity, initial.school_id, "content.lesson.discard", key,
                           {"id": str(lesson_id), **request.model_dump()}, action,
                           lambda: require_parent(db, identity, "lesson", lesson_id, edit=True))


def _freeze(db, identity, parent, draft, source):
    content = LessonContent.model_validate(draft.content)
    asset, sources, questions = _context(db, identity, content, source, existing_asset_id=draft.scene_asset_id,
                                        copied_from=draft.copied_from_version_id)
    origin_rows = db.exec(select(LessonDraftQuestionOrigin).where(LessonDraftQuestionOrigin.lesson_id == parent.id).limit(1001)).all()
    origins = [(row.activity_id, row.question_version_id) for row in origin_rows]
    if len(origins) > 1000 or not set(questions) <= set(origins):
        raise HTTPException(409, "关卡题目来源谱系不完整")
    digest = snapshot_hash(draft.content, draft.copied_from_version_id, asset, sources, origins)
    previous = db.exec(select(LessonVersion).where(LessonVersion.lesson_id == parent.id,
                                                 LessonVersion.draft_revision == draft.revision)).first()
    if previous:
        if previous.payload_hash != digest:
            raise HTTPException(409, "已冻结关卡修订不可改写")
        return previous, content, asset, sources
    latest = db.exec(select(func.coalesce(func.max(LessonVersion.version_no), 0)).where(LessonVersion.lesson_id == parent.id)).one()
    version = LessonVersion(lesson_id=parent.id, version_no=int(latest) + 1, draft_revision=draft.revision,
                            content=draft.content, scene_asset_id=asset.id, copied_from_version_id=draft.copied_from_version_id,
                            payload_hash=digest, created_by=identity.user.id, retained_bytes=draft.retained_bytes)
    db.add(version)
    db.flush()
    for activity_id, refs in sources.items():
        for ref in refs:
            db.add(LessonSource(lesson_version_id=version.id, activity_id=activity_id,
                                material_version_id=ref.material_version_id, chunk_id=ref.chunk_id, locator=ref.locator))
    for activity_id, question_id in questions:
        db.add(LessonQuestion(lesson_version_id=version.id, activity_id=activity_id, question_version_id=question_id))
    for activity_id, question_id in origins:
        db.add(LessonQuestionOrigin(lesson_version_id=version.id, activity_id=activity_id, question_version_id=question_id))
    return version, content, asset, sources


def _check_publish(db, identity, version, content, asset, sources, source, target, statement, *, enforce_target=True):
    check_publication(content.provenance.model_dump(mode="json"), source, target, statement,
                      [item for refs in sources.values() for item in refs], reusing=source.id != target.id or version.copied_from_version_id is not None,
                      public_origin=has_retained_public_grant(db, "lesson", version.id),
                      public_source_ids=public_source_ids(db, "lesson", version.copied_from_version_id))
    check_publication(asset.provenance, db.get(Library, asset.library_id), target, statement,
                      reusing=asset.library_id != target.id, public_origin=asset_has_public_grant(db, asset.id))
    check_lineage(db, version.copied_from_version_id, target, statement)
    check_question_origins(db, version_origins(db, version.id), target, statement)
    return validate_question_links(db, identity, content, target, statement, enforce_target=enforce_target)


def submit_lesson(db, identity, lesson_id, request, key, budget=ContentBudget()):
    staff(identity)
    require_key(key)
    initial = require_library(db, identity, request.target_library_id, "submit")

    def authorize():
        require_library(db, identity, request.target_library_id, "submit")
        require_draft(db, identity, "lesson", lesson_id, edit=True)

    def action():
        _current, parent, source = require_draft(db, identity, "lesson", lesson_id, edit=True)
        draft = locked_draft(db, "lesson", lesson_id)
        check_revision(draft, request.revision)
        version, content, asset, sources = _freeze(db, identity, parent, draft, source)
        target = require_library(db, identity, request.target_library_id, "submit")
        _check_publish(db, identity, version, content, asset, sources, source, target, request.authorization_statement)
        review = LessonReview(version_id=version.id, target_library_id=target.id, submitter_id=identity.user.id,
                              authorization_statement=request.authorization_statement)
        db.add(review)
        budget.admit(db, target.school_id)
        if source.school_id != target.school_id:
            budget.admit(db, source.school_id)
        return {"lesson_id": str(parent.id), "version_id": str(version.id), "review_id": str(review.id)}

    return execute_command(db, identity, initial.school_id, "content.lesson.submit", key,
                           {"id": str(lesson_id), **request.model_dump(mode="json")}, action, authorize)


def decide_lesson(db, identity, review_id, request, key, budget=ContentBudget()):
    staff(identity)
    require_key(key)
    _review, initial = review_manager(db, identity, "lesson", review_id)

    def action():
        _review, target = review_manager(db, identity, "lesson", review_id)
        review = locked(db, LessonReview, review_id)
        check_revision(review, request.revision)
        if review.state != "submitted":
            raise HTTPException(409, "审核已决定，请新增提审记录")
        if request.decision == "approved":
            version, parent, _projection = require_version(db, identity, "lesson", review.version_id)
            content, asset, sources = checked_lesson(db, version)
            _check_publish(db, identity, version, content, asset, sources, db.get(Library, parent.library_id), target,
                           review.authorization_statement)
        review.state, review.reason, review.reviewer_id, review.decided_at = request.decision, request.reason, identity.user.id, now()
        touch(review)
        db.add(review)
        budget.admit(db, target.school_id)
        return {"review_id": str(review.id), "state": review.state, "revision": review.revision}

    return execute_command(db, identity, initial.school_id, "content.lesson.decide", key,
                           {"id": str(review_id), **request.model_dump()}, action,
                           lambda: review_manager(db, identity, "lesson", review_id))


def publish_lesson(db, identity, review_id, request, key, budget=ContentBudget()):
    staff(identity)
    require_key(key)
    _review, initial = review_manager(db, identity, "lesson", review_id)

    def action():
        _review, target = review_manager(db, identity, "lesson", review_id)
        review = locked(db, LessonReview, review_id)
        check_revision(review, request.revision)
        if review.state != "approved":
            raise HTTPException(409, "须先批准确切关卡版本")
        version, parent, _projection = require_version(db, identity, "lesson", review.version_id)
        if parent.retired:
            raise HTTPException(409, "关卡已停用，不能新发布")
        content, asset, sources = checked_lesson(db, version)
        _check_publish(db, identity, version, content, asset, sources, db.get(Library, parent.library_id), target,
                       review.authorization_statement)
        previous = db.exec(select(LessonPublication).where(LessonPublication.review_id == review.id)).first()
        if previous:
            if not previous.active:
                raise HTTPException(409, "旧发布已停用，须重新提审")
            return {"publication_id": str(previous.id), "version_id": str(version.id)}
        publication = LessonPublication(review_id=review.id, version_id=version.id, target_library_id=target.id,
                                        published_by=identity.user.id)
        db.add(publication)
        budget.admit(db, target.school_id)
        return {"publication_id": str(publication.id), "version_id": str(version.id)}

    return execute_command(db, identity, initial.school_id, "content.lesson.publish", key,
                           {"id": str(review_id), **request.model_dump()}, action,
                           lambda: review_manager(db, identity, "lesson", review_id))


def copy_lesson(db, identity, request, key, budget=ContentBudget()):
    staff(identity)
    require_key(key)
    initial = require_library(db, identity, request.target_library_id, "submit")

    def authorize():
        target = require_library(db, identity, request.target_library_id, "submit")
        copy_source(db, identity, "lesson", request.source_version_id, target)

    def action():
        target = require_library(db, identity, request.target_library_id, "submit")
        version, parent, projection = copy_source(db, identity, "lesson", request.source_version_id, target)
        if parent.retired:
            raise HTTPException(409, "源关卡已停用")
        content, asset, sources = checked_lesson(db, version)
        target = require_library(db, identity, request.target_library_id, "submit")
        check_publication(content.provenance.model_dump(mode="json"), db.get(Library, parent.library_id), target,
                          request.authorization_statement, [item for refs in sources.values() for item in refs], reusing=True,
                          public_origin=projection.scope == "platform_public",
                          public_source_ids=public_source_ids(db, "lesson", version.copied_from_version_id))
        questions = _check_publish(db, identity, version, content, asset, sources, db.get(Library, parent.library_id), target,
                                   request.authorization_statement, enforce_target=False)
        new_parent, draft = _insert(db, identity, target, content, asset, sources, questions, version.id)
        budget.admit(db, target.school_id)
        return {"lesson_id": str(new_parent.id), "revision": draft.revision}

    return execute_command(db, identity, initial.school_id, "content.lesson.copy", key, request.model_dump(mode="json"),
                           action, authorize, lambda result: require_draft(db, identity, "lesson", UUID(result["lesson_id"])))


def reference_lesson(db, identity, request, key, budget=ContentBudget()):
    staff(identity)
    require_key(key)
    initial = require_library(db, identity, request.target_library_id, "submit")

    def action():
        target = require_library(db, identity, request.target_library_id, "submit")
        version, parent, projection = copy_source(db, identity, "lesson", request.source_version_id, target)
        if parent.retired:
            raise HTTPException(409, "源关卡已停用")
        content, asset, sources = checked_lesson(db, version)
        target = require_library(db, identity, request.target_library_id, "submit")
        check_publication(content.provenance.model_dump(mode="json"), db.get(Library, parent.library_id), target,
                          request.authorization_statement, [item for refs in sources.values() for item in refs], reusing=True,
                          public_origin=projection.scope == "platform_public",
                          public_source_ids=public_source_ids(db, "lesson", version.copied_from_version_id))
        _check_publish(db, identity, version, content, asset, sources, db.get(Library, parent.library_id), target,
                       request.authorization_statement)
        review = LessonReview(version_id=version.id, target_library_id=target.id, submitter_id=identity.user.id,
                              authorization_statement=request.authorization_statement)
        db.add(review)
        budget.admit(db, target.school_id)
        return {"version_id": str(version.id), "review_id": str(review.id)}

    return execute_command(db, identity, initial.school_id, "content.lesson.reference", key, request.model_dump(mode="json"),
                           action, lambda: require_library(db, identity, request.target_library_id, "submit"))
