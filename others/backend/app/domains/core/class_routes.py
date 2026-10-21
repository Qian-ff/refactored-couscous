from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import or_
from sqlmodel import select

from app.domains.core.auth import CurrentIdentity, Db
from app.domains.core.business_schemas import (
    CatalogInput, CatalogPatch, CatalogView, ClassManagementView, CommandKey, CourseSettings,
    EnrollmentResult, InviteInput, JoinCodeIssued, JoinInput, MemberInput, MemberView, Page,
    RequestDecision, RequestView, RevisionInput, StaffInput, StaffView, TeacherOption,
)
from app.domains.core.commands import check_revision, code_hash, execute_command, issued_code, touch
from app.domains.core.management_routes import keyword, page
from app.domains.core.models import College, Course, CourseCatalog, CourseStaff, Enrollment, EnrollmentRequest, Role, RoleGrant, User
from app.domains.core.policy import (
    can_manage_class, require, require_active_organization, require_catalog,
    require_class, require_student, require_teacher, school_manager, visible_catalog_query,
)
from app.domains.core.schemas import CourseCreate, Message

router = APIRouter(tags=["teaching"])


def catalog_view(record):
    return CatalogView.model_validate(record, from_attributes=True)


def management_view(db, identity, record):
    return ClassManagementView(**record.model_dump(), can_manage_staff=can_manage_class(identity, db, record, primary=True),
                               can_manage_members=can_manage_class(identity, db, record))


def request_view(db, record):
    user = db.get(User, record.user_id)
    return RequestView(**record.model_dump(), display_name=user.display_name)


def class_scope(db, course_id):
    record = db.get(Course, course_id)
    require(record is not None, "教学班不存在或不在授权范围", 404)
    return record.school_id


def locked_class(db, identity, course_id, *, primary=False, history=False):
    record = require_class(db, identity, course_id, manage=True, primary=primary, history=history, write=True)
    db.exec(select(Course).where(Course.id == course_id).with_for_update()).one()
    db.refresh(record)
    require(not record.archived, "教学班已归档，不可修改", 409)
    return record


@router.get("/catalogs", response_model=Page[CatalogView])
def catalogs(identity: CurrentIdentity, db: Db, q: str = Query(default="", max_length=100),
             college_id: UUID | None = None, archived: bool = False,
             offset: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=100)):
    query = visible_catalog_query(identity).where(CourseCatalog.archived == archived)
    if college_id:
        query = query.where(CourseCatalog.college_id == college_id)
    return page(db, query.where(or_(CourseCatalog.code.ilike(keyword(q)), CourseCatalog.title.ilike(keyword(q)))).order_by(
        CourseCatalog.code, CourseCatalog.id), offset, limit)


@router.get("/catalogs/{catalog_id}", response_model=CatalogView)
def catalog(catalog_id: UUID, identity: CurrentIdentity, db: Db):
    return require_catalog(db, identity, catalog_id)


@router.post("/catalogs", response_model=CatalogView, status_code=201)
def create_catalog(body: CatalogInput, identity: CurrentIdentity, db: Db, key: CommandKey):
    college = db.get(College, body.college_id)
    require(college is not None, "学院无效", 422)
    def authorize():
        require(identity.can_create(college.id, college.school_id))
        require_active_organization(db, college.school_id, college.id)
        require_teacher(db, body.owner_id, college.school_id)
        if not identity.manages(college.id, college.school_id):
            require(body.owner_id == identity.user.id, "教师只能创建本人负责的目录")
    def action():
        record = CourseCatalog(**body.model_dump(), school_id=college.school_id)
        record.title = body.title.strip()
        db.add(record)
        db.flush()
        return catalog_view(record)
    return execute_command(db, identity, college.school_id, "catalogs.create", key, body.model_dump(), action, authorize)


