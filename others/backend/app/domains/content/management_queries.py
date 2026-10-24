from fastapi import HTTPException
from sqlalchemy import false, literal, or_
from sqlmodel import select

from app.domains.core.policy import resource_access
from app.domains.core.resource_query import read_resource_predicate
from app.domains.content.access import columns, descriptor, readable_versions, require_library, require_version
from app.domains.content.jobs import job_view
from app.domains.content.models import ContentJob, Library, MaterialPublication, MaterialReview, MaterialVersion
from app.domains.content.views import JobView, Page, PublicationView, ReviewView


def page(db, query, model, view, offset, limit, projection):
    from sqlalchemy import func
    total = db.exec(select(func.count()).select_from(query.subquery())).one()
    rows = db.exec(query.order_by(model.id).offset(offset).limit(limit)).all()
    return Page[view](items=[projection(row) for row in rows], total=total, offset=offset, limit=limit)


def own_jobs(db, identity, offset, limit, version_id=None):
    visible = readable_versions(identity).with_only_columns(MaterialVersion.id)
    query = select(ContentJob).where(ContentJob.owner_id == identity.user.id, ContentJob.work_role == identity.work_role,
                                     ContentJob.version_id.in_(visible))
    if version_id:
        query = query.where(ContentJob.version_id == version_id)
    return page(db, query, ContentJob, JobView, offset, limit, lambda row: job_view(db, identity, row.id))


def reviews(db, identity, offset, limit, library_id=None, state=None):
    manager = read_resource_predicate(identity, columns(Library, creator_id=literal(None), published=false()))
    own_version = readable_versions(identity).with_only_columns(MaterialVersion.id)
    query = select(MaterialReview).join(Library, Library.id == MaterialReview.target_library_id).where(
        Library.active.is_(True), or_(manager, (MaterialReview.submitter_id == identity.user.id)
                                      & MaterialReview.version_id.in_(own_version)))
    if library_id:
        query = query.where(Library.id == library_id)
    if state:
        query = query.where(MaterialReview.state == state)
    return page(db, query, MaterialReview, ReviewView, offset, limit,
                lambda row: review_view(db, identity, row.id))


def review_view(db, identity, review_id):
    row = db.get(MaterialReview, review_id)
    if row is None:
        raise HTTPException(403, "审核记录不存在或无权访问")
    library = db.get(Library, row.target_library_id)
    manager = library is not None and library.active and resource_access(db, identity, descriptor(library)).review
    if not manager:
        if row.submitter_id != identity.user.id:
            raise HTTPException(403, "无权读取审核记录")
        require_version(db, identity, row.version_id)
    return ReviewView(**{name: getattr(row, name) for name in ReviewView.model_fields})


def publications(db, identity, library_id, offset, limit):
    require_library(db, identity, library_id, "review")
    query = select(MaterialPublication).where(MaterialPublication.target_library_id == library_id)
    return page(db, query, MaterialPublication, PublicationView, offset, limit,
                lambda row: PublicationView(**{name: getattr(row, name) for name in PublicationView.model_fields}))
