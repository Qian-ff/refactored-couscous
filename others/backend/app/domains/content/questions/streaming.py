"""Private file I/O with short fresh DB sessions and the existing kernel upload fence."""
import errno
import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from time import monotonic
from uuid import uuid4

from fastapi import HTTPException
from starlette.background import BackgroundTask
from starlette.responses import StreamingResponse

from app.domains.content.background_identity import load_identity
from app.domains.content.downloads import verified_file
from app.domains.content.models import now
from app.domains.content.questions.budget import ContentBudget
from app.domains.content.questions.models import ImportBatch, TransferTask
from app.domains.content.questions.transfers import TransferAdmission, export_download, require_task
from app.domains.content.quota import quota_lock, receiving_slots
from app.domains.content.services import execute_command, locked
from app.domains.content.storage import PrivateStorage
from app.domains.content.upload_fence import FenceUnavailable
from app.domains.content.uploads import _io, _next_chunk
from app.domains.core.commands import tenant_write_lock


@dataclass(frozen=True)
class TransferIO:
    factory: Callable
    storage: PrivateStorage
    budget_for: Callable[[int], ContentBudget]
    admission: TransferAdmission


def receiving_count(db):
    """A must also use this combined count in the C02 receiving-slot check under quota_lock."""
    # Cancellation/expiry is not proof that the receiver or its cleanup has closed.
    # Sealed imports may hold parser leases, which are not upload-slot occupancy.
    return receiving_slots(db)


def _check(factory, context, task_id):
    with factory() as db:
        task = require_task(db, load_identity(db, *context), task_id)
        if task.kind != "import":
            raise HTTPException(409, "此任务不接收文件")
        if task.input_sealed:
            raise HTTPException(409, "文件已封存，请查询任务状态")


def _claim(runtime, context, task_id, writer, guard):
    guard.require(runtime.storage.root, task_id)
    with runtime.factory() as db:
        identity = load_identity(db, *context)
        original = require_task(db, identity, task_id)

        def action():
            quota_lock(db)
            row = locked(db, TransferTask, task_id)
            if row.kind != "import" or row.file_key != task_id.hex + ".blob":
                raise HTTPException(409, "导入文件归属不符")
            if row.state != "created" or row.input_sealed or row.execution_id is not None:
                raise HTTPException(409, "上传状态已改变，请查询任务或重新创建")
            if receiving_count(db) >= 2:
                raise HTTPException(409, "接收通道繁忙，请稍后重试")
            row.state, row.stage = "receiving", "receiving"
            row.lease_owner, row.lease_until = writer, now() + timedelta(seconds=20)
            db.add(row)
            return {"generation": row.generation, "expected_bytes": row.expected_bytes,
                    "input_hash": row.input_hash, "format": row.format, "file_key": row.file_key}

        return execute_command(db, identity, original.school_id, "content.question.import.receive", None,
            {"task_id": str(task_id)}, action, lambda: require_task(db, identity, task_id))


def _heartbeat(runtime, context, task_id, writer, generation, guard):
    guard.require(runtime.storage.root, task_id)
    with runtime.factory() as db:
        task = require_task(db, load_identity(db, *context), task_id)
        if task.generation != generation:
            raise HTTPException(409, "上传代次已改变")
        if (task.state != "receiving" or task.lease_owner != writer or task.lease_until is None
                or task.lease_until <= now() or task.input_sealed):
            raise HTTPException(409, "上传已停止或失去租约")
        task.lease_until = now() + timedelta(seconds=20)
        db.add(task)
        db.commit()


