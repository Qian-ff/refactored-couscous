from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.core.grants import add_role_grant, validate_role_family
from app.core.security import get_password_hash, verify_password
from app.domains.core.auth import AccountIdentity, CurrentAccount, CurrentIdentity, Db
from app.domains.core.business_schemas import (
    AccountCreate, AccountPatch, AccountView, CommandKey, GrantInput, InvitationCreate,
    InvitationContextView, InvitationIssued, InvitationView, OrganizationInput, OrganizationPatch, OrganizationView,
    Page, PasswordChange, PasswordReset, ProfilePatch, Registration,
)
from app.domains.core.commands import (
    check_revision, code_hash, execute_command, issued_code, revoke_sessions, tenant_write_lock, touch,
)
from app.domains.core.csv_tools import fingerprint
from app.domains.core.models import (
    AccountInvitation, College, CommandReceipt, CoreAuditEvent, Course, CourseStaff, Major, Role, RoleGrant, School, User,
)
from app.domains.core.policy import (
    admin_colleges, require, require_account, require_active_organization, require_grant_authority,
    require_school_manager, visible_account_query,
)
from app.domains.core.schemas import Message

router = APIRouter(tags=["management"])


def keyword(value: str):
    return "%" + value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def page(db, query, offset, limit):
    count = db.exec(select(func.count()).select_from(query.order_by(None).subquery())).one()
    return {"data": list(db.exec(query.offset(offset).limit(limit)).all()), "count": count}


def organization_view(record):
    return OrganizationView.model_validate(record, from_attributes=True)


def account_view(db, user):
    value = AccountView.model_validate({**user.model_dump(), "grants": [
        GrantInput(role=g.role, college_id=g.college_id)
        for g in db.exec(select(RoleGrant).where(RoleGrant.user_id == user.id).order_by(RoleGrant.role, RoleGrant.id)).all()
    ]})
    return value


def require_no_active_primary(db, user_id):
    primary = db.exec(select(CourseStaff.id).join(Course, Course.id == CourseStaff.course_id).where(
        CourseStaff.user_id == user_id, CourseStaff.is_primary.is_(True), CourseStaff.is_active.is_(True),
        Course.archived.is_(False))).first()
    require(primary is None, "该教师仍负责在用教学班，请先完成主教师交接", 409)


def organization_query(identity, model):
    require(identity.work_role == "administrator")
    query = select(model)
    if identity.has(Role.PLATFORM_ADMIN):
        return query
    if model is School:
        return query.where(School.id == identity.user.school_id)
    query = query.where(model.school_id == identity.user.school_id)
    if identity.has(Role.SCHOOL_ADMIN):
        return query
    return query.where((College.id if model is College else Major.college_id).in_(admin_colleges(identity)))


@router.get("/admin/schools", response_model=Page[OrganizationView])
def list_schools(identity: CurrentIdentity, db: Db, q: str = Query(default="", max_length=100),
                 offset: int = Query(default=0, ge=0), limit: int = Query(default=100, ge=1, le=100)):
    return page(db, organization_query(identity, School).where(or_(School.code.ilike(keyword(q)),
                School.name.ilike(keyword(q)))).order_by(School.code, School.id), offset, limit)


@router.get("/admin/colleges", response_model=Page[OrganizationView])
def list_colleges(identity: CurrentIdentity, db: Db, school_id: UUID | None = None,
                  q: str = Query(default="", max_length=100), offset: int = Query(default=0, ge=0),
                  limit: int = Query(default=100, ge=1, le=100)):
    query = organization_query(identity, College)
    if school_id:
        query = query.where(College.school_id == school_id)
    return page(db, query.where(or_(College.code.ilike(keyword(q)), College.name.ilike(keyword(q)))).order_by(
        College.code, College.id), offset, limit)


