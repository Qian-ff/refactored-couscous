"""Two-stage private uploads; sessions/locks are closed before awaiting network or file I/O."""
import asyncio
import errno
import hashlib
import json
from datetime import timedelta
from time import monotonic
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import func
from sqlmodel import select

from app.domains.core.commands import tenant_write_lock
from app.domains.content.access import require_library, require_version
from app.domains.content.background_identity import load_identity
from app.domains.content.models import ContentJob, ContentUpload, Material, MaterialVersion
from app.domains.content.quota import enforce_budget, enforce_queue, quota_lock
from app.domains.content.schemas import UploadCreate
from app.domains.content.services import editable_material, execute_command, locked, require_key
from app.domains.content.upload_fence import FenceUnavailable

MIMES = {"pdf": "application/pdf", "txt": "text/plain", "docx":
         "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "pptx":
         "application/vnd.openxmlformats-officedocument.presentationml.presentation"}


def db_now(db):
    return db.exec(select(func.now())).one()


def upload_access(db, identity, upload_id):
    row = db.get(ContentUpload, upload_id)
    if row is None or row.owner_id != identity.user.id or row.work_role != identity.work_role:
        raise HTTPException(403, "无权访问上传记录")
    require_library(db, identity, row.library_id, "submit")
    if row.material_id:
        editable_material(db, identity, row.material_id, row.library_id)
    return row


def create_upload(db, identity, request: UploadCreate, key, free_disk_bytes):
    require_key(key)
    library = require_library(db, identity, request.library_id, "submit")

    def authorize():
        require_library(db, identity, request.library_id, "submit")
        if request.material_id:
            material = editable_material(db, identity, request.material_id, request.library_id)
            if material.title != request.title:
                raise HTTPException(409, "资料标题已改变，请刷新")

    def action():
        quota_lock(db)
        active = db.exec(select(ContentUpload.id).where(ContentUpload.owner_id == identity.user.id,
                                                       ContentUpload.state.in_(["created", "receiving"]))).first()
        if active:
            raise HTTPException(409, "已有活跃上传，请查询状态或取消后重试")
        upload_id = uuid4()
        metadata = request.source_metadata.model_dump()
        row = ContentUpload(id=upload_id, library_id=library.id, material_id=request.material_id,
                            owner_id=identity.user.id, login_session_id=identity.login.id, work_role=identity.work_role,
                            school_id=library.school_id, original_name=request.original_name, title=request.title,
                            source_metadata=metadata, format=request.format, encoding=request.encoding,
                            mime=MIMES[request.format], expected_bytes=request.expected_bytes,
                            expected_hash=request.expected_hash, file_key=upload_id.hex + ".blob",
                            expires_at=db_now(db) + timedelta(minutes=15), reserved_bytes=request.expected_bytes,
                            retained_bytes=len(json.dumps(metadata, ensure_ascii=False).encode("utf-8")))
        db.add(row)
        enforce_budget(db, library.school_id, free_disk_bytes)
        return {"upload_id": str(row.id)}

    return execute_command(db, identity, library.school_id, "content.upload.create", key,
                           request.model_dump(mode="json"), action, authorize,
                           lambda result: upload_access(db, identity, UUID(result["upload_id"])))


def upload_status(db, identity, upload_id):
    row = upload_access(db, identity, upload_id)
    result = {"upload_id": str(row.id), "state": row.state, "expected_bytes": row.expected_bytes,
              "expires_at": row.expires_at, "error_code": row.error_code}
    if row.sealed_version_id:
        version, material, _projection = require_version(db, identity, row.sealed_version_id)
        result.update(version_id=str(version.id), material_id=str(material.id))
    return result


def cancel_upload(db, identity, upload_id, key):
    require_key(key)
    original = upload_access(db, identity, upload_id)

    def action():
        row = locked(db, ContentUpload, upload_id)
        if row.state in {"created", "receiving"}:
            row.state = "canceled"
            row.generation += 1
            db.add(row)
        # The writer/cleanup must confirm file removal before returning reserved space.
        return {"upload_id": str(row.id)}

    return execute_command(db, identity, original.school_id, "content.upload.cancel", key,
                           {"id": str(upload_id)}, action, lambda: upload_access(db, identity, upload_id))


