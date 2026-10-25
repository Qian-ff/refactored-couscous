"""Import preview ingestion and atomic confirmation; no worker, storage or HTTP ownership."""
import hmac
from datetime import datetime
from uuid import UUID

from fastapi import HTTPException
from pydantic import Field
from sqlmodel import select

from app.domains.content.access import descriptor, require_library
from app.domains.content.models import Library, now
from app.domains.content.questions.budget import ContentBudget
from app.domains.content.questions.models import ImportBatch, ImportCreatedQuestion, Question, QuestionDraft, TransferTask
from app.domains.content.questions.policy import draft_query, live_identity, staff
from app.domains.content.questions.queries import bounds
from app.domains.content.questions.schemas import DraftContent, StrictModel, canonical_bytes, fingerprint
from app.domains.content.questions.transfer_codec import Preview, PreviewRow
from app.domains.content.questions.views import Page
from app.domains.content.services import execute_command, locked, require_key
from app.domains.core.commands import check_revision, tenant_write_lock, touch
from app.domains.core.policy import resource_access

HASH_PATTERN = r"^[0-9a-f]{64}$"


class ImportConfirm(StrictModel):
    revision: int = Field(ge=1, strict=True)
    library_id: UUID
    input_hash: str = Field(pattern=HASH_PATTERN)
    preview_hash: str = Field(pattern=HASH_PATTERN)


class BatchView(StrictModel):
    id: UUID
    library_id: UUID
    state: str
    revision: int
    input_hash: str
    preview_hash: str | None
    row_count: int
    expires_at: datetime
    committed_at: datetime | None


class ImportRowView(StrictModel):
    row: int
    content: DraftContent | None
    error: str | None
    duplicate_of: int | None


class CreatedQuestion(StrictModel):
    row: int
    question_id: UUID


def require_batch(db, identity, batch_id):
    staff(identity)
    row = db.get(ImportBatch, batch_id, populate_existing=True)
    if (row is None or row.actor_id != identity.user.id or row.work_role != identity.work_role
            or row.login_session_id != identity.login.id):
        raise HTTPException(403, "导入批次不存在或不属于当前工作会话")
    library = require_library(db, identity, row.library_id, "submit")
    if not resource_access(db, identity, descriptor(library, creator_id=row.actor_id)).read:
        raise HTTPException(403, "无权读取此导入批次")
    if row.state != "committed" and row.expires_at <= now():
        raise HTTPException(410, "导入批次已过期")
    return row, library


def _task(db, batch):
    task = db.exec(select(TransferTask).where(TransferTask.batch_id == batch.id)
                   .execution_options(populate_existing=True)).first()
    library = db.get(Library, batch.library_id, populate_existing=True)
    if (task is None or library is None or task.school_id != library.school_id
            or task.kind != "import" or task.library_id != batch.library_id
            or task.owner_id != batch.actor_id or task.login_session_id != batch.login_session_id
            or task.work_role != batch.work_role or task.input_hash != batch.input_hash):
        raise HTTPException(409, "导入任务与批次不匹配")
    return task


def preview_hash(batch, task):
    return fingerprint({"batch_id": str(batch.id), "task_id": str(task.id), "library_id": str(batch.library_id),
        "input_hash": batch.input_hash, "worker_result_hash": task.result_hash, "generation": task.generation,
        "rows": batch.normalized_rows, "errors": batch.errors})


def _existing_duplicates(db, identity, library_id, contents):
    hashes = {content.payload.duplicate_hash() for content in contents}
    if not hashes:
        return set()
    rows = db.exec(draft_query(identity, "question").where(Question.library_id == library_id,
        Question.retired.is_(False), QuestionDraft.duplicate_hash.in_(hashes))).all()
    return {row.duplicate_hash for row in rows}


def ingest_preview(db, task_id, generation, execution_id, lease_owner, preview: Preview, budget=ContentBudget()):
    """Trusted runner transaction only. Caller commits/rolls back and confirms process cleanup.

    This function never accepts HTTP-uploaded previews and never releases task reservation.
    The controller must call it only after reading the actual bounded result from its fixed runner.
    """
    original = db.get(TransferTask, task_id, populate_existing=True)
    if original is None:
        raise HTTPException(409, "导入任务不存在")
    tenant_write_lock(db, original.school_id)
    task = locked(db, TransferTask, task_id)
    if (task.kind != "import" or task.state != "running" or task.generation != generation
            or task.execution_id != execution_id or task.lease_owner != lease_owner
            or task.stop_confirmed or task.lease_until is None or task.lease_until <= now()
            or task.expires_at <= now()):
        raise HTTPException(409, "导入执行已过期、停止或被替换")
    # Revalidate even a caller-supplied Pydantic instance constructed without validation.
    preview = Preview.model_validate(preview.model_dump(mode="json"))
    from app.domains.content.background_identity import load_identity
    identity = load_identity(db, task.owner_id, task.login_session_id, task.work_role)
    identity = live_identity(db, identity)
    batch, _library = require_batch(db, identity, task.batch_id)
    batch = locked(db, ImportBatch, batch.id)
    _task(db, batch)
    if batch.state != "pending" or preview.input_hash != task.input_hash:
        raise HTTPException(409, "预检输入指纹或批次状态不匹配")
    duplicates = _existing_duplicates(db, identity, batch.library_id,
        [row.content for row in preview.rows if row.content is not None])
    rows, errors = [], []
    for row in preview.rows:
        value = row.model_dump(mode="json")
        error = row.error or ("batch_duplicate" if row.duplicate_of is not None else None)
        if row.content is not None and row.content.payload.duplicate_hash() in duplicates:
            error = "existing_duplicate"
        if error:
            errors.append({"row": row.row, "code": error})
        rows.append(value)
    task.result_hash = preview.digest()
    task.result_bytes = len(canonical_bytes(preview))
    task.state, task.stage, task.finished_at = "succeeded", "previewed", now()
    batch.normalized_rows, batch.errors, batch.row_count = rows, errors, len(rows)
    batch.state = "invalid" if errors else "ready"
    batch.preview_hash = preview_hash(batch, task)
    batch.retained_bytes = len(canonical_bytes({"rows": rows, "errors": errors}))
    touch(batch)
    db.add(task)
    db.add(batch)
    budget.admit(db, task.school_id)
    return {"batch_id": str(batch.id), "revision": batch.revision, "state": batch.state}