@router.get("/admin/majors", response_model=Page[OrganizationView])
def list_majors(identity: CurrentIdentity, db: Db, college_id: UUID | None = None,
                q: str = Query(default="", max_length=100), offset: int = Query(default=0, ge=0),
                limit: int = Query(default=100, ge=1, le=100)):
    query = organization_query(identity, Major)
    if college_id:
        query = query.where(Major.college_id == college_id)
    return page(db, query.where(or_(Major.code.ilike(keyword(q)), Major.name.ilike(keyword(q)))).order_by(
        Major.code, Major.id), offset, limit)


def create_organization(model, body, identity, db, key):
    school_id = body.school_id
    def authorize():
        if model is School:
            require(identity.has(Role.PLATFORM_ADMIN))
            require(body.code != "platform", "platform 是平台运维保留登录代码", 422)
        elif model is College:
            require_school_manager(identity, school_id)
            school = db.get(School, school_id) if school_id else None
            require(school is not None and school.is_active, "学校不存在或已停用", 422)
        else:
            require(body.college_id is not None and school_id is not None, "须指定学校和学院", 422)
            require(identity.manages(body.college_id, school_id))
            require_active_organization(db, school_id, body.college_id)
    def action():
        values = {"code": body.code, "name": body.name.strip()}
        if model is not School:
            values["school_id"] = school_id
        if model is Major:
            values["college_id"] = body.college_id
        record = model(**values)
        db.add(record)
        db.flush()
        return organization_view(record)
    return execute_command(db, identity, school_id, f"organizations.create.{model.__tablename__}",
                           key, body.model_dump(), action, authorize)


@router.post("/admin/schools", response_model=OrganizationView, status_code=201)
def create_school(body: OrganizationInput, identity: CurrentIdentity, db: Db, key: CommandKey):
    return create_organization(School, body, identity, db, key)


@router.post("/admin/colleges", response_model=OrganizationView, status_code=201)
def create_college(body: OrganizationInput, identity: CurrentIdentity, db: Db, key: CommandKey):
    return create_organization(College, body, identity, db, key)


@router.post("/admin/majors", response_model=OrganizationView, status_code=201)
def create_major(body: OrganizationInput, identity: CurrentIdentity, db: Db, key: CommandKey):
    return create_organization(Major, body, identity, db, key)


def update_organization(model, record_id, body, identity, db, key):
    record = db.exec(organization_query(identity, model).where(model.id == record_id)).first()
    require(record is not None, "组织不存在或不在授权范围", 404)
    school_id = record.id if model is School else record.school_id
    def authorize():
        if model is School:
            require(identity.has(Role.PLATFORM_ADMIN))
        elif model is College:
            require_school_manager(identity, school_id)
        else:
            require(identity.manages(record.college_id, school_id))
    def action():
        db.refresh(record)
        check_revision(record, body.revision)
        for field, value in body.model_dump(exclude_unset=True, exclude={"revision"}).items():
            require(value is not None, "名称和启用状态不可为空", 422)
            setattr(record, field, value.strip() if isinstance(value, str) else value)
        touch(record)
        db.add(record)
        db.flush()
        return organization_view(record)
    return execute_command(db, identity, school_id, f"organizations.update.{record_id}", key,
                           body.model_dump(), action, authorize)


@router.patch("/admin/schools/{record_id}", response_model=OrganizationView)
def update_school(record_id: UUID, body: OrganizationPatch, identity: CurrentIdentity, db: Db, key: CommandKey):
    return update_organization(School, record_id, body, identity, db, key)


@router.patch("/admin/colleges/{record_id}", response_model=OrganizationView)
def update_college(record_id: UUID, body: OrganizationPatch, identity: CurrentIdentity, db: Db, key: CommandKey):
    return update_organization(College, record_id, body, identity, db, key)


@router.patch("/admin/majors/{record_id}", response_model=OrganizationView)
def update_major(record_id: UUID, body: OrganizationPatch, identity: CurrentIdentity, db: Db, key: CommandKey):
    return update_organization(Major, record_id, body, identity, db, key)


