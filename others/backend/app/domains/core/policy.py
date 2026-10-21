"""Shared SQL scope and operation permissions consumed by B1 and the content domain."""
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import false, or_
from sqlmodel import Session, select

from app.core.grants import validate_role_family
from app.domains.core.auth import Identity
from app.domains.core.models import College, Course, CourseCatalog, CourseStaff, Enrollment, Major, Role, RoleGrant, School, User


def require(condition: bool, message="无权执行此操作", status=403):
    if not condition:
        raise HTTPException(status, message)


def admin_colleges(identity: Identity):
    return [g.college_id for g in identity.grants if g.role == Role.COLLEGE_ADMIN
            and g.school_id == identity.user.school_id]


def school_manager(identity: Identity, school_id: UUID | None):
    return identity.has(Role.PLATFORM_ADMIN) or (
        school_id is not None and identity.user.school_id == school_id and identity.has(Role.SCHOOL_ADMIN))


def require_school_manager(identity: Identity, school_id: UUID | None):
    require(school_manager(identity, school_id))


def require_active_organization(db: Session, school_id: UUID, college_id: UUID,
                                major_id: UUID | None = None):
    school, college = db.get(School, school_id), db.get(College, college_id)
    require(school is not None and school.is_active and college is not None
            and college.is_active and college.school_id == school_id, "学校或学院无效/已停用", 422)
    if major_id:
        major = db.get(Major, major_id)
        require(major is not None and major.is_active and major.school_id == school_id
                and major.college_id == college_id, "专业不属于所选学院或已停用", 422)


def require_teacher(db: Session, user_id: UUID, school_id: UUID):
    user = db.get(User, user_id)
    grant = db.exec(select(RoleGrant).where(RoleGrant.user_id == user_id, RoleGrant.role == Role.TEACHER)).first()
    require(user is not None and user.is_active and user.school_id == school_id and grant is not None,
            "必须选择本校有效教师", 422)
    return user


def require_student(db: Session, user: User | None, school_id: UUID):
    require(user is not None and user.is_active and user.school_id == school_id, "学生账号不存在或无效", 422)
    roles = list(db.exec(select(RoleGrant).where(RoleGrant.user_id == user.id)).all())
    require(bool(roles) and {grant.role for grant in roles} == {Role.STUDENT}, "必须选择独立学生账号", 422)


def staff_query(user_id: UUID, *, primary=False):
    query = select(CourseStaff.course_id).where(CourseStaff.user_id == user_id, CourseStaff.is_active.is_(True))
    return query.where(CourseStaff.is_primary.is_(True)) if primary else query


def visible_course_query(identity: Identity, *, include_archived=False):
    query = select(Course)
    if identity.has(Role.PLATFORM_ADMIN):
        return query if include_archived else query.where(Course.archived.is_(False))
    terms = []
    if identity.has(Role.SCHOOL_ADMIN):
        terms.append(Course.school_id == identity.user.school_id)
    if admin_colleges(identity):
        terms.append(Course.college_id.in_(admin_colleges(identity)))
    if identity.has(Role.TEACHER):
        terms.append(Course.id.in_(staff_query(identity.user.id)))
    if identity.has(Role.STUDENT):
        terms.append(Course.id.in_(select(Enrollment.course_id).where(
            Enrollment.user_id == identity.user.id, Enrollment.status == "active")))
        include_archived = False
    query = query.where(Course.school_id == identity.user.school_id, or_(*terms) if terms else false())
    return query if include_archived else query.where(Course.archived.is_(False))


def catalog_manage(identity: Identity, catalog: CourseCatalog):
    return identity.manages(catalog.college_id, catalog.school_id) or (
        identity.has(Role.TEACHER) and identity.user.school_id == catalog.school_id
        and catalog.owner_id == identity.user.id)


