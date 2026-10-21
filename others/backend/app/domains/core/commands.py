"""Transaction boundary for B1 writes. Receipts never contain passwords or invitation codes."""
import hashlib
import hmac
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlmodel import Session, select

from app.core.config import settings
from app.domains.core.auth import Identity, available_work_roles
from app.domains.core.csv_tools import fingerprint
from app.domains.core.models import CommandReceipt, CoreAuditEvent, LoginSession, RoleGrant, School, User


def tenant_write_lock(db: Session, school_id: UUID | None):
    key = int.from_bytes(hashlib.sha256(f"labconnect:b1:{school_id}".encode()).digest()[:8], "big", signed=True)
    db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})


def refresh_identity(db: Session, identity: Identity):
    user = db.exec(select(User).where(User.id == identity.user.id).with_for_update()).one()
    db.refresh(user)
    db.refresh(identity.login)
    if not user.is_active or identity.login.revoked or identity.login.expires_at.replace(tzinfo=UTC) <= datetime.now(UTC):
        raise HTTPException(401, "登录已失效，请重新登录")
    school = db.get(School, user.school_id) if user.school_id else None
    if school is not None:
        db.refresh(school)
        if not school.is_active:
            raise HTTPException(401, "学校已停用，请联系平台管理员")
    identity.user = user
    identity.all_grants = list(db.exec(select(RoleGrant).where(RoleGrant.user_id == user.id)).all())
    if identity.work_role not in available_work_roles(identity.all_grants):
        raise HTTPException(403, "当前工作身份已撤销")
    if user.must_change_password:
        raise HTTPException(403, "请先修改临时密码")


def execute_command(db: Session, identity: Identity, school_id: UUID | None, operation: str,
                    key: str | None, payload: object, action: Callable[[], object],
                    authorize: Callable[[], None] | None = None) -> dict:
    try:
        tenant_write_lock(db, school_id)
        refresh_identity(db, identity)
        if authorize:
            authorize()  # Also runs on replay: a receipt never restores revoked access.
        subject, work_role = str(identity.user.id), identity.work_role
        receipt = db.exec(select(CommandReceipt).where(
            CommandReceipt.subject == subject, CommandReceipt.work_role == work_role,
            CommandReceipt.operation == operation, CommandReceipt.key == key,
        )).first() if key else None
        digest = fingerprint(payload)
        if receipt:
            if not hmac.compare_digest(receipt.request_hash, digest):
                raise HTTPException(409, "同一幂等键的请求内容不同，请核对后使用新键")
            result = receipt.result
        else:
            result = jsonable_encoder(action())
            if key:
                db.add(CommandReceipt(subject=subject, work_role=work_role, operation=operation,
                                      key=key, request_hash=digest, result=result))
            db.add(CoreAuditEvent(school_id=school_id, actor_id=identity.user.id, work_role=work_role,
                                 operation=operation, details={"result": "succeeded"}))
        db.commit()
        return result
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(409, "数据重复或关联发生冲突，整笔操作未保存，请刷新后重试") from error
    except OperationalError as error:
        db.rollback()
        # Do not echo SQL, connection strings, or parameters.
        code = getattr(error.orig, "sqlstate", None)
        if code in {"40001", "40P01", "55P03"}:
            raise HTTPException(409, "并发操作发生冲突，请刷新后重试") from error
        raise
    except Exception:
        db.rollback()
        raise


def check_revision(record, revision: int):
    if record.revision != revision:
        raise HTTPException(409, "数据已被其他人修改，请刷新核对")


def touch(record):
    record.revision += 1


def revoke_sessions(db: Session, user_id: UUID):
    for login in db.exec(select(LoginSession).where(LoginSession.user_id == user_id,
                                                  LoginSession.revoked.is_(False))).all():
        login.revoked = True
        db.add(login)


def code_hash(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def issued_code(scope: str, key: str) -> str:
    """Deterministic for authorized retries; only its hash is persisted."""
    return hmac.new(settings.SECRET_KEY.encode(), f"b1-invite:{scope}:{key}".encode(), hashlib.sha256).hexdigest()
