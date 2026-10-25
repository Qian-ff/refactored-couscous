"""Persisted C1 task commands; A supplies the one shared queue, storage and runner."""
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
import hashlib
import re
from typing import Literal
from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import Field, field_validator, model_validator
from sqlmodel import select

from app.domains.content.access import require_library
from app.domains.content.models import Library, now
from app.domains.content.questions.budget import ContentBudget
from app.domains.content.questions.imports import require_batch
from app.domains.content.questions.models import ExportVersion, ImportBatch, TransferTask
from app.domains.content.questions.policy import has_retained_public_grant, live_identity, public_source_ids, require_version, staff
from app.domains.content.questions.schemas import DraftContent, StrictModel, canonical_bytes, clean_text
from app.domains.content.questions.services import check_lineage, checked_version
from app.domains.content.questions.sources import check_publication
from app.domains.content.questions.transfer_cli import ExportInput
from app.domains.content.questions.transfer_codec import INPUT_LIMITS, OUTPUT_LIMIT, VERSION
from app.domains.content.quota import quota_lock
from app.domains.content.services import execute_command, locked, require_key

HASH_PATTERN = r"^[0-9a-f]{64}$"
RESERVATION = 33554432
MIMES = {"csv": "text/csv; charset=utf-8", "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}


@dataclass(frozen=True)
class TransferAdmission:
    # A checks all C02/C1 queue entries and upload receiving slots under the same global lock.
    check: Callable | None = None

    def admit(self, db, owner_id, *, receiving):
        if self.check is None:
            raise HTTPException(503, "CONTENT_TRANSFER_QUEUE_UNAVAILABLE：统一任务控制尚未接入")
        quota_lock(db)
        self.check(db, owner_id, receiving=receiving)


class ImportCreate(StrictModel):
    library_id: UUID
    format: Literal["csv", "xlsx"]
    expected_bytes: int = Field(gt=0, strict=True)
    input_hash: str = Field(pattern=HASH_PATTERN)

    @model_validator(mode="after")
    def size(self):
        if self.expected_bytes > INPUT_LIMITS[self.format]:
            raise ValueError("题目导入超过对应格式上限")
        return self


class ExportCreate(StrictModel):
    library_id: UUID
    format: Literal["csv", "xlsx"]
    version_ids: tuple[UUID, ...] = Field(min_length=1, max_length=1000)
    authorization_statement: str = Field(min_length=1, max_length=2000)

    _statement = field_validator("authorization_statement")(clean_text)

    @field_validator("version_ids")
    @classmethod
    def unique_versions(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("导出固定版本不能重复")
        return value


class TaskGeneration(StrictModel):
    generation: int = Field(ge=1, strict=True)


def require_task(db, identity, task_id, *, allow_expired=False):
    staff(identity)
    task = db.get(TransferTask, task_id, populate_existing=True)
    if (task is None or task.owner_id != identity.user.id or task.work_role != identity.work_role
            or task.login_session_id != identity.login.id):
        raise HTTPException(403, "任务不存在或不属于当前工作会话")
    if not allow_expired and task.expires_at <= now():
        raise HTTPException(410, "任务已过期")
    library = db.get(Library, task.library_id, populate_existing=True)
    if library is None or not library.active or task.school_id != library.school_id:
        raise HTTPException(403, "任务目标范围不可用")
    if task.kind == "import":
        require_batch(db, identity, task.batch_id)
    elif task.kind == "export":
        rows = db.exec(select(ExportVersion).where(ExportVersion.task_id == task.id).order_by(ExportVersion.ordinal)).all()
        if not 1 <= len(rows) <= 1000 or [row.ordinal for row in rows] != list(range(len(rows))):
            raise HTTPException(409, "导出固定版本清单无效")
        for row in rows:
            _version, parent, _projection = require_version(db, identity, "question", row.version_id, task.library_id)
            if parent.retired:
                raise HTTPException(403, "导出来源已停用")
    else:
        raise HTTPException(409, "未知题目任务类型")
    return task


def create_import(db, identity, request: ImportCreate, key, budget=ContentBudget(), admission=TransferAdmission()):
    staff(identity)
    require_key(key)
    library = require_library(db, identity, request.library_id, "submit")

    def action():
        admission.admit(db, identity.user.id, receiving=True)
        current = require_library(db, identity, request.library_id, "submit")
        expires = now() + timedelta(minutes=15)
        batch = ImportBatch(library_id=current.id, actor_id=identity.user.id, login_session_id=identity.login.id,
            work_role=identity.work_role, input_hash=request.input_hash, expires_at=expires)
        db.add(batch)
        db.flush()
        task_id = uuid4()
        task = TransferTask(id=task_id, batch_id=batch.id, kind="import", format=request.format, library_id=current.id,
            school_id=current.school_id, owner_id=identity.user.id, login_session_id=identity.login.id,
            work_role=identity.work_role, input_hash=request.input_hash, expected_bytes=request.expected_bytes,
            file_key=task_id.hex + ".blob", expires_at=expires, reserved_bytes=RESERVATION)
        db.add(task)
        budget.admit(db, current.school_id)
        return {"task_id": str(task.id), "batch_id": str(batch.id), "state": task.state, "generation": task.generation}

    return execute_command(db, identity, library.school_id, "content.question.import.create", key,
        request.model_dump(mode="json"), action,
        lambda: require_library(db, identity, request.library_id, "submit"),
        lambda result: require_task(db, identity, UUID(result["task_id"])))


def _export_content(db, identity, library_id, version_ids, statement):
    contents = []
    size = 0
    for version_id in version_ids:
        version, parent, projection = require_version(db, identity, "question", version_id, library_id)
        if parent.retired:
            raise HTTPException(409, "题目已停用，不能用于新导出")
        payload, sources = checked_version(db, version)
        source = db.get(Library, parent.library_id, populate_existing=True)
        check_publication(version.provenance, source, projection, statement, sources, reusing=True,
            public_origin=has_retained_public_grant(db, "question", version.id),
            public_source_ids=public_source_ids(db, "question", version.copied_from_version_id))
        check_lineage(db, version.copied_from_version_id, projection, statement)
        item = DraftContent(payload=payload, provenance=version.provenance)
        size += len(canonical_bytes(item)) + 1
        if size > OUTPUT_LIMIT - 1024:
            raise HTTPException(413, "导出输入快照超过16MiB，请分批导出")
        contents.append(item)
    return canonical_bytes(ExportInput(protocol=VERSION, questions=tuple(contents)))


def create_export(db, identity, request: ExportCreate, key, budget=ContentBudget(), admission=TransferAdmission()):
    staff(identity)
    require_key(key)
    current = live_identity(db, identity)
    # Preflight read authority; the transaction rechecks it after refreshing the real login.
    for version_id in request.version_ids:
        require_version(db, current, "question", version_id, request.library_id)
    library = db.get(Library, request.library_id, populate_existing=True)

    def authorize():
        for version_id in request.version_ids:
            require_version(db, identity, "question", version_id, request.library_id)

    def action():
        admission.admit(db, identity.user.id, receiving=False)
        data = _export_content(db, identity, request.library_id, request.version_ids, request.authorization_statement)
        task_id = uuid4()
        task = TransferTask(id=task_id, kind="export", format=request.format, library_id=library.id,
            school_id=library.school_id, owner_id=identity.user.id, login_session_id=identity.login.id,
            work_role=identity.work_role, input_hash=hashlib.sha256(data).hexdigest(), expected_bytes=len(data),
            file_key=task_id.hex + ".blob", state="queued", stage="queued", reserved_bytes=RESERVATION,
            expires_at=now() + timedelta(hours=24))
        db.add(task)
        db.flush()
        for ordinal, version_id in enumerate(request.version_ids):
            db.add(ExportVersion(task_id=task.id, version_id=version_id, ordinal=ordinal))
        budget.admit(db, library.school_id)
        return {"task_id": str(task.id), "state": "queued", "generation": task.generation}

    return execute_command(db, identity, library.school_id, "content.question.export.create", key,
        request.model_dump(mode="json"), action, authorize,
        lambda result: require_task(db, identity, UUID(result["task_id"])))


def export_worker_input(db, identity, task_id):
    """Trusted controller only; this returns private answers, never a public task-status DTO."""
    identity = live_identity(db, identity)
    task = require_task(db, identity, task_id)
    if task.kind != "export" or task.state not in {"queued", "running"}:
        raise HTTPException(409, "导出任务未处于可执行状态")
    rows = db.exec(select(ExportVersion).where(ExportVersion.task_id == task.id).order_by(ExportVersion.ordinal)).all()
    data = _export_content(db, identity, task.library_id, [row.version_id for row in rows], "既有授权导出任务执行时复核")
    if len(data) != task.expected_bytes or hashlib.sha256(data).hexdigest() != task.input_hash:
        raise HTTPException(409, "导出固定内容指纹发生变化")
    return data


def cancel_transfer(db, identity, task_id, request: TaskGeneration, key):
    require_key(key)
    task = require_task(db, identity, task_id)

    def action():
        quota_lock(db)
        row = locked(db, TransferTask, task_id)
        if row.generation != request.generation:
            raise HTTPException(409, "任务代次已改变，请刷新")
        batch = locked(db, ImportBatch, row.batch_id) if row.batch_id is not None else None
        if batch is not None and batch.state == "committed":
            raise HTTPException(409, "批次已生成草稿，不能取消历史确认")
        if row.state in {"created", "receiving", "queued", "running"} or (row.state == "succeeded" and batch is not None):
            row.state, row.stage, row.finished_at = "canceled", "stopping", now()
            row.generation += 1
            db.add(row)
            if batch is not None:
                batch.state, batch.revision = "canceled", batch.revision + 1
                db.add(batch)
        # Even queued tasks may retain a sealed upload. Release only after confirmed cleanup.
        return {"task_id": str(row.id), "state": row.state, "generation": row.generation}

    return execute_command(db, identity, task.school_id, "content.question.transfer.cancel", key,
        {"task_id": str(task_id), **request.model_dump()}, action,
        lambda: require_task(db, identity, task_id))


def export_download(db, identity, task_id):
    """Private storage ticket. Stream code must reauthorize with a fresh session between chunks."""
    task = require_task(db, live_identity(db, identity), task_id)
    if (task.kind != "export" or task.state != "succeeded" or task.result_hash is None
            or not re.fullmatch(HASH_PATTERN, task.result_hash) or not 0 < task.result_bytes <= INPUT_LIMITS[task.format]):
        raise HTTPException(409, "导出文件尚未可用")
    return {"file_key": task.file_key, "expected_hash": task.result_hash, "expected_bytes": task.result_bytes,
            "mime": MIMES[task.format], "filename": "labconnect-questions." + task.format}


def check_retryable(task, generation):
    if (task.generation != generation or task.state not in {"failed", "canceled"}
            or not task.stop_confirmed or task.reserved_bytes != 0
            or (task.kind == "import" and not task.input_sealed)):
        raise HTTPException(409, "旧执行/清理尚未确认或原件不可用，不能重试")


def retry_transfer(db, identity, task_id, request: TaskGeneration, key, budget=ContentBudget(), admission=TransferAdmission()):
    require_key(key)
    original = require_task(db, identity, task_id)

    def action():
        admission.admit(db, identity.user.id, receiving=False)
        task = locked(db, TransferTask, task_id)
        check_retryable(task, request.generation)
        if task.kind == "export":
            rows = db.exec(select(ExportVersion).where(ExportVersion.task_id == task.id).order_by(ExportVersion.ordinal)).all()
            _export_content(db, identity, task.library_id, [row.version_id for row in rows], "重试既有授权导出")
        if task.batch_id is not None:
            batch = locked(db, ImportBatch, task.batch_id)
            if batch.state == "committed":
                raise HTTPException(409, "不能重试已生成草稿的批次")
            batch.state, batch.preview_hash, batch.row_count = "pending", None, 0
            batch.normalized_rows, batch.errors, batch.retained_bytes = [], [], 0
            batch.revision += 1
            db.add(batch)
        task.generation += 1
        task.state, task.stage, task.error_code = "queued", "queued", None
        task.execution_id, task.lease_owner, task.lease_until = None, None, None
        task.stop_confirmed, task.finished_at, task.reserved_bytes = False, None, RESERVATION
        task.result_hash, task.result_bytes = None, 0
        db.add(task)
        budget.admit(db, task.school_id)
        return {"task_id": str(task.id), "state": "queued", "generation": task.generation}

    return execute_command(db, identity, original.school_id, "content.question.transfer.retry", key,
        {"task_id": str(task_id), **request.model_dump()}, action,
        lambda: require_task(db, identity, task_id))


def task_view(db, identity, task_id):
    task = require_task(db, live_identity(db, identity), task_id)
    return {"task_id": str(task.id), "batch_id": str(task.batch_id) if task.batch_id else None,
        "kind": task.kind, "format": task.format, "state": task.state, "stage": task.stage,
        "generation": task.generation, "error_code": task.error_code, "expires_at": task.expires_at,
        "result_bytes": task.result_bytes if task.state == "succeeded" else 0}