def _check_upload(factory, context, upload_id):
    with factory() as db:
        identity = load_identity(db, *context)
        upload_access(db, identity, upload_id)


def _claim(factory, context, upload_id, writer_id, guard):
    guard.require(guard.root, upload_id)
    with factory() as db:
        identity = load_identity(db, *context)
        row = upload_access(db, identity, upload_id)
        school_id = row.school_id

        def action():
            quota_lock(db)
            current = locked(db, ContentUpload, upload_id)
            replay = current.state == "sealed"
            if not replay and (current.state != "created" or current.login_session_id != identity.login.id
                               or current.expires_at <= db_now(db)):
                raise HTTPException(409, "上传会话不能开始，请查询状态后重新上传")
            streams = db.exec(select(func.count()).select_from(ContentUpload).where(
                ContentUpload.lease_owner.is_not(None), ContentUpload.id != upload_id)).one()
            if streams >= 2:
                raise HTTPException(409, "上传通道繁忙，请稍后重试")
            if not replay:
                current.state = "receiving"
            current.lease_owner = writer_id
            current.lease_until = db_now(db) + timedelta(seconds=20)
            db.add(current)
            return {**current.model_dump(), "replay": replay}

        return execute_command(db, identity, school_id, "content.upload.receive", None, {"id": str(upload_id)},
                               action, lambda: upload_access(db, identity, upload_id))


def _heartbeat(factory, context, upload_id, writer_id, generation, replay=False, guard=None):
    if guard is None:
        raise FenceUnavailable()
    guard.require(guard.root, upload_id)
    with factory() as db:
        identity = load_identity(db, *context)
        row = upload_access(db, identity, upload_id)
        if (row.state != ("sealed" if replay else "receiving") or row.generation != generation
                or row.lease_owner != writer_id or (not replay and row.expires_at <= db_now(db))
                or row.lease_until is None or row.lease_until <= db_now(db)):
            raise HTTPException(409, "上传已取消、过期或失去租约")
        row.lease_until = db_now(db) + timedelta(seconds=20)
        db.add(row)
        db.commit()


def _finish(factory, context, upload_id, writer_id, generation, free_disk_bytes, guard):
    guard.require(guard.root, upload_id)
    with factory() as db:
        identity = load_identity(db, *context)
        initial = upload_access(db, identity, upload_id)

        def action():
            quota_lock(db)
            row = locked(db, ContentUpload, upload_id)
            if (row.state != "receiving" or row.generation != generation or row.lease_owner != writer_id
                    or row.expires_at <= db_now(db) or row.lease_until is None or row.lease_until <= db_now(db)):
                raise HTTPException(409, "上传已失效，不能封存")
            enforce_queue(db, identity.user.id)
            if row.material_id:
                material = editable_material(db, identity, row.material_id, row.library_id)
            else:
                material = Material(library_id=row.library_id, creator_id=identity.user.id, title=row.title)
                db.add(material)
                db.flush()
            latest = db.exec(select(func.coalesce(func.max(MaterialVersion.version_no), 0)).where(
                MaterialVersion.material_id == material.id)).one()
            version = MaterialVersion(material_id=material.id, version_no=int(latest) + 1, input_kind="file",
                                      upload_id=row.id, content_hash=row.expected_hash, source_metadata=row.source_metadata,
                                      created_by=identity.user.id,
                                      retained_bytes=len(json.dumps(row.source_metadata, ensure_ascii=False).encode("utf-8")))
            db.add(version)
            db.flush()
            row.sealed_version_id = version.id
            row.material_id = material.id
            row.state = "sealed"
            row.retained_bytes += row.expected_bytes
            row.reserved_bytes = 0
            row.lease_owner = None
            row.lease_until = None
            db.add(row)
            job = ContentJob(owner_id=identity.user.id, login_session_id=identity.login.id, work_role=identity.work_role,
                             school_id=row.school_id, library_id=row.library_id, version_id=version.id)
            db.add(job)
            enforce_budget(db, row.school_id, free_disk_bytes)
            return {"upload_id": str(row.id), "version_id": str(version.id), "material_id": str(material.id)}

        return execute_command(db, identity, initial.school_id, "content.upload.seal", "seal-" + upload_id.hex,
                               {"upload_id": str(upload_id), "generation": generation}, action,
                               lambda: upload_access(db, identity, upload_id))


