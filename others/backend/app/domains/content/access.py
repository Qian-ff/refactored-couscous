"""B's resource policy applied to real source or approved target bindings."""
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import and_, false, literal, or_, true
from sqlalchemy.orm import aliased
from sqlmodel import Session, select

from app.domains.core.auth import Identity
from app.domains.core.models import College, Course, CourseCatalog, School
from app.domains.core.policy import ResourceDescriptor, resource_access
from app.domains.core.resource_query import ResourceColumns, read_resource_predicate
from app.domains.content.models import Library, Material, MaterialPublication, MaterialReview, MaterialVersion


def descriptor(library: Library, *, creator_id=None, published=False):
    return ResourceDescriptor(scope=library.scope, school_id=library.school_id, college_id=library.college_id,
                              catalog_id=library.catalog_id, course_id=library.course_id,
                              audience=library.audience, creator_id=creator_id, published=published)


def columns(library, *, creator_id, published):
    return ResourceColumns(scope=library.scope, school_id=library.school_id, college_id=library.college_id,
                           catalog_id=library.catalog_id, course_id=library.course_id,
                           audience=library.audience, creator_id=creator_id, published=published)


def readable_versions(identity: Identity):
    """EXISTS prevents duplicate versions before count/pagination with multiple publications."""
    target = aliased(Library)
    published = select(MaterialPublication.id).join(
        MaterialReview, MaterialReview.id == MaterialPublication.review_id,
    ).join(target, target.id == MaterialPublication.target_library_id).where(
        MaterialPublication.version_id == MaterialVersion.id,
        MaterialPublication.active.is_(True), target.active.is_(True),
        MaterialReview.state == "approved",
        MaterialReview.version_id == MaterialPublication.version_id,
        MaterialReview.target_library_id == MaterialPublication.target_library_id,
        read_resource_predicate(identity, columns(target, creator_id=Material.creator_id, published=true())),
    ).correlate(MaterialVersion, Material).exists()
    source = and_(Library.active.is_(True), read_resource_predicate(
        identity, columns(Library, creator_id=Material.creator_id, published=false())))
    review_target = aliased(Library)
    reviewable = select(MaterialReview.id).join(
        review_target, review_target.id == MaterialReview.target_library_id,
    ).where(
        MaterialReview.version_id == MaterialVersion.id,
        MaterialReview.state.in_(["submitted", "approved"]), review_target.active.is_(True),
        read_resource_predicate(identity, columns(review_target, creator_id=literal(None), published=false())),
    ).correlate(MaterialVersion).exists()
    return select(MaterialVersion).join(Material, Material.id == MaterialVersion.material_id).join(
        Library, Library.id == Material.library_id).where(or_(source, published, reviewable))


def require_version(db: Session, identity: Identity, version_id: UUID):
    version = db.exec(readable_versions(identity).where(MaterialVersion.id == version_id)).first()
    if version is None:
        raise HTTPException(403, "无权读取该资料版本")
    material = db.get(Material, version.material_id)
    source = db.get(Library, material.library_id)
    if source.active and resource_access(db, identity, descriptor(source, creator_id=material.creator_id)).read:
        return version, material, source
    bindings = db.exec(select(MaterialPublication, MaterialReview, Library).join(
        MaterialReview, MaterialReview.id == MaterialPublication.review_id,
    ).join(Library, Library.id == MaterialPublication.target_library_id).where(
        MaterialPublication.version_id == version_id, MaterialPublication.active.is_(True),
        MaterialReview.state == "approved", MaterialReview.version_id == version_id,
        MaterialReview.target_library_id == MaterialPublication.target_library_id,
        Library.active.is_(True),
    ).order_by(MaterialPublication.id)).all()
    for _publication, _review, target in bindings:
        if resource_access(db, identity, descriptor(target, creator_id=material.creator_id, published=True)).read:
            return version, material, target
    reviews = db.exec(select(MaterialReview, Library).join(
        Library, Library.id == MaterialReview.target_library_id,
    ).where(MaterialReview.version_id == version_id, MaterialReview.state.in_(["submitted", "approved"]),
            Library.active.is_(True)).order_by(MaterialReview.id)).all()
    for _review, target in reviews:
        if resource_access(db, identity, descriptor(target)).review:
            return version, material, target
    raise HTTPException(403, "资料授权已改变，请刷新")


def require_library(db: Session, identity: Identity, library_id: UUID, capability: str):
    library = db.get(Library, library_id)
    if library is None or not library.active:
        raise HTTPException(403, "资料库不存在、已停用或无权访问")
    access = resource_access(db, identity, descriptor(library))
    if capability not in {"submit", "review"} or not getattr(access, capability):
        raise HTTPException(403, "无权执行此资料库操作")
    return library


def resolve_scope(db: Session, scope: str, parent_id: UUID | None):
    """Derive organization fields from B's actual parents, preserving cross-college courses."""
    if scope == "platform_public":
        if parent_id is not None:
            raise HTTPException(422, "平台公共库不接受组织父级")
        return dict(school_id=None, college_id=None, catalog_id=None, course_id=None)
    model = {"school": School, "college": College, "catalog": CourseCatalog, "course": Course}.get(scope)
    parent = db.get(model, parent_id) if model and parent_id else None
    if parent is None or getattr(parent, "archived", False) or not getattr(parent, "is_active", True):
        raise HTTPException(422, "资料库父级无效")
    return dict(school_id=parent.id if scope == "school" else parent.school_id,
                college_id=parent.id if scope == "college" else getattr(parent, "college_id", None),
                catalog_id=parent.id if scope == "catalog" else getattr(parent, "catalog_id", None),
                course_id=parent.id if scope == "course" else None)