@router.patch("/catalogs/{catalog_id}", response_model=CatalogView)
def update_catalog(catalog_id: UUID, body: CatalogPatch, identity: CurrentIdentity, db: Db, key: CommandKey):
    record = require_catalog(db, identity, catalog_id, manage=True)
    def authorize():
        require_catalog(db, identity, catalog_id, manage=True)
        if "owner_id" in body.model_fields_set:
            require(identity.manages(record.college_id, record.school_id), "课程负责人调整须由有范围管理员操作")
    def action():
        db.refresh(record)
        check_revision(record, body.revision)
        if "owner_id" in body.model_fields_set:
            require(body.owner_id is not None, "目录须指定有效负责人", 422)
            require_teacher(db, body.owner_id, record.school_id)
            record.owner_id = body.owner_id
        if body.title is not None:
            record.title = body.title.strip()
        if body.archived is not None:
            if body.archived:
                active = db.exec(select(Course.id).where(Course.catalog_id == record.id, Course.archived.is_(False))).first()
                require(active is None, "请先归档目录下全部教学班", 409)
            record.archived = body.archived
        touch(record)
        db.add(record)
        return catalog_view(record)
    return execute_command(db, identity, record.school_id, f"catalogs.update.{catalog_id}", key,
                           body.model_dump(), action, authorize)


def create_class(body: CourseCreate, identity, db, key, public_serializer):
    college = db.get(College, body.college_id)
    require(college is not None, "无权在该学院创建课程", 403)
    def authorize():
        require_active_organization(db, college.school_id, college.id)
        teacher = require_teacher(db, body.teacher_id, college.school_id)
        if body.catalog_id:
            catalog = require_catalog(db, identity, body.catalog_id, manage=True)
            require(not catalog.archived, "目录已归档", 409)
            require(catalog.school_id == college.school_id, "目录与教学班不属于同校", 422)
            if catalog.college_id != college.id:
                require(school_manager(identity, college.school_id), "跨学院开班须由校管理员协调")
            require(identity.manages(college.id, college.school_id) or (
                catalog.owner_id == identity.user.id and identity.has(Role.TEACHER)
                and identity.user.college_id == college.id))
        else:
            require(identity.can_create(college.id, college.school_id), "无权在该学院创建课程")
        if not identity.manages(college.id, college.school_id):
            require(teacher.id == identity.user.id, "教师只能创建由本人负责的教学班")
    def action():
        title = body.title.strip()
        require(bool(title), "课程名称不能为空", 422)
        if body.catalog_id:
            catalog = db.get(CourseCatalog, body.catalog_id)
        else:
            catalog = CourseCatalog(school_id=college.school_id, college_id=college.id, owner_id=body.teacher_id,
                                    code=body.code, title=title)
            db.add(catalog)
            db.flush()
        course = Course(school_id=college.school_id, college_id=college.id, catalog_id=catalog.id,
                        code=body.code, title=title)
        db.add(course)
        db.flush()
        db.add(CourseStaff(school_id=course.school_id, course_id=course.id, user_id=body.teacher_id, is_primary=True))
        db.flush()
        return public_serializer(course, db)
    return execute_command(db, identity, college.school_id, "courses.create", key, body.model_dump(), action, authorize)


@router.get("/courses/{course_id}/management", response_model=ClassManagementView)
def class_management(course_id: UUID, identity: CurrentIdentity, db: Db):
    record = require_class(db, identity, course_id, manage=True, history=True)
    return management_view(db, identity, record)


@router.patch("/courses/{course_id}/settings", response_model=ClassManagementView)
def update_settings(course_id: UUID, body: CourseSettings, identity: CurrentIdentity, db: Db, key: CommandKey):
    def authorize():
        require_class(db, identity, course_id, primary=True, write=True)
    def action():
        record = locked_class(db, identity, course_id, primary=True)
        check_revision(record, body.revision)
        for field, value in body.model_dump(exclude_unset=True, exclude={"revision"}).items():
            require(value is not None, "班级配置不可为空", 422)
            setattr(record, field, value.strip() if isinstance(value, str) else value)
        touch(record)
        db.add(record)
        return management_view(db, identity, record)
    return execute_command(db, identity, class_scope(db, course_id), f"courses.settings.{course_id}", key,
                           body.model_dump(), action, authorize)