@router.get("/admin/accounts", response_model=Page[AccountView])
def list_accounts(identity: CurrentIdentity, db: Db, school_id: UUID | None = None, college_id: UUID | None = None,
                  role: Role | None = None, q: str = Query(default="", max_length=100),
                  offset: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=100)):
    query = visible_account_query(identity)
    if school_id:
        query = query.where(User.school_id == school_id)
    if college_id:
        query = query.where(User.college_id == college_id)
    if role:
        query = query.where(User.id.in_(select(RoleGrant.user_id).where(RoleGrant.role == role)))
    query = query.where(or_(User.username.ilike(keyword(q)), User.display_name.ilike(keyword(q)),
                           User.student_no.ilike(keyword(q)))).order_by(User.username, User.id)
    result = page(db, query, offset, limit)
    return {"data": [account_view(db, user) for user in result["data"]], "count": result["count"]}


@router.get("/admin/accounts/{user_id}", response_model=AccountView)
def get_account(user_id: UUID, identity: CurrentIdentity, db: Db):
    return account_view(db, require_account(db, identity, user_id))


def validate_new_account(db, identity, body):
    require(identity.work_role == "administrator")
    require(identity.manages(body.college_id, body.school_id))
    require_active_organization(db, body.school_id, body.college_id, body.major_id)
    try:
        validate_role_family({g.role for g in body.grants})
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    if any(g.role == Role.STUDENT for g in body.grants):
        require(body.student_no is not None and body.major_id is not None, "新学生须填写独立学号和专业", 422)
    require(len({(g.role, g.college_id) for g in body.grants}) == len(body.grants), "授权重复", 422)
    for grant in body.grants:
        require_grant_authority(identity, body.school_id, body.college_id, grant.role, grant.college_id)
        if grant.college_id:
            require_active_organization(db, body.school_id, grant.college_id)
    require(db.exec(select(User).where(User.school_id == body.school_id, User.username == body.username)).first() is None,
            "账号已存在，导入或创建不能覆盖", 409)
    if body.student_no:
        require(db.exec(select(User).where(User.school_id == body.school_id, User.student_no == body.student_no)).first() is None,
                "学号已存在", 409)


def insert_account(db, body, *, must_change=True):
    values = body.model_dump(exclude={"grants", "temporary_password"})
    values["display_name"] = body.display_name.strip()
    user = User(**values, hashed_password=get_password_hash(body.temporary_password.get_secret_value()),
                must_change_password=must_change)
    db.add(user)
    db.flush()
    for grant in body.grants:
        add_role_grant(db, user_id=user.id, role=grant.role, college_id=grant.college_id)
    return user


@router.post("/admin/accounts", response_model=AccountView, status_code=201)
def create_account(body: AccountCreate, identity: CurrentIdentity, db: Db, key: CommandKey):
    def authorize():
        require(identity.manages(body.college_id, body.school_id))
        for grant in body.grants:
            require_grant_authority(identity, body.school_id, body.college_id, grant.role, grant.college_id)
    def action():
        validate_new_account(db, identity, body)
        return account_view(db, insert_account(db, body))
    return execute_command(db, identity, body.school_id, "accounts.create", key, body.model_dump(), action, authorize,
                           lambda result: require_account(db, identity, UUID(result["id"])))


