from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query
from sqlalchemy import or_
from sqlmodel import select

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.domains.core.auth import AccountIdentity, CurrentAccount, CurrentIdentity, Db, available_work_roles, default_work_role
from app.domains.core.class_routes import create_class
from app.domains.core.management_routes import keyword, page
from app.domains.core.models import College, Course, CourseStaff, LoginSession, Role, RoleGrant, School, User
from app.domains.core.policy import visible_course_query
from app.domains.core.schemas import (CourseContext, CourseCreate, CoursePublic, CoursesPublic,
                                      GrantPublic, LoginInput, Message, OrganizationPublic, Token, UserPublic)

router = APIRouter()
DUMMY_HASH = get_password_hash("safelab-dummy-password-never-used-for-login")


@router.post("/auth/login", tags=["auth"], response_model=Token)
def login(body: LoginInput, db: Db):
    school = db.exec(select(School).where(School.code == body.school_code)).first()
    school_filter = User.school_id == school.id if school else User.school_id.is_(None)
    user = db.exec(select(User).where(school_filter, User.username == body.username)).first()
    valid_school = (school is not None and school.is_active) or body.school_code == "platform"
    valid, updated = verify_password(body.password, user.hashed_password if user else DUMMY_HASH)
    if not valid_school or not user or not user.is_active or not valid:
        raise HTTPException(status_code=401, detail="学校、账号或密码不正确")
    if updated:
        user.hashed_password = updated
        db.add(user)
    expires = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    grants = list(db.exec(select(RoleGrant).where(RoleGrant.user_id == user.id)).all())
    try:
        selected = default_work_role(grants)
    except ValueError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    session = LoginSession(user_id=user.id, expires_at=expires, default_work_role=selected)
    db.add(session)
    db.commit()
    encoded = create_access_token(user.id, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES), str(session.id))
    return Token(access_token=encoded, expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)


@router.post("/auth/logout", tags=["auth"], response_model=Message)
def logout(identity: CurrentAccount, db: Db):
    identity.login.revoked = True
    db.add(identity.login)
    db.commit()
    return Message(message="已安全退出")


@router.get("/auth/me", tags=["auth"], response_model=UserPublic)
def me(identity: AccountIdentity, db: Db):
    user = identity.user
    school = db.get(School, user.school_id) if user.school_id else None
    college = db.get(College, user.college_id) if user.college_id else None
    create = any(identity.has(role) for role in (Role.PLATFORM_ADMIN, Role.SCHOOL_ADMIN, Role.COLLEGE_ADMIN, Role.TEACHER))
    return UserPublic(id=user.id, username=user.username, display_name=user.display_name,
                      school=OrganizationPublic(id=school.id, name=school.name) if school else None,
                      college=OrganizationPublic(id=college.id, school_id=college.school_id, name=college.name) if college else None,
                      grants=[GrantPublic(role=g.role, college_id=g.college_id) for g in identity.all_grants],
                      effective_grants=[GrantPublic(role=g.role, college_id=g.college_id) for g in identity.grants],
                      available_work_roles=available_work_roles(identity.all_grants), active_work_role=identity.work_role,
                      student_no=user.student_no, major_id=user.major_id, gender=user.gender, contact=user.contact,
                      must_change_password=user.must_change_password, revision=user.revision,
                      permissions=(["profile:read", "password:change"] if user.must_change_password else
                                   ["courses:read"] + (["courses:create"] if create else [])))


def visible_courses(identity: CurrentIdentity):
    return visible_course_query(identity)


def public_course(course: Course, db: Db) -> CoursePublic:
    college = db.get(College, course.college_id)
    primary = db.exec(select(User).join(CourseStaff, CourseStaff.user_id == User.id).where(
        CourseStaff.course_id == course.id, CourseStaff.is_primary.is_(True), CourseStaff.is_active.is_(True))).first()
    return CoursePublic(id=course.id, school_id=course.school_id, college_id=course.college_id, catalog_id=course.catalog_id,
                        college_name=college.name, code=course.code, title=course.title,
                        teacher_name=primary.display_name if primary else "待分配")


@router.get("/courses/context", tags=["courses"], response_model=CourseContext)
def context(identity: CurrentIdentity, db: Db):
    query = select(College).where(College.is_active.is_(True))
    if not identity.has(Role.PLATFORM_ADMIN):
        query = query.where(College.school_id == identity.user.school_id)
    colleges = [college for college in db.exec(query).all()
                if identity.can_create(college.id, college.school_id)]
    school_ids = {college.school_id for college in colleges}
    teachers = []
    if school_ids:
        teachers = list(db.exec(select(User).where(User.school_id.in_(school_ids), User.is_active.is_(True),
            User.id.in_(select(RoleGrant.user_id).where(RoleGrant.role == Role.TEACHER)))).all())  # noqa: E712
        if not any(identity.has(role) for role in (Role.PLATFORM_ADMIN, Role.SCHOOL_ADMIN)):
            permitted_colleges = {college.id for college in colleges}
            teachers = [teacher for teacher in teachers if teacher.college_id in permitted_colleges]
        if not any(identity.has(role) for role in (Role.PLATFORM_ADMIN, Role.SCHOOL_ADMIN, Role.COLLEGE_ADMIN)):
            teachers = [teacher for teacher in teachers if teacher.id == identity.user.id]
    return CourseContext(can_create=bool(colleges),
                         colleges=[OrganizationPublic(id=c.id, name=c.name, school_id=c.school_id) for c in colleges],
                         teachers=[OrganizationPublic(id=t.id, name=t.display_name, school_id=t.school_id) for t in teachers])


@router.get("/courses", tags=["courses"], response_model=CoursesPublic)
def courses(identity: CurrentIdentity, db: Db, offset: int = Query(default=0, ge=0),
            limit: int = Query(default=100, ge=1, le=100), q: str = Query(default="", max_length=100),
            catalog_id: UUID | None = None, college_id: UUID | None = None, archived: bool = False):
    query = visible_course_query(identity, include_archived=archived).where(Course.archived == archived,
        or_(Course.code.ilike(keyword(q)), Course.title.ilike(keyword(q))))
    if catalog_id:
        query = query.where(Course.catalog_id == catalog_id)
    if college_id:
        query = query.where(Course.college_id == college_id)
    result = page(db, query.order_by(Course.created_at.desc(), Course.id), offset, limit)
    return CoursesPublic(data=[public_course(c, db) for c in result["data"]], count=result["count"])


@router.get("/courses/{course_id}", tags=["courses"], response_model=CoursePublic)
def course(course_id: UUID, identity: CurrentIdentity, db: Db):
    record = db.exec(visible_courses(identity).where(Course.id == course_id)).first()
    if record is None:
        raise HTTPException(status_code=404, detail="课程不存在或不在你的授权范围内")
    return public_course(record, db)


@router.post("/courses", tags=["courses"], response_model=CoursePublic, status_code=201)
def create_course(body: CourseCreate, identity: CurrentIdentity, db: Db,
                  key: Annotated[str | None, Header(alias="Idempotency-Key", min_length=8, max_length=128)] = None):
    return create_class(body, identity, db, key, public_course)