@router.get("/courses/{course_id}/staff", response_model=Page[StaffView])
def list_staff(course_id: UUID, identity: CurrentIdentity, db: Db,
               q: str = Query(default="", max_length=100),
               offset: int = Query(default=0, ge=0), limit: int = Query(default=100, ge=1, le=100)):
    require_class(db, identity, course_id, manage=True, history=True)
    query = select(CourseStaff).join(User, User.id == CourseStaff.user_id).where(CourseStaff.course_id == course_id,
        or_(User.display_name.ilike(keyword(q)), User.username.ilike(keyword(q)))).order_by(CourseStaff.is_primary.desc(), CourseStaff.id)
    result = page(db, query, offset, limit)
    return {"data": [StaffView(user_id=s.user_id, display_name=db.get(User, s.user_id).display_name,
                               is_primary=s.is_primary, is_active=s.is_active) for s in result["data"]], "count": result["count"]}


@router.post("/courses/{course_id}/staff", response_model=ClassManagementView)
def add_staff(course_id: UUID, body: StaffInput, identity: CurrentIdentity, db: Db, key: CommandKey):
    def authorize():
        require_class(db, identity, course_id, primary=True, write=True)
    def action():
        record = locked_class(db, identity, course_id, primary=True)
        check_revision(record, body.revision)
        require_teacher(db, body.teacher_id, record.school_id)
        staff = db.exec(select(CourseStaff).where(CourseStaff.course_id == course_id, CourseStaff.user_id == body.teacher_id)).first()
        if staff:
            staff.is_active = True
        else:
            staff = CourseStaff(school_id=record.school_id, course_id=record.id, user_id=body.teacher_id)
        db.add(staff)
        touch(record)
        db.add(record)
        return management_view(db, identity, record)
    return execute_command(db, identity, class_scope(db, course_id), f"courses.staff.add.{course_id}", key,
                           body.model_dump(), action, authorize)


@router.get("/courses/{course_id}/teacher-options", response_model=Page[TeacherOption])
def teacher_options(course_id: UUID, identity: CurrentIdentity, db: Db, q: str = Query(min_length=2, max_length=100),
                    offset: int = Query(default=0, ge=0), limit: int = Query(default=10, ge=1, le=20)):
    course = require_class(db, identity, course_id, primary=True, write=True)
    query = select(User).where(User.school_id == course.school_id, User.is_active.is_(True),
        User.id.in_(select(RoleGrant.user_id).where(RoleGrant.role == Role.TEACHER)),
        or_(User.username.ilike(keyword(q)), User.display_name.ilike(keyword(q)))).order_by(User.username, User.id)
    return page(db, query, offset, limit)


@router.post("/courses/{course_id}/remove-staff", response_model=ClassManagementView)
def remove_staff(course_id: UUID, body: StaffInput, identity: CurrentIdentity, db: Db, key: CommandKey):
    def authorize():
        require_class(db, identity, course_id, primary=True, write=True)
    def action():
        record = locked_class(db, identity, course_id, primary=True)
        check_revision(record, body.revision)
        staff = db.exec(select(CourseStaff).where(CourseStaff.course_id == course_id, CourseStaff.user_id == body.teacher_id)).first()
        require(staff is not None and staff.is_active, "协作教师不存在", 409)
        require(not staff.is_primary, "主教师须通过交接更换", 409)
        staff.is_active = False
        db.add(staff)
        touch(record)
        db.add(record)
        return management_view(db, identity, record)
    return execute_command(db, identity, class_scope(db, course_id), f"courses.staff.remove.{course_id}", key,
                           body.model_dump(), action, authorize)