def _cleanup_held(factory, storage, upload_id, guard, expected_writer=None):
    guard.require(storage.root, upload_id)
    cleaner = uuid4()
    with factory() as db:
        original = db.get(ContentUpload, upload_id)
        if original is None:
            return False
        tenant_write_lock(db, original.school_id)
        quota_lock(db)
        row = locked(db, ContentUpload, upload_id)
        if expected_writer is not None and row.lease_owner != expected_writer:
            db.rollback()
            return False
        referenced = db.exec(select(MaterialVersion.id).where(MaterialVersion.upload_id == upload_id)).first()
        if row.sealed_version_id is not None or referenced is not None or row.state == "sealed":
            # A completed replay can release its receiving slot, never its permanent original.
            row.lease_owner, row.lease_until = None, None
            db.add(row)
            db.commit()
            return False
        if row.state == "created" and row.expires_at > db_now(db):
            db.rollback()
            return False
        if row.state == "created":
            row.state = "expired"
        elif row.state == "receiving":
            row.state, row.error_code = "failed", "UPLOAD_INTERRUPTED"
        if row.state not in {"canceled", "expired", "failed"}:
            db.rollback()
            return False
        # The kernel guard proves no old I/O still owns the upload; fence delayed claim callbacks.
        row.generation += 1
        row.lease_owner = cleaner
        row.lease_until = db_now(db) + timedelta(seconds=20)
        db.add(row)
        key, school_id, generation = row.file_key, row.school_id, row.generation
        db.commit()
    storage.remove_unreferenced(upload_id.hex + ".part", guard)
    storage.remove_unreferenced(key, guard)
    with factory() as db:
        tenant_write_lock(db, school_id)
        quota_lock(db)
        row = locked(db, ContentUpload, upload_id)
        referenced = db.exec(select(MaterialVersion.id).where(MaterialVersion.upload_id == upload_id)).first()
        if (row.sealed_version_id is None and referenced is None and row.lease_owner == cleaner
                and row.generation == generation):
            row.reserved_bytes = 0
            row.lease_owner, row.lease_until = None, None
            db.add(row)
            db.commit()
    return True


def cleanup_idle_upload(factory, storage, upload_id):
    """No lease/PID guess: take the stable kernel guard before invalidating or deleting anything."""
    attempt = storage.fence.try_acquire(upload_id)
    if attempt.status == "unavailable":
        raise FenceUnavailable()
    if attempt.status == "busy":
        return False
    with attempt.guard:
        return _cleanup_held(factory, storage, upload_id, attempt.guard)


def reap_uploads(factory, storage, limit=50):
    with factory() as db:
        rows = db.exec(select(ContentUpload.id).where(
            (ContentUpload.lease_owner.is_not(None))
            | ((ContentUpload.state == "created") & (ContentUpload.expires_at <= db_now(db)))
            | (ContentUpload.state.in_(["canceled", "expired", "failed"]) & (ContentUpload.reserved_bytes > 0))
        ).order_by(ContentUpload.expires_at, ContentUpload.id).limit(limit)).all()
    # Each attempt uses a nonblocking filesystem guard outside any DB transaction.
    error_code = None
    for upload_id in rows:
        try:
            cleanup_idle_upload(factory, storage, upload_id)
        except FenceUnavailable:
            error_code = "UPLOAD_FENCE_UNAVAILABLE"
        except OSError:
            error_code = "STORAGE_CLEANUP_FAILED"
    return error_code


async def _io(function, *args, dispose_on_cancel=None):
    """Cancellation must not outlive a file write or transaction running in a thread."""
    task = asyncio.create_task(asyncio.to_thread(function, *args))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                continue
            except Exception:
                break
        if not task.cancelled() and task.exception() is None and dispose_on_cancel:
            dispose_on_cancel(task.result())
        raise


