"""Scope in SQL before filtering/counting/paging, then authorize the returned fixed object again."""
from fastapi import HTTPException
from sqlalchemy import and_, false, func, literal, or_, true
from sqlalchemy.orm import aliased
from sqlmodel import select

from app.domains.content.access import columns, descriptor, require_library, require_version as require_material
from app.domains.content.models import Library, SourceChunk
from app.domains.content.questions.models import Question, QuestionDraft, QuestionDraftSource, QuestionPublication, QuestionReview, QuestionSource, QuestionVersion
from app.domains.content.questions.policy import draft_query, require_draft, require_version, staff, version_query
from app.domains.content.questions.schemas import QuestionPayload
from app.domains.content.questions.services import checked_version
from app.domains.content.questions.views import BankView, DraftView, Page, PublicationView, ReviewView, SourceView, VersionView
from app.domains.core.policy import resource_access
from app.domains.core.resource_query import read_resource_predicate


def keyword(text):
    return "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def bounds(q, knowledge, offset, limit):
    if len(q) > 100 or len(knowledge) > 100 or not 0 <= offset <= 2147483647 or not 1 <= limit <= 100:
        raise HTTPException(422, "关键词/知识点最长100字符，limit为1至100，offset须为非负整数")


def readable_sources(db, identity, rows):
    result = []
    for row in rows:
        try:
            version, material, _projection = require_material(db, identity, row.material_version_id)
        except HTTPException as error:
            if error.status_code != 403:
                raise
            continue
        locator = {}
        if row.chunk_id is not None:
            chunk = db.get(SourceChunk, row.chunk_id)
            if chunk is None or chunk.material_version_id != version.id:
                raise HTTPException(409, "来源页段与版本不匹配")
            locator = dict(chunk.locator)
        result.append(SourceView(material_id=material.id, material_version_id=version.id,
                                  chunk_id=row.chunk_id, locator=locator))
    return tuple(result)


def draft_view(db, identity, question_id):
    row, parent, library = require_draft(db, identity, "question", question_id)
    access = resource_access(db, identity, descriptor(library, creator_id=parent.creator_id))
    rows = db.exec(select(QuestionDraftSource).where(QuestionDraftSource.question_id == parent.id).order_by(QuestionDraftSource.id)).all()
    return DraftView(question_id=parent.id, library_id=library.id, revision=row.revision, parent_revision=parent.revision,
                     retired=parent.retired, can_edit=not parent.retired and (
                         access.review or (access.submit and parent.creator_id == identity.user.id)),
                     payload=QuestionPayload.model_validate(row.payload), provenance=row.provenance,
                     sources=readable_sources(db, identity, rows), updated_at=row.updated_at)


def version_view(db, identity, version_id, library_id=None):
    row, parent, projection = require_version(db, identity, "question", version_id, library_id)
    payload, _sources = checked_version(db, row)
    refs = db.exec(select(QuestionSource).where(QuestionSource.question_version_id == row.id).order_by(QuestionSource.id)).all()
    return VersionView(question_id=parent.id, version_id=row.id, library_id=projection.id, version_no=row.version_no,
                       payload=payload, provenance=row.provenance, sources=readable_sources(db, identity, refs), created_at=row.created_at)


def drafts(db, identity, q="", knowledge="", offset=0, limit=50, library_id=None):
    staff(identity)
    bounds(q, knowledge, offset, limit)
    query = draft_query(identity, "question")
    if library_id is not None:
        query = query.where(Question.library_id == library_id)
    if q:
        query = query.where(QuestionDraft.payload["stem"].astext.ilike(keyword(q), escape="\\"))
    if knowledge:
        query = query.where(QuestionDraft.payload["knowledge_points"].contains([knowledge]))
    total = db.exec(select(func.count()).select_from(query.subquery())).one()
    rows = db.exec(query.order_by(QuestionDraft.updated_at.desc(), QuestionDraft.question_id).offset(offset).limit(limit)).all()
    return Page[DraftView](items=tuple(draft_view(db, identity, row.question_id) for row in rows), total=total, offset=offset, limit=limit)


def versions(db, identity, q="", knowledge="", offset=0, limit=50, library_id=None, question_id=None):
    staff(identity)
    bounds(q, knowledge, offset, limit)
    query = version_query(identity, "question", library_id)
    if question_id is not None:
        query = query.where(QuestionVersion.question_id == question_id)
    if q:
        query = query.where(QuestionVersion.payload["stem"].astext.ilike(keyword(q), escape="\\"))
    if knowledge:
        query = query.where(QuestionVersion.payload["knowledge_points"].contains([knowledge]))
    total = db.exec(select(func.count()).select_from(query.subquery())).one()
    rows = db.exec(query.order_by(QuestionVersion.created_at.desc(), QuestionVersion.id).offset(offset).limit(limit)).all()
    return Page[VersionView](items=tuple(version_view(db, identity, row.id, library_id) for row in rows), total=total, offset=offset, limit=limit)