@router.post("/courses/{course_id}/transfer", response_model=ClassManagementView)
def transfer_class(course_id: UUID, body: StaffInput, identity: CurrentIdentity, db: Db, key: CommandKey):
    def authorize():
        require_class(db, identity, course_id, primary=True, write=True)
    def action():
        record = locked_class(db, identity, course_id, primary=True)
        check_revision(record, body.revision)
        require_teacher(db, body.teacher_id, record.school_id)
        previous = db.exec(select(CourseStaff).where(CourseStaff.course_id == course_id,
                           CourseStaff.is_primary.is_(True), CourseStaff.is_active.is_(True))).first()
        require(previous is not None and previous.user_id != body.teacher_id, "请选择不同的接任教师", 422)
        previous.is_primary, previous.is_active = False, False
        db.add(previous)
        db.flush()  # Release partial unique index before promoting the replacement.
        replacement = db.exec(select(CourseStaff).where(CourseStaff.course_id == course_id,
                              CourseStaff.user_id == body.teacher_id)).first()
        if replacement is None:
            replacement = CourseStaff(school_id=record.school_id, course_id=course_id, user_id=body.teacher_id)
        replacement.is_primary, replacement.is_active = True, True
        db.add(replacement)
        touch(record)
        db.add(record)
        db.flush()
        # The outgoing teacher loses this class immediately; return the state without reading through old permission.
        return management_view(db, identity, record)
    return execute_command(db, identity, class_scope(db, course_id), f"courses.transfer.{course_id}", key,
                           body.model_dump(), action, authorize)


def cancel_requests(db, course_id, user_id=None):
    query = select(EnrollmentRequest).where(EnrollmentRequest.course_id == course_id, EnrollmentRequest.status == "pending")
    if user_id:
        query = query.where(EnrollmentRequest.user_id == user_id)
    for pending in db.exec(query).all():
        pending.status, pending.decided_at = "canceled", datetime.now(UTC)
        db.add(pending)


@router.post("/courses/{course_id}/archive", response_model=ClassManagementView)
def archive_class(course_id: UUID, body: RevisionInput, identity: CurrentIdentity, db: Db, key: CommandKey):
    def authorize():
        require_class(db, identity, course_id, primary=True, history=True)
    def action():
        record = locked_class(db, identity, course_id, primary=True)
        check_revision(record, body.revision)
        record.archived, record.join_code_hash, record.join_code_expires_at = True, None, None
        touch(record)
        db.add(record)
        cancel_requests(db, course_id)
        return management_view(db, identity, record)
    return execute_command(db, identity, class_scope(db, course_id), f"courses.archive.{course_id}", key,
                           body.model_dump(), action, authorize)


@router.post("/courses/{course_id}/invite", response_model=JoinCodeIssued)
def rotate_join_code(course_id: UUID, body: InviteInput, identity: CurrentIdentity, db: Db, key: CommandKey):
    code = issued_code(f"class:{course_id}", key)
    def authorize():
        require_class(db, identity, course_id, primary=True, write=True)
    def action():
        record = locked_class(db, identity, course_id, primary=True)
        check_revision(record, body.revision)
        require(body.expires_at.replace(tzinfo=UTC) > datetime.now(UTC), "有效期须晚于现在", 422)
        record.join_code_hash, record.join_code_expires_at = code_hash(code), body.expires_at
        touch(record)
        db.add(record)
        return {"course_id": record.id, "expires_at": record.join_code_expires_at, "revision": record.revision}
    result = execute_command(db, identity, class_scope(db, course_id), f"courses.invite.{course_id}", key,
                             body.model_dump(), action, authorize)
    return {**result, "code": code}


def set_enrollment(db, course, user, status):
    enrollment = db.exec(select(Enrollment).where(Enrollment.course_id == course.id, Enrollment.user_id == user.id)).first()
    if enrollment is None:
        enrollment = Enrollment(school_id=course.school_id, course_id=course.id, user_id=user.id, status=status)
    else:
        enrollment.status = status
    db.add(enrollment)
    db.flush()
    return enrollment


def pull_member(db, course, username):
    user = db.exec(select(User).where(User.school_id == course.school_id, User.username == username)).first()
    require_student(db, user, course.school_id)
    enrollment = set_enrollment(db, course, user, "active")
    cancel_requests(db, course.id, user.id)
    return enrollment


@router.get("/courses/{course_id}/members", response_model=Page[MemberView])
def members(course_id: UUID, identity: CurrentIdentity, db: Db, q: str = Query(default="", max_length=100),
            status: str = Query(default="active", pattern=r"^(active|withdrawn|removed|all)$"),
            offset: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=100)):
    require_class(db, identity, course_id, manage=True, history=True)
    query = select(Enrollment).join(User, User.id == Enrollment.user_id).where(Enrollment.course_id == course_id,
        or_(User.username.ilike(keyword(q)), User.display_name.ilike(keyword(q)), User.student_no.ilike(keyword(q))))
    if status != "all":
        query = query.where(Enrollment.status == status)
    result = page(db, query.order_by(User.username, Enrollment.id), offset, limit)
    data = []
    for item in result["data"]:
        user = db.get(User, item.user_id)
        data.append(MemberView(**user.model_dump(), status=item.status))
    return {"data": data, "count": result["count"]}