def batch_view(db, identity, batch_id):
    batch, _library = require_batch(db, live_identity(db, identity), batch_id)
    return BatchView.model_validate({name: getattr(batch, name) for name in BatchView.model_fields})


def preview_rows(db, identity, batch_id, offset=0, limit=50):
    bounds("", "", offset, limit)
    batch, _library = require_batch(db, live_identity(db, identity), batch_id)
    errors = {error["row"]: error["code"] for error in batch.errors}
    items = []
    for raw in batch.normalized_rows[offset:offset + limit]:
        row = PreviewRow.model_validate(raw)
        items.append(ImportRowView(row=row.row, content=row.content,
                                  error=errors.get(row.row, row.error), duplicate_of=row.duplicate_of))
    return Page[ImportRowView](items=tuple(items), total=batch.row_count, offset=offset, limit=limit)


def _confirmed_contents(batch, task, request):
    check_revision(batch, request.revision)
    if (batch.state != "ready" or task.state != "succeeded" or task.expires_at <= now()
            or request.library_id != batch.library_id or request.input_hash != batch.input_hash
            or batch.errors or batch.preview_hash is None
            or not hmac.compare_digest(request.preview_hash, batch.preview_hash)
            or not hmac.compare_digest(batch.preview_hash, preview_hash(batch, task))):
        raise HTTPException(409, "确认信息、预检结果或任务状态已改变，请重新预检")
    preview = Preview.model_validate({"input_hash": batch.input_hash, "rows": batch.normalized_rows})
    if len(preview.rows) != batch.row_count or any(row.error or row.duplicate_of is not None for row in preview.rows):
        raise HTTPException(409, "存在未通过的预检行，不能创建草稿")
    return [row.content for row in preview.rows]


def confirm_import(db, identity, batch_id, request: ImportConfirm, key, budget=ContentBudget()):
    require_key(key)
    original, library = require_batch(db, identity, batch_id)

    def action():
        batch = locked(db, ImportBatch, batch_id)
        task = _task(db, batch)
        contents = _confirmed_contents(batch, task, request)
        if _existing_duplicates(db, identity, batch.library_id, contents):
            raise HTTPException(409, "题库已有相同题干和选项，请重新预检")
        parents = [Question(library_id=batch.library_id, creator_id=identity.user.id) for _ in contents]
        db.add_all(parents)
        db.flush()
        for row, parent, content in zip(batch.normalized_rows, parents, contents, strict=True):
            payload, provenance = content.payload.model_dump(mode="json"), content.provenance.model_dump(mode="json")
            db.add(QuestionDraft(question_id=parent.id, payload=payload, provenance=provenance,
                duplicate_hash=content.payload.duplicate_hash(), updated_by=identity.user.id,
                retained_bytes=len(canonical_bytes({"payload": payload, "provenance": provenance}))))
            db.add(ImportCreatedQuestion(batch_id=batch.id, row_number=row["row"], question_id=parent.id))
        batch.state, batch.committed_at = "committed", now()
        touch(batch)
        db.add(batch)
        budget.admit(db, library.school_id)
        # IDs live in the authorized paged result table, never a 1000-answer command receipt.
        return {"batch_id": str(batch.id), "revision": batch.revision, "state": "committed", "created_count": len(parents)}

    return execute_command(db, identity, library.school_id, "content.question.import.confirm", key,
        {"batch_id": str(original.id), **request.model_dump(mode="json")}, action,
        lambda: require_batch(db, identity, batch_id))


def created_questions(db, identity, batch_id, offset=0, limit=50):
    bounds("", "", offset, limit)
    batch, _library = require_batch(db, live_identity(db, identity), batch_id)
    if batch.state != "committed":
        raise HTTPException(409, "批次尚未确认生成草稿")
    # The result mapping never restores a draft read grant after role/course revocation.
    query = select(ImportCreatedQuestion).join(Question, Question.id == ImportCreatedQuestion.question_id).where(
        ImportCreatedQuestion.batch_id == batch.id,
        Question.id.in_(draft_query(identity, "question").with_only_columns(QuestionDraft.question_id)))
    from sqlalchemy import func
    total = db.exec(select(func.count()).select_from(query.subquery())).one()
    rows = db.exec(query.order_by(ImportCreatedQuestion.row_number).offset(offset).limit(limit)).all()
    return {"items": [{"row": row.row_number, "question_id": str(row.question_id)} for row in rows],
            "total": total, "offset": offset, "limit": limit}