async def _next_chunk(iterator, wall_deadline, heartbeat):
    """Keep the 20-second lease live while waiting up to 30 seconds for network input."""
    task = asyncio.ensure_future(anext(iterator))
    deadline = min(wall_deadline, monotonic() + 30)
    try:
        while True:
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise HTTPException(408, "UPLOAD_TIMEOUT")
            try:
                return await asyncio.wait_for(asyncio.shield(task), min(5, remaining))
            except asyncio.TimeoutError:
                if monotonic() >= deadline:
                    raise HTTPException(408, "UPLOAD_TIMEOUT") from None
                await heartbeat()
    finally:
        if not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)


async def receive_upload(factory, storage, context, upload_id, source):
    """context is server-derived (user.id, login.id, work_role), never HTTP body identity."""
    writer_id = uuid4()
    stream, guard = None, None
    try:
        await _io(_check_upload, factory, context, upload_id)
        attempt = await _io(storage.fence.try_acquire, upload_id,
                            dispose_on_cancel=lambda result: result.guard.close() if result.guard else None)
        if attempt.status != "acquired":
            raise HTTPException(409 if attempt.status == "busy" else 503,
                                "UPLOAD_BUSY" if attempt.status == "busy" else "UPLOAD_FENCE_UNAVAILABLE")
        guard = attempt.guard
        snapshot = await _io(_claim, factory, context, upload_id, writer_id, guard)
        generation, replay = snapshot["generation"], snapshot["replay"]
        digest, count, signature = hashlib.sha256(), 0, b""
        start = checkpoint = monotonic()
        if not replay:
            await _io(_heartbeat, factory, context, upload_id, writer_id, generation, replay, guard)
            stream = await _io(storage.create, upload_id.hex + ".part", guard, dispose_on_cancel=lambda file: file.close())
        iterator = aiter(source)
        while True:
            remaining = 300 - (monotonic() - start)
            if remaining <= 0:
                raise HTTPException(408, "UPLOAD_TIMEOUT")
            try:
                piece = await _next_chunk(iterator, start + 300, lambda: _io(
                    _heartbeat, factory, context, upload_id, writer_id, generation, replay, guard))
            except StopAsyncIteration:
                break
            if monotonic() - checkpoint >= 5:
                await _io(_heartbeat, factory, context, upload_id, writer_id, generation, replay, guard)
                checkpoint = monotonic()
            count += len(piece)
            if count > snapshot["expected_bytes"]:
                raise HTTPException(413, "上传字节超过声明上限")
            signature = (signature + piece[:8])[:8]
            digest.update(piece)
            if stream:
                await _io(stream.write, piece)
        if count != snapshot["expected_bytes"] or digest.hexdigest() != snapshot["expected_hash"]:
            raise HTTPException(409, "文件字节或SHA256不符")
        if ((snapshot["format"] == "pdf" and not signature.startswith(b"%PDF-"))
                or (snapshot["format"] in {"docx", "pptx"} and not signature.startswith(b"PK\x03\x04"))):
            raise HTTPException(415, "文件类型与声明不符")
        await _io(_heartbeat, factory, context, upload_id, writer_id, generation, replay, guard)
        if replay:
            with factory() as db:
                identity = load_identity(db, *context)
                return upload_status(db, identity, upload_id)
        await _io(storage.flush, stream, guard)
        await _io(stream.close)
        stream = None
        await _io(storage.seal, upload_id.hex + ".part", snapshot["file_key"], guard)
        free = await _io(storage.free_bytes)
        return await _io(_finish, factory, context, upload_id, writer_id, generation, free, guard)
    except FenceUnavailable:
        raise HTTPException(503, "UPLOAD_FENCE_UNAVAILABLE") from None
    except asyncio.TimeoutError as error:
        raise HTTPException(408, "UPLOAD_TIMEOUT") from error
    except OSError as error:
        code = "STORAGE_FULL" if error.errno == errno.ENOSPC else "STORAGE_UNAVAILABLE"
        raise HTTPException(507 if error.errno == errno.ENOSPC else 503, code) from None
    finally:
        try:
            if stream:
                await _io(stream.close)
        finally:
            if guard:
                try:
                    # Keep the same guard through cleanup and accounting, including completed replays.
                    await _io(_cleanup_held, factory, storage, upload_id, guard, writer_id)
                except (OSError, FenceUnavailable):
                    raise HTTPException(503, "STORAGE_CLEANUP_FAILED：预留空间保持占用") from None
                finally:
                    await _io(guard.close)
