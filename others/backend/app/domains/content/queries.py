"""Authorization precedes counts, newest-version selection, and all public projections."""
import json

from fastapi import HTTPException
from sqlalchemy import and_, false, func, literal, or_, true
from sqlalchemy.orm import aliased
from sqlmodel import select

from app.domains.core.policy import resource_access
from app.domains.core.resource_query import read_resource_predicate
from app.domains.content.access import columns, descriptor, readable_versions, require_library, require_version, submit_libraries
from app.domains.content.models import ContentUpload, Library, Material, MaterialPublication, MaterialReview, MaterialVersion, SourceChunk
from app.domains.content.services import warnings_hash
from app.domains.content.views import ChunkPage, ChunkView, LibraryView, Page, SubmitTarget, VersionView


def keyword(value):
    return "%" + value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def library_query(identity, include_inactive=False):
    outer = aliased(Library)
    manager = read_resource_predicate(identity, columns(outer, creator_id=literal(None), published=false()))
    own_source = select(MaterialVersion.id).join(Material, Material.id == MaterialVersion.material_id).where(
        Material.library_id == outer.id, read_resource_predicate(identity, columns(
            outer, creator_id=Material.creator_id, published=false()))).correlate(outer).exists()
    publication = select(MaterialPublication.id).join(MaterialReview, MaterialReview.id == MaterialPublication.review_id).where(
        MaterialPublication.target_library_id == outer.id, MaterialPublication.active.is_(True),
        MaterialReview.state == "approved", MaterialReview.version_id == MaterialPublication.version_id,
        MaterialReview.target_library_id == outer.id,
        read_resource_predicate(identity, columns(outer, creator_id=literal(None), published=true())),
    ).correlate(outer).exists()
    allowed = and_(outer.active.is_(True), or_(manager, own_source, publication))
    if include_inactive:
        allowed = or_(allowed, manager)
    return select(outer).where(allowed), outer


def libraries(db, identity, q, offset, limit, include_inactive=False):
    query, model = library_query(identity, include_inactive)
    if q:
        query = query.where(model.title.ilike(keyword(q), escape="\\"))
    count = db.exec(select(func.count()).select_from(query.subquery())).one()
    rows = db.exec(query.order_by(model.title, model.id).offset(offset).limit(limit)).all()
    items = []
    for row in rows:
        access = resource_access(db, identity, descriptor(row))
        items.append(LibraryView(id=row.id, title=row.title, scope=row.scope, audience=row.audience,
                                 active=row.active, revision=row.revision, can_submit=access.submit,
                                 can_review=access.review))
    return Page[LibraryView](items=items, total=count, offset=offset, limit=limit)


def targets(db, identity, q, offset, limit):
    query = submit_libraries(identity)
    if q:
        query = query.where(Library.title.ilike(keyword(q), escape="\\"))
    rows = db.exec(query.order_by(Library.title, Library.id).offset(offset).limit(limit)).all()
    result = []
    for row in rows:
        require_library(db, identity, row.id, "submit")
        result.append(SubmitTarget(id=row.id, title=row.title, scope=row.scope))
    return result


def version_view(db, identity, version_id, library_id=None):
    version, material, projection = require_version(db, identity, version_id, library_id)
    source = db.get(Library, material.library_id)
    source_access = resource_access(db, identity, descriptor(source, creator_id=material.creator_id))
    review_access = resource_access(db, identity, descriptor(projection)).review
    can_see_metadata = review_access or (source_access.read and source_access.submit and material.creator_id == identity.user.id)
    upload = db.get(ContentUpload, version.upload_id) if version.upload_id else None
    return VersionView(material_id=material.id, version_id=version.id, library_id=projection.id,
                       title=material.title, version_no=version.version_no, input_kind=version.input_kind,
                       extraction_state=version.extraction_state, original_name=upload.original_name if upload else None,
                       file_bytes=upload.expected_bytes if upload else None, content_hash=version.content_hash,
                       parser_version=version.parser_version, created_at=version.created_at,
                       warnings=version.warnings, warning_hash=warnings_hash(version),
                       source_metadata=version.source_metadata if can_see_metadata else None)


def versions(db, identity, q, offset, limit, library_id=None, material_id=None, newest_only=False):
    query = readable_versions(identity, library_id).outerjoin(ContentUpload, ContentUpload.id == MaterialVersion.upload_id)
    if q:
        query = query.where(or_(Material.title.ilike(keyword(q), escape="\\"),
                               ContentUpload.original_name.ilike(keyword(q), escape="\\")))
    if material_id is not None:
        query = query.where(Material.id == material_id)
    if newest_only:
        # Rank after authorization, so an unreadable v2 cannot hide the student's published v1.
        ranked = query.with_only_columns(MaterialVersion.id, func.row_number().over(
            partition_by=MaterialVersion.material_id,
            order_by=(MaterialVersion.version_no.desc(), MaterialVersion.id)).label("rn")).subquery()
        query = select(MaterialVersion).where(MaterialVersion.id.in_(select(ranked.c.id).where(ranked.c.rn == 1)))
    count = db.exec(select(func.count()).select_from(query.subquery())).one()
    rows = db.exec(query.order_by(MaterialVersion.created_at.desc(), MaterialVersion.id).offset(offset).limit(limit)).all()
    return Page[VersionView](items=[version_view(db, identity, row.id, library_id) for row in rows],
                             total=count, offset=offset, limit=limit)


def chunks(db, identity, version_id, after, limit, library_id=None):
    version, _material, _projection = require_version(db, identity, version_id, library_id)
    if version.extraction_state != "succeeded":
        raise HTTPException(409, "资料尚未成功解析，无可用页段")
    query = select(SourceChunk).where(SourceChunk.material_version_id == version_id)
    total = db.exec(select(func.count()).select_from(query.subquery())).one()
    rows = db.exec(query.where(SourceChunk.ordinal > after).order_by(SourceChunk.ordinal).limit(limit + 1)).all()
    items, used = [], 256
    for row in rows[:limit]:
        item = ChunkView(id=row.id, ordinal=row.ordinal, locator=row.locator, text=row.text, text_hash=row.text_hash)
        needed = len(item.model_dump_json().encode("utf-8")) + 1
        if used + needed > 1024 * 1024:
            if not items:
                raise HTTPException(413, "单页段超出响应预算")
            break
        used += needed
        items.append(item)
    last = items[-1].ordinal if items else after
    page = ChunkPage(version_id=version_id, items=items, total=total, next_ordinal=last if last < total else None)
    if len(json.dumps(page.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":")).encode()) > 1024 * 1024:
        raise HTTPException(413, "页段响应超出预算")
    return page
