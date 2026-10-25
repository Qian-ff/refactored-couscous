"""Authorization precedes counts, newest-version selection, and all public projections."""
import json

from fastapi import HTTPException
from sqlalchemy import and_, false, func, literal, or_, true, tuple_
from sqlalchemy.orm import aliased
from sqlmodel import select

from app.domains.core.policy import resource_access
from app.domains.core.models import Course
from app.domains.core.resource_query import read_resource_predicate
from app.domains.content.access import columns, descriptor, readable_versions, require_library, require_version, submit_libraries
from app.domains.content.models import ContentUpload, Library, Material, MaterialPublication, MaterialReview, MaterialVersion, SourceChunk
from app.domains.content.services import validate_publication_source, warnings_hash
from app.domains.content.views import (ChunkPage, ChunkView, LibraryView, Page, PublicationView,
    ReviewView, SearchMatch, SubmitTarget, TargetBinding, VersionActions, VersionView)


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
                                 active=row.active, revision=row.revision, can_submit=row.active and access.submit,
                                 can_review=row.active and access.review, can_manage=access.review))
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


def review_projection(db, identity, row, published=None):
    target = db.get(Library, row.target_library_id)
    manager = bool(target and target.active and resource_access(db, identity, descriptor(target)).review)
    version = db.get(MaterialVersion, row.version_id)
    material = db.get(Material, version.material_id)
    if published is None:
        published = db.exec(select(MaterialPublication.id).where(MaterialPublication.review_id == row.id)).first() is not None
    publishable = manager and row.state == "approved" and row.original_authorized and not published and not material.retired
    if publishable:
        try:
            validate_publication_source(version, db.get(Library, material.library_id), target, row.authorization_statement)
            publishable = row.warning_hash == warnings_hash(version)
        except HTTPException:
            publishable = False
    values = {name: getattr(row, name) for name in ReviewView.model_fields if name in MaterialReview.model_fields}
    return ReviewView(**values, can_decide=manager and row.state == "submitted", can_publish=publishable)


def publication_projection(db, identity, row):
    target = db.get(Library, row.target_library_id)
    values = {name: getattr(row, name) for name in PublicationView.model_fields if name in MaterialPublication.model_fields}
    return PublicationView(**values, can_retire=bool(row.active and target and target.active
        and resource_access(db, identity, descriptor(target)).review))


def binding_batch(db, identity, contexts):
    pairs = {(version.id, projection.id) for version, _material, projection in contexts}
    if not pairs:
        return {}
    manager = read_resource_predicate(identity, columns(Library, creator_id=literal(None), published=false()))
    ranked = select(MaterialReview.id.label("id"), func.row_number().over(
        partition_by=(MaterialReview.version_id, MaterialReview.target_library_id),
        order_by=(MaterialReview.submitted_at.desc(), MaterialReview.id)).label("rn")).join(
            Library, Library.id == MaterialReview.target_library_id).where(
                tuple_(MaterialReview.version_id, MaterialReview.target_library_id).in_(pairs),
                or_(manager, MaterialReview.submitter_id == identity.user.id)).subquery()
    reviews = db.exec(select(MaterialReview).where(MaterialReview.id.in_(select(ranked.c.id).where(ranked.c.rn == 1)))).all()
    linked = set(db.exec(select(MaterialPublication.review_id).where(
        MaterialPublication.review_id.in_([review.id for review in reviews]))).all()) if reviews else set()
    ranked_publications = select(MaterialPublication.id.label("id"), func.row_number().over(
        partition_by=(MaterialPublication.version_id, MaterialPublication.target_library_id),
        order_by=(MaterialPublication.published_at.desc(), MaterialPublication.id)).label("rn")).join(
            Library, Library.id == MaterialPublication.target_library_id).where(
                tuple_(MaterialPublication.version_id, MaterialPublication.target_library_id).in_(pairs),
                MaterialPublication.active.is_(True), Library.active.is_(True),
                read_resource_predicate(identity, columns(Library, creator_id=literal(None), published=true()))).subquery()
    publications = db.exec(select(MaterialPublication).where(MaterialPublication.id.in_(
        select(ranked_publications.c.id).where(ranked_publications.c.rn == 1)))).all()
    result = {pair: TargetBinding(target_library_id=pair[1]) for pair in pairs}
    for review in reviews:
        result[(review.version_id, review.target_library_id)].review = review_projection(db, identity, review, review.id in linked)
    for publication in publications:
        result[(publication.version_id, publication.target_library_id)].active_publication = publication_projection(db, identity, publication)
    return result