def visible_catalog_query(identity: Identity):
    if identity.has(Role.PLATFORM_ADMIN):
        return select(CourseCatalog)
    terms = [CourseCatalog.id.in_(visible_course_query(identity).with_only_columns(Course.catalog_id))]
    if identity.has(Role.SCHOOL_ADMIN):
        terms.append(CourseCatalog.school_id == identity.user.school_id)
    if admin_colleges(identity):
        terms.append(CourseCatalog.college_id.in_(admin_colleges(identity)))
    if identity.has(Role.TEACHER):
        terms.append(CourseCatalog.owner_id == identity.user.id)
    return select(CourseCatalog).where(CourseCatalog.school_id == identity.user.school_id, or_(*terms))


def require_catalog(db: Session, identity: Identity, catalog_id: UUID, *, manage=False):
    catalog = db.exec(visible_catalog_query(identity).where(CourseCatalog.id == catalog_id)).first()
    require(catalog is not None, "课程目录不存在或不在授权范围", 404)
    if manage:
        require(catalog_manage(identity, catalog))
    return catalog


def can_manage_class(identity: Identity, db: Session, course: Course, *, primary=False):
    if identity.manages(course.college_id, course.school_id):
        return True
    if not identity.has(Role.TEACHER) or identity.user.school_id != course.school_id:
        return False
    return db.exec(staff_query(identity.user.id, primary=primary).where(CourseStaff.course_id == course.id)).first() is not None


def require_class(db: Session, identity: Identity, course_id: UUID, *, manage=False, primary=False,
                  history=False, write=False):
    course = db.exec(visible_course_query(identity, include_archived=history).where(Course.id == course_id)).first()
    require(course is not None, "教学班不存在或不在授权范围", 404)
    if manage or primary:
        require(can_manage_class(identity, db, course, primary=primary))
    if write:
        require(not course.archived, "教学班已归档，不可修改", 409)
    return course


def visible_account_query(identity: Identity):
    require(identity.work_role == "administrator")
    if identity.has(Role.PLATFORM_ADMIN):
        return select(User)
    query = select(User).where(User.school_id == identity.user.school_id)
    if identity.has(Role.SCHOOL_ADMIN):
        return query
    return query.where(User.college_id.in_(admin_colleges(identity)), ~User.id.in_(select(RoleGrant.user_id).where(
        RoleGrant.role.in_([Role.PLATFORM_ADMIN, Role.SCHOOL_ADMIN, Role.COLLEGE_ADMIN]))))


def require_account(db: Session, identity: Identity, user_id: UUID, *, write=False):
    user = db.exec(visible_account_query(identity).where(User.id == user_id)).first()
    require(user is not None, "账号不存在或不在授权范围", 404)
    if write:
        require(user.id != identity.user.id, "请使用个人资料和本人改密，不可管理自己的授权")
        roles = {g.role for g in db.exec(select(RoleGrant).where(RoleGrant.user_id == user.id)).all()}
        try:
            validate_role_family(roles)
        except ValueError as error:
            raise HTTPException(409, f"账号 {user.id} 存在历史角色冲突，请保留数据并交总控核查") from error
        if not identity.has(Role.PLATFORM_ADMIN):
            require(not roles.intersection({Role.PLATFORM_ADMIN, Role.SCHOOL_ADMIN}), "不能管理同级或更高权限账号")
            require(identity.manages(user.college_id, user.school_id))
    return user


def require_grant_authority(identity: Identity, school_id: UUID, college_id: UUID, role: Role,
                            grant_college_id: UUID | None):
    require(role != Role.PLATFORM_ADMIN, "平台运维账号不通过学校账号入口创建")
    if role == Role.SCHOOL_ADMIN:
        require(identity.has(Role.PLATFORM_ADMIN), "校管理员由平台运维授权")
        require(grant_college_id is None, "校管理员授权不绑定学院", 422)
    elif role == Role.COLLEGE_ADMIN:
        require_school_manager(identity, school_id)
        require(grant_college_id is not None, "学院管理员须指定授权学院", 422)
    else:
        require(identity.manages(college_id, school_id))
        require(grant_college_id is None, "学生和教师使用账号组织范围，不接受管理员学院字段", 422)