@router.patch("/admin/accounts/{user_id}", response_model=AccountView)
def update_account(user_id: UUID, body: AccountPatch, identity: CurrentIdentity, db: Db, key: CommandKey):
    user = require_account(db, identity, user_id, write=True)
    def authorize():
        require_account(db, identity, user_id, write=True)
    def action():
        db.exec(select(User).where(User.id == user_id).with_for_update()).one()
        db.refresh(user)
        require_account(db, identity, user_id, write=True)
        check_revision(user, body.revision)
        values = body.model_dump(exclude_unset=True, exclude={"revision"})
        student = db.exec(select(RoleGrant.id).where(RoleGrant.user_id == user_id, RoleGrant.role == Role.STUDENT)).first()
        if student:
            # Legacy missing fields stay compatible; established student identity fields cannot be erased.
            for field in ("student_no", "major_id"):
                if getattr(user, field) is not None and field in values:
                    require(values[field] is not None, "学生学号和专业不可清空；更正时请选择有效值", 422)
        college_id = values.get("college_id", user.college_id)
        require(college_id is not None, "学校账号须保留学院", 422)
        require(identity.manages(college_id, user.school_id))
        require_active_organization(db, user.school_id, college_id, values.get("major_id", user.major_id))
        for field, value in values.items():
            if field in {"display_name", "is_active"}:
                require(value is not None, "姓名或状态不可为空", 422)
            setattr(user, field, value.strip() if isinstance(value, str) else value)
        if not user.is_active:
            require_no_active_primary(db, user.id)
        touch(user)
        db.add(user)
        if not user.is_active:
            revoke_sessions(db, user.id)
        db.flush()
        return account_view(db, user)
    return execute_command(db, identity, user.school_id, f"accounts.update.{user_id}", key,
                           body.model_dump(), action, authorize)


@router.post("/admin/accounts/{user_id}/grants", response_model=AccountView)
def grant_role(user_id: UUID, body: GrantInput, identity: CurrentIdentity, db: Db, key: CommandKey):
    user = require_account(db, identity, user_id, write=True)
    def authorize():
        require_account(db, identity, user_id, write=True)
        require_grant_authority(identity, user.school_id, user.college_id, body.role, body.college_id)
        if body.college_id:
            require_active_organization(db, user.school_id, body.college_id)
    def action():
        if body.role == Role.STUDENT:
            require(user.student_no is not None and user.major_id is not None, "授予学生身份前须完善学号和专业", 422)
        try:
            add_role_grant(db, user_id=user.id, role=body.role, college_id=body.college_id)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
        touch(user)
        db.add(user)
        return account_view(db, user)
    return execute_command(db, identity, user.school_id, f"accounts.grant.{user_id}", key,
                           body.model_dump(), action, authorize)


@router.post("/admin/accounts/{user_id}/revoke-grant", response_model=AccountView)
def revoke_role(user_id: UUID, body: GrantInput, identity: CurrentIdentity, db: Db, key: CommandKey):
    user = require_account(db, identity, user_id, write=True)
    def authorize():
        require_account(db, identity, user_id, write=True)
        require_grant_authority(identity, user.school_id, user.college_id, body.role, body.college_id)
    def action():
        db.exec(select(User).where(User.id == user_id).with_for_update()).one()
        require_account(db, identity, user_id, write=True)
        if body.role == Role.TEACHER:
            require_no_active_primary(db, user_id)
        grant = db.exec(select(RoleGrant).where(RoleGrant.user_id == user_id, RoleGrant.role == body.role,
                                               RoleGrant.college_id == body.college_id)).first()
        require(grant is not None, "授权已不存在", 409)
        db.delete(grant)
        touch(user)
        db.add(user)
        db.flush()
        return account_view(db, user)
    return execute_command(db, identity, user.school_id, f"accounts.revoke.{user_id}", key,
                           body.model_dump(), action, authorize)


@router.post("/admin/accounts/{user_id}/reset-password", response_model=Message)
def reset_password(user_id: UUID, body: PasswordReset, identity: CurrentIdentity, db: Db, key: CommandKey):
    user = require_account(db, identity, user_id, write=True)
    def action():
        db.exec(select(User).where(User.id == user_id).with_for_update()).one()
        require_account(db, identity, user_id, write=True)
        user.hashed_password = get_password_hash(body.temporary_password.get_secret_value())
        user.must_change_password = True
        touch(user)
        db.add(user)
        revoke_sessions(db, user.id)
        return {"message": "临时密码已设置，旧会话已撤销；账号下次登录须改密"}
    return execute_command(db, identity, user.school_id, f"accounts.password.{user_id}", key,
                           body.model_dump(), action, lambda: require_account(db, identity, user_id, write=True))