def _finish(runtime, context, task_id, writer, generation, free, guard):
    guard.require(runtime.storage.root, task_id)
    with runtime.factory() as db:
        identity = load_identity(db, *context)
        original = require_task(db, identity, task_id)

        def action():
            runtime.admission.admit(db, identity.user.id, receiving=False)
            task = locked(db, TransferTask, task_id)
            if (task.state != "receiving" or task.generation != generation or task.lease_owner != writer
                    or task.lease_until is None or task.lease_until <= now() or task.input_sealed):
                raise HTTPException(409, "上传已失效，不能封存")
            task.input_sealed, task.retained_bytes = True, task.expected_bytes
            task.state, task.stage = "queued", "queued"
            task.lease_owner, task.lease_until = None, None
            db.add(task)
            runtime.budget_for(free).admit(db, task.school_id)
            return {"task_id": str(task.id), "batch_id": str(task.batch_id), "state": "queued", "generation": task.generation}

        return execute_command(db, identity, original.school_id, "content.question.import.seal", "seal-" + task_id.hex,
            {"task_id": str(task_id), "generation": generation}, action, lambda: require_task(db, identity, task_id))


def cleanup_upload(runtime, task_id, guard, expected_writer=None):
    """Only cleans unstarted uploads. Runner executions require A's real stop receipt first."""
    storage = runtime.storage
    guard.require(storage.root, task_id)
    cleaner = uuid4()
    with runtime.factory() as db:
        original = db.get(TransferTask, task_id, populate_existing=True)
        if original is None:
            return False
        tenant_write_lock(db, original.school_id)
        quota_lock(db)
        task = locked(db, TransferTask, task_id)
        if task.kind != "import" or task.file_key != task_id.hex + ".blob":
            raise HTTPException(409, "上传清理对象不符")
        if expected_writer is not None and task.lease_owner != expected_writer:
            return False
        if task.execution_id is not None or task.state in {"queued", "running", "succeeded"}:
            return False
        if task.state == "created" and task.expires_at > now():
            return False
        if task.state not in {"created", "receiving", "failed", "canceled", "expired"}:
            return False
        if task.state in {"created", "receiving"}:
            task.state = "expired" if task.expires_at <= now() else "failed"
            task.error_code = "UPLOAD_INTERRUPTED"
        keep_original = task.input_sealed
        task.generation += 1
        task.lease_owner, task.lease_until, task.stage = cleaner, now() + timedelta(seconds=20), "cleanup"
        db.add(task)
        key, generation, school_id = task.file_key, task.generation, task.school_id
        if task.batch_id is not None:
            batch = locked(db, ImportBatch, task.batch_id)
            if batch.state == "committed":
                raise HTTPException(409, "不能清理已确认批次的原件")
            batch.state, batch.revision = task.state, batch.revision + 1
            db.add(batch)
        db.commit()
    storage.remove_unreferenced(task_id.hex + ".part", guard)
    if not keep_original:
        storage.remove_unreferenced(key, guard)
    with runtime.factory() as db:
        tenant_write_lock(db, school_id)
        quota_lock(db)
        task = locked(db, TransferTask, task_id)
        if task.generation != generation or task.lease_owner != cleaner or task.execution_id is not None:
            raise HTTPException(409, "清理代次发生改变，保留预留空间")
        task.reserved_bytes, task.stop_confirmed = 0, True
        task.retained_bytes = task.expected_bytes if keep_original else 0
        task.lease_owner, task.lease_until, task.stage = None, None, "stopped"
        db.add(task)
        db.commit()
    return True


def reap_upload(runtime, task_id):
    attempt = runtime.storage.fence.try_acquire(task_id)
    if attempt.status != "acquired":
        return False
    with attempt.guard as guard:
        return cleanup_upload(runtime, task_id, guard)