@router.post("/courses/{course_id}/members", response_model=EnrollmentResult)
def add_member(course_id: UUID, body: MemberInput, identity: CurrentIdentity, db: Db, key: CommandKey):
    def authorize():
        require_class(db, identity, course_id, manage=True, write=True)
    def action():
        record = locked_class(db, identity, course_id)
        pull_member(db, record, body.username)
        return EnrollmentResult(course_id=record.id, status="active")
    return execute_command(db, identity, class_scope(db, course_id), f"courses.members.add.{course_id}", key,
                           body.model_dump(), action, authorize)


@router.post("/courses/{course_id}/remove-member", response_model=EnrollmentResult)
def remove_member(course_id: UUID, body: MemberInput, identity: CurrentIdentity, db: Db, key: CommandKey):
    def authorize():
        require_class(db, identity, course_id, manage=True, write=True)
    def action():
        record = locked_class(db, identity, course_id)
        user = db.exec(select(User).where(User.school_id == record.school_id, User.username == body.username)).first()
        enrollment = db.exec(select(Enrollment).where(Enrollment.course_id == course_id,
                                                    Enrollment.user_id == user.id)).first() if user else None
        require(enrollment is not None, "学生不在本班名单", 404)
        enrollment.status = "removed"
        db.add(enrollment)
        cancel_requests(db, course_id, user.id)
        return EnrollmentResult(course_id=course_id, status="removed")
    return execute_command(db, identity, class_scope(db, course_id), f"courses.members.remove.{course_id}", key,
                           body.model_dump(), action, authorize)


def pending_request(db, course_id, user_id, kind):
    pending = db.exec(select(EnrollmentRequest).where(EnrollmentRequest.course_id == course_id,
        EnrollmentRequest.user_id == user_id, EnrollmentRequest.kind == kind, EnrollmentRequest.status == "pending")).first()
    if pending is None:
        course = db.get(Course, course_id)
        pending = EnrollmentRequest(school_id=course.school_id, course_id=course_id, user_id=user_id, kind=kind)
        db.add(pending)
        db.flush()
    return pending


@router.post("/enrollments/join", response_model=EnrollmentResult)
def join_class(body: JoinInput, identity: CurrentIdentity, db: Db, key: CommandKey):
    def authorize():
        require(identity.has(Role.STUDENT))
        require_student(db, identity.user, identity.user.school_id)
    def action():
        record = db.exec(select(Course).where(Course.school_id == identity.user.school_id,
                          Course.join_code_hash == code_hash(body.invitation_code), Course.archived.is_(False))).first()
        require(record is not None and record.join_code_expires_at is not None
                and record.join_code_expires_at.replace(tzinfo=UTC) > datetime.now(UTC), "班级邀请码无效或已过期", 422)
        enrollment = db.exec(select(Enrollment).where(Enrollment.course_id == record.id, Enrollment.user_id == identity.user.id)).first()
        if enrollment and enrollment.status == "active":
            return EnrollmentResult(course_id=record.id, status="active")
        if record.join_approval:
            pending = pending_request(db, record.id, identity.user.id, "join")
            return EnrollmentResult(course_id=record.id, status="pending_join", request_id=pending.id)
        set_enrollment(db, record, identity.user, "active")
        cancel_requests(db, record.id, identity.user.id)
        return EnrollmentResult(course_id=record.id, status="active")
    return execute_command(db, identity, identity.user.school_id, "enrollments.join", key,
                           body.model_dump(), action, authorize)


