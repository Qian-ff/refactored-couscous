from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import ValidationError
from sqlmodel import select

from app.domains.core.auth import CurrentIdentity, Db
from app.domains.core.business_schemas import AccountCreate, CommandKey, CsvCommit, CsvInput, CsvPreview, CsvResult, CsvTemplateView, GrantInput
from app.domains.core.class_routes import pull_member
from app.domains.core.commands import execute_command
from app.domains.core.csv_tools import csv_template, fingerprint, parse_csv
from app.domains.core.management_routes import insert_account, validate_new_account
from app.domains.core.models import College, Major, Role, User
from app.domains.core.policy import require, require_account, require_active_organization, require_class, require_grant_authority, require_student

router = APIRouter(tags=["imports"])


@router.get("/imports/template", response_model=CsvTemplateView)
def template(identity: CurrentIdentity, kind: str = Query(pattern=r"^(accounts|roster)$")):
    require(identity.work_role in {"teacher", "administrator"})
    return {"kind": kind, "csv": csv_template(kind), "encoding": "UTF-8",
            "instructions": "先预检，全部通过后确认；账号密码为8-256位临时密码且强制首改；多角色用|分隔，学生不能兼教职；不覆盖已有账号。"}


def import_scope(db, identity, body):
    if body.kind == "accounts":
        require(identity.work_role == "administrator")
        require(identity.has(Role.PLATFORM_ADMIN) or identity.user.school_id == body.school_id)
        require(body.course_id is None, "账号导入不接受教学班字段", 422)
        return None
    require(body.course_id is not None, "须选择目标教学班", 422)
    course = require_class(db, identity, body.course_id, manage=True, write=True)
    require(course.school_id == body.school_id, "目标学校与教学班不一致", 422)
    return course


def account_row(db, identity, school_id, values):
    college = db.exec(select(College).where(College.school_id == school_id, College.code == values.get("college_code"))).first()
    require(college is not None, "学院代码不存在", 422)
    major = db.exec(select(Major).where(Major.school_id == school_id, Major.college_id == college.id,
                                       Major.code == values["major_code"])).first() if values.get("major_code") else None
    if values.get("major_code"):
        require(major is not None, "专业代码不属于该学院", 422)
    roles = [Role(value.strip()) for value in values.get("role", "").split("|")]
    body = AccountCreate(school_id=school_id, college_id=college.id, major_id=major.id if major else None,
        username=values.get("username", ""), display_name=values.get("display_name", ""),
        student_no=values.get("student_no") or None, gender=values.get("gender") or None,
        contact=values.get("contact") or None, temporary_password=values.get("temporary_password", ""),
        grants=[GrantInput(role=role, college_id=college.id if role == Role.COLLEGE_ADMIN else None) for role in roles])
    require(identity.manages(college.id, school_id))
    require_active_organization(db, school_id, college.id, body.major_id)
    for grant in body.grants:
        require_grant_authority(identity, school_id, college.id, grant.role, grant.college_id)
    return body


def import_permissions(db, identity, body):
    course = import_scope(db, identity, body)
    if body.kind == "accounts":
        rows, _ = parse_csv(body.csv, body.kind)
        for row in rows:
            try:
                account_row(db, identity, body.school_id, row.values)
            except HTTPException as error:
                if error.status_code in {403, 404}:
                    raise
            except (ValidationError, ValueError):
                # Content errors are reported with row numbers by preview; never echo raw values.
                pass
    return course


def preview(db, identity, body):
    course = import_scope(db, identity, body)
    rows, errors = parse_csv(body.csv, body.kind)
    for row in rows:
        try:
            if body.kind == "accounts":
                account = account_row(db, identity, body.school_id, row.values)
                validate_new_account(db, identity, account)
            else:
                user = db.exec(select(User).where(User.school_id == course.school_id,
                                                  User.username == row.values.get("username"))).first()
                require_student(db, user, course.school_id)
        except ValidationError as error:
            for detail in error.errors(include_input=False, include_url=False, include_context=False):
                errors.append({"line": row.line, "field": ".".join(str(part) for part in detail["loc"]),
                               "message": "字段格式不正确，请按模板检查"})
        except HTTPException as error:
            errors.append({"line": row.line, "field": "row", "message": str(error.detail)})
        except ValueError:
            errors.append({"line": row.line, "field": "role", "message": "角色无效或存在学生/教职冲突"})
    digest = fingerprint({"kind": body.kind, "school_id": body.school_id, "course_id": body.course_id,
                          "csv": body.csv, "actor": identity.user.id, "work_role": identity.work_role})
    return CsvPreview(valid=not errors, row_count=len(rows), digest=digest, errors=errors), rows


@router.post("/imports/preview", response_model=CsvPreview)
def preview_import(body: CsvInput, identity: CurrentIdentity, db: Db):
    return preview(db, identity, body)[0]


@router.post("/imports/commit", response_model=CsvResult)
def commit_import(body: CsvCommit, identity: CurrentIdentity, db: Db, key: CommandKey):
    def authorize():
        import_permissions(db, identity, body)
    def action():
        checked, rows = preview(db, identity, body)
        require(checked.digest == body.preview_digest, "预检内容或工作身份已改变，请重新预检", 409)
        if not checked.valid:
            raise HTTPException(409, {"code": "IMPORT_INVALID", "message": "预检失败，整批未保存", "errors": checked.errors})
        course = import_scope(db, identity, body)
        ids: list[UUID] = []
        for row in rows:
            if body.kind == "accounts":
                account = account_row(db, identity, body.school_id, row.values)
                validate_new_account(db, identity, account)
                ids.append(insert_account(db, account).id)
            else:
                ids.append(pull_member(db, course, row.values["username"]).user_id)
        return CsvResult(count=len(ids), ids=ids)
    def replay(result):
        if body.kind == "accounts":
            for user_id in result["ids"]:
                require_account(db, identity, UUID(user_id))
    return execute_command(db, identity, body.school_id, f"imports.{body.kind}", key, body.model_dump(), action, authorize, replay)