@router.get("/profile", response_model=AccountView)
def get_profile(identity: AccountIdentity, db: Db):
    return account_view(db, identity.user)


@router.patch("/profile", response_model=AccountView)
def update_profile(body: ProfilePatch, identity: CurrentIdentity, db: Db, key: CommandKey):
    def action():
        check_revision(identity.user, body.revision)
        for field, value in body.model_dump(exclude_unset=True, exclude={"revision"}).items():
            setattr(identity.user, field, value)
        touch(identity.user)
        db.add(identity.user)
        return account_view(db, identity.user)
    return execute_command(db, identity, identity.user.school_id, "profile.update", key, body.model_dump(), action)


@router.post("/auth/change-password", response_model=Message, tags=["auth"])
def change_password(body: PasswordChange, account: CurrentAccount, db: Db):
    try:
        tenant_write_lock(db, account.user.school_id)
        user = db.exec(select(User).where(User.id == account.user.id).with_for_update()).one()
        db.refresh(user)
        db.refresh(account.login)
        require(user.is_active and not account.login.revoked, "登录已失效，请重新登录", 401)
        old, new = body.old_password.get_secret_value(), body.new_password.get_secret_value()
        require(verify_password(old, user.hashed_password)[0], "原密码不正确", 422)
        require(old != new, "新密码应与原密码不同", 422)
        user.hashed_password = get_password_hash(new)
        user.must_change_password = False
        touch(user)
        db.add(user)
        revoke_sessions(db, user.id)
        db.add(CoreAuditEvent(school_id=user.school_id, actor_id=user.id, work_role="account",
                              operation="password.change", entity_id=user.id))
        db.commit()
        return Message(message="密码已修改，所有旧会话已撤销，请重新登录")
    except Exception:
        db.rollback()
        raise


@router.get("/admin/account-invitations", response_model=Page[InvitationView])
def list_invitations(identity: CurrentIdentity, db: Db, offset: int = Query(default=0, ge=0),
                     limit: int = Query(default=100, ge=1, le=100)):
    require(identity.work_role == "administrator")
    query = select(AccountInvitation)
    if not identity.has(Role.PLATFORM_ADMIN):
        query = query.where(AccountInvitation.school_id == identity.user.school_id)
        if not identity.has(Role.SCHOOL_ADMIN):
            query = query.where(AccountInvitation.college_id.in_(admin_colleges(identity)))
    return page(db, query.order_by(AccountInvitation.expires_at.desc(), AccountInvitation.id), offset, limit)


@router.post("/admin/account-invitations", response_model=InvitationIssued, status_code=201)
def create_invitation(body: InvitationCreate, identity: CurrentIdentity, db: Db, key: CommandKey):
    code = issued_code(f"account:{identity.user.id}", key)
    def authorize():
        require(identity.manages(body.college_id, body.school_id))
        require_active_organization(db, body.school_id, body.college_id, body.major_id)
    def action():
        require(body.expires_at.replace(tzinfo=UTC) > datetime.now(UTC), "有效期须晚于现在", 422)
        invite = AccountInvitation(**body.model_dump(), code_hash=code_hash(code), created_by=identity.user.id)
        db.add(invite)
        db.flush()
        return InvitationView.model_validate(invite, from_attributes=True)
    result = execute_command(db, identity, body.school_id, "account-invitations.create", key,
                             body.model_dump(), action, authorize)
    return {**result, "code": code}