@dataclass(frozen=True)
class ResourceDescriptor:
    scope: Literal["platform_public", "school", "college", "catalog", "course"]
    school_id: UUID | None = None
    college_id: UUID | None = None
    catalog_id: UUID | None = None
    course_id: UUID | None = None
    published: bool = False
    creator_id: UUID | None = None
    audience: Literal["all", "staff"] = "all"


@dataclass(frozen=True)
class ResourceAccess:
    read: bool = False
    submit: bool = False
    review: bool = False


def resource_access(db: Session, identity: Identity, resource: ResourceDescriptor) -> ResourceAccess:
    """ResourceDescriptor must be loaded by C from server-owned metadata, never from client claims."""
    student = identity.has(Role.STUDENT)
    if resource.scope == "platform_public":
        # An allegedly public item carrying a private school/parent is invalid, rather than a bypass.
        if any((resource.school_id, resource.college_id, resource.catalog_id, resource.course_id)):
            return ResourceAccess()
        operator = identity.has(Role.PLATFORM_ADMIN)
        return ResourceAccess(operator or (resource.published and (not student or resource.audience == "all")), operator, operator)
    school = db.get(School, resource.school_id) if resource.school_id else None
    if school is None or not school.is_active:
        return ResourceAccess()
    if not identity.has(Role.PLATFORM_ADMIN) and identity.user.school_id != school.id:
        return ResourceAccess()
    read, submit, review = False, False, False
    if resource.scope == "school":
        if resource.college_id or resource.catalog_id or resource.course_id:
            return ResourceAccess()
        review = school_manager(identity, school.id)
        submit = review or identity.has(Role.TEACHER)
        read = resource.published or review or (submit and resource.creator_id == identity.user.id)
    elif resource.scope == "college":
        college = db.get(College, resource.college_id) if resource.college_id else None
        if college is None or college.school_id != school.id or resource.catalog_id or resource.course_id:
            return ResourceAccess()
        review = identity.manages(college.id, school.id)
        submit = review or (identity.has(Role.TEACHER) and identity.user.college_id == college.id)
        member = identity.user.college_id == college.id
        read = review or (resource.published and member) or (submit and resource.creator_id == identity.user.id)
    elif resource.scope == "catalog":
        catalog = db.get(CourseCatalog, resource.catalog_id) if resource.catalog_id else None
        if (catalog is None or catalog.school_id != school.id or catalog.archived or resource.course_id
                or (resource.college_id and resource.college_id != catalog.college_id)):
            return ResourceAccess()
        review = catalog_manage(identity, catalog)
        permitted = db.exec(visible_course_query(identity).where(Course.catalog_id == catalog.id)).first() is not None
        submit = review or (identity.has(Role.TEACHER) and permitted)
        read = review or (resource.published and permitted) or (submit and resource.creator_id == identity.user.id)
    elif resource.scope == "course":
        course = db.get(Course, resource.course_id) if resource.course_id else None
        if (course is None or course.school_id != school.id or course.archived
                or (resource.catalog_id and resource.catalog_id != course.catalog_id)
                or (resource.college_id and resource.college_id != course.college_id)):
            return ResourceAccess()
        submit = can_manage_class(identity, db, course)
        review = submit
        permitted = db.exec(visible_course_query(identity).where(Course.id == course.id)).first() is not None
        read = review or (resource.published and permitted) or (submit and resource.creator_id == identity.user.id)
    if student and resource.audience == "staff":
        read = False
    return ResourceAccess(bool(read), bool(submit), bool(review))


def may_read_own_training_history(identity: Identity, student_id: UUID) -> bool:
    """Historical self access is separate from live Enrollment. B2 attaches the real records."""
    return identity.has(Role.STUDENT) and identity.user.id == student_id