def project_version(db, identity, context, binding):
    version, material, projection = context
    source = db.get(Library, material.library_id)
    source_access = resource_access(db, identity, descriptor(source, creator_id=material.creator_id))
    target_access = resource_access(db, identity, descriptor(projection))
    review_access = target_access.review
    can_see_metadata = review_access or (source_access.read and source_access.submit and material.creator_id == identity.user.id)
    editable = source.active and source_access.read and (source_access.review or
        (source_access.submit and material.creator_id == identity.user.id))
    submittable = bool(editable and not material.retired and projection.active and target_access.submit)
    if submittable:
        try:
            validate_publication_source(version, source, projection, "Capability precondition only; submission still requires a statement")
        except HTTPException:
            submittable = False
    upload = db.get(ContentUpload, version.upload_id) if version.upload_id else None
    course = db.get(Course, projection.course_id) if projection.course_id else None
    return VersionView(material_id=material.id, version_id=version.id, library_id=projection.id,
                       title=material.title, version_no=version.version_no, input_kind=version.input_kind,
                       extraction_state=version.extraction_state, original_name=upload.original_name if upload else None,
                       file_bytes=upload.expected_bytes if upload else None, content_hash=version.content_hash,
                       parser_version=version.parser_version, created_at=version.created_at,
                       warnings=version.warnings, warning_hash=warnings_hash(version),
                       source_metadata=version.source_metadata if can_see_metadata else None,
                       material_revision=material.revision if editable else None,
                       actions=VersionActions(edit_material=editable, retire_material=bool(source.active and source_access.review),
                           create_version=editable and not material.retired, submit_review=submittable,
                           preview=version.extraction_state == "succeeded", download=True), binding=binding,
                       file_type=upload.format if upload else "text", course_id=course.id if course else None,
                       course_code=course.code if course else None, course_title=course.title if course else None)


def version_view(db, identity, version_id, library_id=None):
    context = require_version(db, identity, version_id, library_id)
    bindings = binding_batch(db, identity, [context])
    return project_version(db, identity, context, bindings[(context[0].id, context[2].id)])


def search_matches(db, contexts, q):
    """One bounded matching chunk per already authorized page version, never a full-library fetch."""
    ids = [version.id for version, _material, _projection in contexts if version.extraction_state == "succeeded"]
    start = func.greatest(1, func.strpos(func.lower(SourceChunk.text), func.lower(q)) - 60)
    ranked = select(SourceChunk.id.label("id"), SourceChunk.material_version_id.label("version_id"),
        SourceChunk.ordinal, SourceChunk.locator, func.substr(SourceChunk.text, start, 240).label("snippet"),
        func.row_number().over(partition_by=SourceChunk.material_version_id, order_by=SourceChunk.ordinal).label("rn"),
    ).where(SourceChunk.material_version_id.in_(ids), SourceChunk.text.ilike(keyword(q), escape="\\")).subquery()
    matches = {row.version_id: SearchMatch(kind="chunk", snippet=row.snippet, chunk_id=row.id,
        ordinal=row.ordinal, locator=row.locator) for row in db.exec(select(ranked).where(ranked.c.rn == 1))} if ids else {}
    for version, material, _projection in contexts:
        if version.id in matches:
            continue
        upload = db.get(ContentUpload, version.upload_id) if version.upload_id else None
        for kind, value in (("input_text", version.input_text), ("title", material.title),
                            ("filename", upload.original_name if upload else None)):
            if value and q.lower() in value.lower():
                start = max(0, value.lower().find(q.lower()) - 60)
                matches[version.id] = SearchMatch(kind=kind, snippet=value[start:start + 240])
                break
    return matches


def versions(db, identity, q, offset, limit, library_id=None, material_id=None, newest_only=False,
             course_id=None, file_type=None, created_after=None, created_before=None):
    if any(value is not None and value.tzinfo is None for value in (created_after, created_before)):
        raise HTTPException(422, "时间筛选须包含时区")
    if created_after and created_before and created_after > created_before:
        raise HTTPException(422, "开始时间不能晚于结束时间")
    query = readable_versions(identity, library_id, course_id).outerjoin(ContentUpload, ContentUpload.id == MaterialVersion.upload_id)
    if q:
        body = select(SourceChunk.id).where(SourceChunk.material_version_id == MaterialVersion.id,
            SourceChunk.text.ilike(keyword(q), escape="\\")).correlate(MaterialVersion).exists()
        query = query.where(or_(Material.title.ilike(keyword(q), escape="\\"),
                               ContentUpload.original_name.ilike(keyword(q), escape="\\"),
                               MaterialVersion.input_text.ilike(keyword(q), escape="\\"),
                               and_(MaterialVersion.extraction_state == "succeeded", body)))
    if file_type:
        query = query.where(MaterialVersion.input_kind == "text" if file_type == "text" else ContentUpload.format == file_type)
    if created_after:
        query = query.where(MaterialVersion.created_at >= created_after)
    if created_before:
        query = query.where(MaterialVersion.created_at <= created_before)
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
    contexts = [require_version(db, identity, row.id, library_id, course_id) for row in rows]
    bindings = binding_batch(db, identity, contexts)
    matches = search_matches(db, contexts, q) if q else {}
    items = [project_version(db, identity, context, bindings[(context[0].id, context[2].id)]) for context in contexts]
    for item in items:
        item.search_match = matches.get(item.version_id)
    return Page[VersionView](items=items, total=count, offset=offset, limit=limit)


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
