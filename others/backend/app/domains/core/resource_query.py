"""SQL content read scope, so C can authorize before count/pagination/snippets.

Build ResourceColumns with the real resource table's server-owned columns (literal(None)
for an inapplicable parent). Apply read_resource_predicate to both count and page queries.
Use policy.resource_access again for details, downloads, submit/review and fixed versions.
"""
from dataclasses import dataclass
from typing import Any

from sqlalchemy import and_, false, or_, true
from sqlmodel import select

from app.domains.core.auth import Identity
from app.domains.core.models import College, Course, CourseCatalog, Role, School
from app.domains.core.policy import admin_colleges, staff_query, visible_course_query


@dataclass(frozen=True)
class ResourceColumns:
    scope: Any
    school_id: Any
    college_id: Any
    catalog_id: Any
    course_id: Any
    published: Any
    creator_id: Any
    audience: Any


def read_resource_predicate(identity: Identity, c: ResourceColumns):
    platform = identity.has(Role.PLATFORM_ADMIN)
    school_admin = identity.has(Role.SCHOOL_ADMIN)
    teacher = identity.has(Role.TEACHER)
    student = identity.has(Role.STUDENT)
    own_school = c.school_id == identity.user.school_id
    tenant = true() if platform else own_school
    school_review = true() if platform else and_(own_school, true() if school_admin else false())
    college_review = true() if platform else or_(school_review, and_(own_school, c.college_id.in_(admin_colleges(identity))))
    no_parents = and_(c.college_id.is_(None), c.catalog_id.is_(None), c.course_id.is_(None))
    published = c.published.is_(True)
    own_draft = and_(c.creator_id == identity.user.id, true() if teacher else false())
    active_school = select(School.id).where(School.id == c.school_id, School.is_active.is_(True)).exists()

    public = and_(c.scope == "platform_public", c.school_id.is_(None), no_parents,
                  true() if platform else published)
    school = and_(c.scope == "school", no_parents, or_(published, school_review, own_draft))
    college_exists = select(College.id).where(College.id == c.college_id, College.school_id == c.school_id).exists()
    college = and_(c.scope == "college", c.catalog_id.is_(None), c.course_id.is_(None), college_exists,
        or_(college_review, and_(c.college_id == identity.user.college_id, or_(published, own_draft))))

    readable_catalogs = visible_course_query(identity).with_only_columns(Course.catalog_id)
    catalog_review = true() if platform else or_(
        CourseCatalog.school_id == identity.user.school_id if school_admin else false(),
        CourseCatalog.college_id.in_(admin_colleges(identity)),
        and_(CourseCatalog.owner_id == identity.user.id, true() if teacher else false()),
    )
    catalog_exists = select(CourseCatalog.id).where(
        CourseCatalog.id == c.catalog_id, CourseCatalog.school_id == c.school_id,
        CourseCatalog.archived.is_(False), or_(c.college_id.is_(None), c.college_id == CourseCatalog.college_id),
        or_(catalog_review, and_(CourseCatalog.id.in_(readable_catalogs), or_(published, own_draft))),
    ).exists()
    catalog = and_(c.scope == "catalog", c.course_id.is_(None), catalog_exists)

    readable_courses = visible_course_query(identity).with_only_columns(Course.id)
    course_manager = true() if platform else or_(
        Course.school_id == identity.user.school_id if school_admin else false(),
        Course.college_id.in_(admin_colleges(identity)),
        Course.id.in_(staff_query(identity.user.id)) if teacher else false(),
    )
    course_exists = select(Course.id).where(
        Course.id == c.course_id, Course.school_id == c.school_id, Course.archived.is_(False),
        or_(c.catalog_id.is_(None), c.catalog_id == Course.catalog_id),
        or_(c.college_id.is_(None), c.college_id == Course.college_id),
        or_(course_manager, and_(Course.id.in_(readable_courses), published)),
    ).exists()
    course = and_(c.scope == "course", course_exists)
    return and_(or_(public, and_(tenant, active_school, or_(school, college, catalog, course))),
                c.audience == "all" if student else true())