async def receive(runtime, context, task_id, source):
    """No DB connection or transaction spans network reads/writes; context comes from identity."""
    writer, guard, stream = uuid4(), None, None
    try:
        await _io(_check, runtime.factory, context, task_id)
        attempt = await _io(runtime.storage.fence.try_acquire, task_id,
            dispose_on_cancel=lambda value: value.guard.close() if value.guard else None)
        if attempt.status != "acquired":
            raise HTTPException(409 if attempt.status == "busy" else 503, "UPLOAD_BUSY_OR_UNAVAILABLE")
        guard = attempt.guard
        snapshot = await _io(_claim, runtime, context, task_id, writer, guard)
        generation = snapshot["generation"]
        stream = await _io(runtime.storage.create, task_id.hex + ".part", guard, dispose_on_cancel=lambda file: file.close())
        digest, count, signature = hashlib.sha256(), 0, b""
        start = checkpoint = monotonic()
        iterator = aiter(source)

        async def heartbeat():
            await _io(_heartbeat, runtime, context, task_id, writer, generation, guard)

        while True:
            try:
                piece = await _next_chunk(iterator, start + 300, heartbeat)
            except StopAsyncIteration:
                break
            if monotonic() - checkpoint >= 5:
                await heartbeat()
                checkpoint = monotonic()
            count += len(piece)
            if count > snapshot["expected_bytes"]:
                raise HTTPException(413, "上传字节超过声明长度")
            signature = (signature + piece[:4])[:4]
            digest.update(piece)
            if stream is not None:
                await _io(stream.write, piece)
        if count != snapshot["expected_bytes"] or digest.hexdigest() != snapshot["input_hash"]:
            raise HTTPException(409, "上传长度或SHA256不匹配")
        if snapshot["format"] == "xlsx" and not signature.startswith(b"PK\x03\x04"):
            raise HTTPException(415, "文件格式与声明不符")
        await heartbeat()
        await _io(runtime.storage.flush, stream, guard)
        await _io(stream.close)
        stream = None
        await _io(runtime.storage.seal, task_id.hex + ".part", snapshot["file_key"], guard)
        free = await _io(runtime.storage.free_bytes)
        return await _io(_finish, runtime, context, task_id, writer, generation, free, guard)
    except FenceUnavailable:
        raise HTTPException(503, "UPLOAD_FENCE_UNAVAILABLE") from None
    except OSError as error:
        raise HTTPException(507 if error.errno == errno.ENOSPC else 503, "STORAGE_UNAVAILABLE") from None
    finally:
        try:
            if stream is not None:
                await _io(stream.close)
        finally:
            if guard is not None:
                try:
                    await _io(cleanup_upload, runtime, task_id, guard, writer)
                except (OSError, FenceUnavailable):
                    raise HTTPException(503, "STORAGE_CLEANUP_FAILED：预留空间保持占用") from None
                finally:
                    await _io(guard.close)


def _download_ticket(factory, context, task_id):
    with factory() as db:
        return export_download(db, load_identity(db, *context), task_id)


async def download(runtime, context, task_id):
    ticket = await _io(_download_ticket, runtime.factory, context, task_id)
    specification = {"key": ticket["file_key"], "bytes": ticket["expected_bytes"], "hash": ticket["expected_hash"]}
    try:
        stream = await _io(verified_file, runtime.storage, specification, dispose_on_cancel=lambda file: file.close())
    except OSError:
        raise HTTPException(503, "STORAGE_UNAVAILABLE") from None

    async def body():
        digest, count = hashlib.sha256(), 0
        try:
            while count < ticket["expected_bytes"]:
                current = await _io(_download_ticket, runtime.factory, context, task_id)
                if current != ticket:
                    return
                data = await _io(stream.read, min(262144, ticket["expected_bytes"] - count))
                if not data:
                    return
                digest.update(data)
                count += len(data)
                if count == ticket["expected_bytes"] and digest.hexdigest() != ticket["expected_hash"]:
                    return
                yield data
        except (HTTPException, OSError):
            # A revoked/truncated transfer must not return an error JSON file with status 200.
            return
        finally:
            await _io(stream.close)

    return StreamingResponse(body(), media_type=ticket["mime"], headers={"Content-Length": str(ticket["expected_bytes"]),
        "Content-Disposition": 'attachment; filename="' + ticket["filename"] + '"',
        "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"}, background=BackgroundTask(stream.close))