@router.post("/courses/{course_id}/leave", response_model=EnrollmentResult)
def leave_class(course_id: UUID, identity: CurrentIdentity, db: Db, key: CommandKey):
    def authorize():
        require(identity.has(Role.STUDENT))
        # A retry after successful withdrawal may read its receipt, but never returns course content.
        record = db.get(Course, course_id)
        require(record is not None and record.school_id == identity.user.school_id, "教学班不存在", 404)
    def action():
        record = require_class(db, identity, course_id, write=True)
        if record.leave_approval:
            pending = pending_request(db, record.id, identity.user.id, "leave")
            return EnrollmentResult(course_id=record.id, status="pending_leave", request_id=pending.id)
        set_enrollment(db, record, identity.user, "withdrawn")
        cancel_requests(db, record.id, identity.user.id)
        return EnrollmentResult(course_id=record.id, status="withdrawn")
    return execute_command(db, identity, class_scope(db, course_id), f"enrollments.leave.{course_id}", key, {}, action, authorize)


@router.get("/courses/{course_id}/requests", response_model=Page[RequestView])
def requests(course_id: UUID, identity: CurrentIdentity, db: Db, status: str = Query(default="pending",
             pattern=r"^(pending|approved|rejected|canceled|all)$"), offset: int = Query(default=0, ge=0),
             limit: int = Query(default=50, ge=1, le=100)):
    require_class(db, identity, course_id, manage=True, history=True)
    query = select(EnrollmentRequest).where(EnrollmentRequest.course_id == course_id)
    if status != "all":
        query = query.where(EnrollmentRequest.status == status)
    result = page(db, query.order_by(EnrollmentRequest.created_at.desc(), EnrollmentRequest.id), offset, limit)
    return {"data": [request_view(db, item) for item in result["data"]], "count": result["count"]}


@router.get("/enrollments/requests", response_model=Page[RequestView])
def my_requests(identity: CurrentIdentity, db: Db, offset: int = Query(default=0, ge=0),
                limit: int = Query(default=50, ge=1, le=100)):
    require(identity.has(Role.STUDENT))
    query = select(EnrollmentRequest).where(EnrollmentRequest.user_id == identity.user.id,
        EnrollmentRequest.school_id == identity.user.school_id).order_by(EnrollmentRequest.created_at.desc(), EnrollmentRequest.id)
    result = page(db, query, offset, limit)
    return {"data": [request_view(db, item) for item in result["data"]], "count": result["count"]}


@router.post("/enrollments/requests/{request_id}/cancel", response_model=Message)
def cancel_my_request(request_id: UUID, identity: CurrentIdentity, db: Db, key: CommandKey):
    def authorize():
        require(identity.has(Role.STUDENT))
        request = db.get(EnrollmentRequest, request_id)
        require(request is not None and request.user_id == identity.user.id
                and request.school_id == identity.user.school_id, "申请不存在", 404)
    def action():
        request = db.get(EnrollmentRequest, request_id)
        require(request.status == "pending", "申请已经处理", 409)
        request.status, request.decided_at = "canceled", datetime.now(UTC)
        db.add(request)
        return {"message": "申请已取消"}
    return execute_command(db, identity, identity.user.school_id, f"enrollments.cancel.{request_id}", key, {}, action, authorize)


@router.post("/courses/{course_id}/requests/{request_id}/decide", response_model=RequestView)
def decide_request(course_id: UUID, request_id: UUID, body: RequestDecision, identity: CurrentIdentity, db: Db, key: CommandKey):
    def authorize():
        require_class(db, identity, course_id, manage=True, write=True)
    def action():
        record = locked_class(db, identity, course_id)
        pending = db.get(EnrollmentRequest, request_id)
        require(pending is not None and pending.course_id == course_id, "申请不存在", 404)
        require(pending.status == "pending", "申请已经处理，请刷新", 409)
        user = db.get(User, pending.user_id)
        if body.approve:
            if pending.kind == "join":
                require_student(db, user, record.school_id)
                set_enrollment(db, record, user, "active")
            else:
                set_enrollment(db, record, user, "withdrawn")
        pending.status = "approved" if body.approve else "rejected"
        pending.decided_at, pending.decided_by = datetime.now(UTC), identity.user.id
        db.add(pending)
        return request_view(db, pending)
    return execute_command(db, identity, class_scope(db, course_id), f"enrollments.decide.{request_id}", key,
                           body.model_dump(), action, authorize)