@router.post("/admin/account-invitations/{invitation_id}/revoke", response_model=Message)
def revoke_invitation(invitation_id: UUID, identity: CurrentIdentity, db: Db, key: CommandKey):
    invite = db.get(AccountInvitation, invitation_id)
    require(invite is not None, "邀请不存在", 404)
    def authorize():
        require(identity.manages(invite.college_id, invite.school_id), "邀请不存在或无权访问", 404)
    def action():
        invite.revoked = True
        db.add(invite)
        return {"message": "邀请已撤销"}
    return execute_command(db, identity, invite.school_id, f"account-invitations.revoke.{invitation_id}",
                           key, {}, action, authorize)


def lookup_invitation(db, school_code, code):
    school = db.exec(select(School).where(School.code == school_code, School.is_active.is_(True))).first()
    invite = db.exec(select(AccountInvitation).where(AccountInvitation.code_hash == code_hash(code))).first()
    require(school is not None and invite is not None and invite.school_id == school.id,
            "邀请不存在、已失效或不属于该学校", 422)
    return school, invite


def valid_invitation(invite):
    require(not invite.revoked and invite.used_count < invite.max_uses
            and invite.expires_at.replace(tzinfo=UTC) > datetime.now(UTC), "邀请已失效或使用次数已满", 422)


@router.get("/auth/invitations/{code}", tags=["auth"], response_model=InvitationContextView)
def invitation_context(code: str, db: Db, school_code: str = Query(min_length=1, max_length=40)):
    school, invite = lookup_invitation(db, school_code, code)
    valid_invitation(invite)
    require_active_organization(db, school.id, invite.college_id, invite.major_id)
    college = db.get(College, invite.college_id)
    majors = select(Major).where(Major.school_id == school.id, Major.college_id == college.id, Major.is_active.is_(True))
    if invite.major_id:
        majors = majors.where(Major.id == invite.major_id)
    return {"school_id": school.id, "school_name": school.name, "college_id": college.id,
            "college_name": college.name, "majors": [organization_view(m) for m in db.exec(majors.order_by(Major.code)).all()]}


@router.post("/auth/register", response_model=Message, status_code=201, tags=["auth"])
def register_account(body: Registration, db: Db, key: CommandKey):
    school, invite = lookup_invitation(db, body.school_code, body.invitation_code)
    try:
        tenant_write_lock(db, school.id)
        db.refresh(invite)
        require(not invite.revoked, "邀请已撤销", 422)
        subject = f"register:{invite.id}"
        digest = fingerprint(body.model_dump())
        receipt = db.exec(select(CommandReceipt).where(CommandReceipt.subject == subject,
            CommandReceipt.work_role == "public", CommandReceipt.operation == "register", CommandReceipt.key == key)).first()
        if receipt:
            require(receipt.request_hash == digest, "幂等键已用于其他注册资料", 409)
            db.commit()
            return receipt.result
        valid_invitation(invite)
        major_id = invite.major_id or body.major_id
        require(major_id is not None and (body.major_id is None or body.major_id == major_id), "请选择邀请允许的专业", 422)
        require_active_organization(db, school.id, invite.college_id, major_id)
        duplicate = db.exec(select(User).where(User.school_id == school.id, or_(
            User.username == body.username, User.student_no == body.student_no))).first()
        require(duplicate is None, "账号或学号已存在，请联系管理员", 409)
        account = AccountCreate(school_id=school.id, college_id=invite.college_id, major_id=major_id,
            username=body.username, display_name=body.display_name, student_no=body.student_no,
            gender=body.gender, contact=body.contact, temporary_password=body.password,
            grants=[GrantInput(role=Role.STUDENT)])
        user = insert_account(db, account, must_change=False)
        invite.used_count += 1
        db.add(invite)
        result = {"message": "账号已开通，请使用学校、账号和本人密码登录"}
        db.add(CommandReceipt(subject=subject, work_role="public", operation="register", key=key,
                              request_hash=digest, result=result))
        db.add(CoreAuditEvent(school_id=school.id, actor_id=user.id, work_role="student",
                              operation="account.register", entity_id=user.id))
        db.commit()
        return result
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(409, "账号、学号或邀请状态已变化，未创建账号") from error
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