def banks(db, identity, q="", offset=0, limit=50, include_inactive=False):
    staff(identity)
    bounds(q, "", offset, limit)
    bank = aliased(Library)
    manager = read_resource_predicate(identity, columns(bank, creator_id=literal(None), published=false()))
    own = select(Question.id).where(Question.library_id == bank.id,
        read_resource_predicate(identity, columns(bank, creator_id=Question.creator_id, published=false()))).correlate(bank).exists()
    published = select(QuestionPublication.id).join(QuestionReview, QuestionReview.id == QuestionPublication.review_id).where(
        QuestionPublication.target_library_id == bank.id, QuestionPublication.active.is_(True), QuestionReview.state == "approved",
        QuestionReview.version_id == QuestionPublication.version_id, QuestionReview.target_library_id == bank.id,
        read_resource_predicate(identity, columns(bank, creator_id=literal(None), published=true()))).correlate(bank).exists()
    allowed = and_(bank.active.is_(True), or_(manager, own, published))
    if include_inactive:
        allowed = or_(allowed, manager)
    query = select(bank).where(allowed)
    if q:
        query = query.where(bank.title.ilike(keyword(q), escape="\\"))
    total = db.exec(select(func.count()).select_from(query.subquery())).one()
    rows = db.exec(query.order_by(bank.title, bank.id).offset(offset).limit(limit)).all()
    items = []
    for row in rows:
        access = resource_access(db, identity, descriptor(row))
        items.append(BankView(id=row.id, title=row.title, scope=row.scope, audience=row.audience, active=row.active,
                              revision=row.revision, can_submit=access.submit, can_review=access.review))
    return Page[BankView](items=tuple(items), total=total, offset=offset, limit=limit)


def review_view(db, identity, review_id):
    staff(identity)
    row = db.get(QuestionReview, review_id)
    if row is None:
        raise HTTPException(403, "审核记录不存在或无权读取")
    _version, _parent, _projection = require_version(db, identity, "question", row.version_id)
    target = db.get(Library, row.target_library_id)
    access = resource_access(db, identity, descriptor(target))
    if not target.active or not (access.review or row.submitter_id == identity.user.id):
        raise HTTPException(403, "无权读取审核记录")
    return ReviewView(id=row.id, version_id=row.version_id, target_library_id=target.id, state=row.state,
                      revision=row.revision, authorization_statement=row.authorization_statement, reason=row.reason,
                      submitted_at=row.submitted_at, decided_at=row.decided_at)


def reviews(db, identity, offset=0, limit=50, library_id=None, state=None):
    staff(identity)
    bounds("", "", offset, limit)
    manager = read_resource_predicate(identity, columns(Library, creator_id=literal(None), published=false()))
    readable_version = version_query(identity, "question").with_only_columns(QuestionVersion.id)
    query = select(QuestionReview).join(Library, Library.id == QuestionReview.target_library_id).where(
        Library.active.is_(True), or_(manager, QuestionReview.submitter_id == identity.user.id),
        QuestionReview.version_id.in_(readable_version))
    if library_id is not None:
        query = query.where(QuestionReview.target_library_id == library_id)
    if state is not None:
        if state not in {"submitted", "approved", "rejected"}:
            raise HTTPException(422, "审核状态无效")
        query = query.where(QuestionReview.state == state)
    total = db.exec(select(func.count()).select_from(query.subquery())).one()
    rows = db.exec(query.order_by(QuestionReview.submitted_at.desc(), QuestionReview.id).offset(offset).limit(limit)).all()
    return Page[ReviewView](items=tuple(review_view(db, identity, row.id) for row in rows), total=total, offset=offset, limit=limit)


def publications(db, identity, library_id, offset=0, limit=50):
    staff(identity)
    bounds("", "", offset, limit)
    require_library(db, identity, library_id, "review")
    query = select(QuestionPublication).where(QuestionPublication.target_library_id == library_id)
    total = db.exec(select(func.count()).select_from(query.subquery())).one()
    rows = db.exec(query.order_by(QuestionPublication.published_at.desc(), QuestionPublication.id).offset(offset).limit(limit)).all()
    return Page[PublicationView](items=tuple(PublicationView(id=row.id, version_id=row.version_id,
        target_library_id=row.target_library_id, active=row.active, revision=row.revision,
        published_at=row.published_at, retired_at=row.retired_at) for row in rows), total=total, offset=offset, limit=limit)
