"""C1's two fixed transfer tasks, using the existing runner and global quota lock."""
import asyncio
from datetime import timedelta
import hashlib
from time import monotonic
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import and_, or_
from sqlmodel import select

from app.core.content_transfer_runner import QuestionTransferExecution
from app.domains.content.background_identity import load_identity
from app.domains.content.models import ContentJob, now
from app.domains.content.parse_runner import RunnerUnavailable
from app.domains.content.questions.budget import ContentBudget
from app.domains.content.questions.http import C1Environment
from app.domains.content.questions.imports import ingest_preview
from app.domains.content.questions.models import TransferTask
from app.domains.content.questions.streaming import TransferIO, reap_upload
from app.domains.content.questions.transfer_codec import Preview, INPUT_LIMITS
from app.domains.content.questions.transfers import TransferAdmission, require_task, export_worker_input
from app.domains.content.quota import enforce_budget, enforce_queue, pending_receiver, quota_lock
from app.domains.content.services import locked
from app.domains.content.uploads import _io
from app.domains.core.commands import tenant_write_lock


def admission(db, owner_id, *, receiving):
    enforce_queue(db, owner_id)
    if receiving and pending_receiver(db, owner_id):
        raise HTTPException(409, "已有接收会话，请先完成或取消")


def budget_for(free_bytes):
    return ContentBudget(lambda db, school_id: enforce_budget(db, school_id, free_bytes))


def environment(runtime):
    storage = runtime.require_storage()
    budget = budget_for(runtime.free_bytes())  # sampled before any quota transaction
    gate = TransferAdmission(admission)
    return C1Environment(budget, gate, TransferIO(runtime.factory, storage, budget_for, gate))


def unfinished(model):
    return or_(model.state == "running", and_(model.execution_id.is_not(None),
        or_(model.stop_confirmed.is_(False), model.reserved_bytes > 0)))


class TransferDriver:
    def __init__(self, runtime):
        self.runtime, self.factory, self.storage, self.runner = runtime, runtime.factory, runtime.storage, runtime.runner
        self.owner = uuid4()
        self.last_error = None

    def _claim(self):
        with self.factory() as db:
            first = db.exec(select(TransferTask).where(TransferTask.state == "queued").order_by(
                TransferTask.created_at, TransferTask.id).limit(1)).first()
            if first is None:
                return None
            tenant_write_lock(db, first.school_id)
            quota_lock(db)
            if any(db.exec(select(model.id).where(unfinished(model)).limit(1)).first() is not None
                   for model in (ContentJob, TransferTask)):
                return None
            material = db.exec(select(ContentJob).where(ContentJob.state == "queued").order_by(
                ContentJob.created_at, ContentJob.id).limit(1)).first()
            if material is not None and (material.created_at, str(material.id)) < (first.created_at, str(first.id)):
                return None
            row = locked(db, TransferTask, first.id)
            if row.state != "queued":
                return None
            try:
                identity = load_identity(db, row.owner_id, row.login_session_id, row.work_role)
                require_task(db, identity, row.id)
                if row.kind == "import" and not row.input_sealed:
                    raise HTTPException(409, "未封存输入")
                data = export_worker_input(db, identity, row.id) if row.kind == "export" else None
            except HTTPException:
                row.state, row.stage, row.error_code = "failed", "cleaning", "ACCESS_REVOKED"
                db.add(row)
                db.commit()
                return None
            row.state, row.stage, row.execution_id = "running", "starting", uuid4()
            row.lease_owner, row.lease_until, row.stop_confirmed = self.owner, now() + timedelta(seconds=20), False
            db.add(row)
            result = {"id": row.id, "execution": row.execution_id, "generation": row.generation,
                "kind": row.kind, "format": row.format, "hash": row.input_hash, "bytes": row.expected_bytes,
                "file_key": row.file_key, "data": data}
            db.commit()
            return result

    def _live(self, db, claim):
        initial = db.get(TransferTask, claim["id"])
        tenant_write_lock(db, initial.school_id)
        quota_lock(db)
        row = locked(db, TransferTask, claim["id"])
        if (row.execution_id != claim["execution"] or row.generation != claim["generation"]
                or row.lease_owner != self.owner or row.state != "running"
                or row.lease_until is None or row.lease_until <= now()):
            raise HTTPException(409, "TASK_FENCED")
        require_task(db, load_identity(db, row.owner_id, row.login_session_id, row.work_role), row.id)
        return row

    def _heartbeat(self, claim):
        with self.factory() as db:
            row = self._live(db, claim)
            row.lease_until = now() + timedelta(seconds=20)
            db.add(row)
            db.commit()

    async def _await_live(self, awaitable, claim, timeout):
        work = asyncio.ensure_future(awaitable)
        deadline = monotonic() + timeout
        try:
            while True:
                remaining = deadline - monotonic()
                if remaining <= 0:
                    raise TimeoutError()
                done, _ = await asyncio.wait({work}, timeout=min(5, remaining))
                if work in done:
                    return work.result()
                await _io(self._heartbeat, claim)
        finally:
            if not work.done():
                work.cancel()
            await asyncio.gather(work, return_exceptions=True)

    async def _source(self, claim):
        if claim["data"] is not None:
            for offset in range(0, len(claim["data"]), 65536):
                yield claim["data"][offset:offset + 65536]
            return
        stream = await _io(self.storage.open, claim["file_key"], dispose_on_cancel=lambda file: file.close())
        try:
            while data := await _io(stream.read, 65536):
                yield data
        finally:
            await _io(stream.close)

    def _seal_export(self, claim, raw):
        if not raw or len(raw) > INPUT_LIMITS[claim["format"]] or len(raw) * 2 > 33554432:
            raise HTTPException(413, "INVALID_RESULT")
        if claim["format"] == "xlsx" and not raw.startswith(b"PK\x03\x04"):
            raise HTTPException(409, "INVALID_RESULT")
        if claim["format"] == "csv":
            raw.decode("utf-8-sig", errors="strict")
        attempt = self.storage.fence.try_acquire(claim["id"])
        if attempt.status != "acquired":
            raise HTTPException(503, "OUTPUT_BUSY")
        guard = attempt.guard
        try:
            with self.storage.create(claim["id"].hex + ".part", guard) as file:
                file.write(raw)
                self.storage.flush(file, guard)
            self.storage.seal(claim["id"].hex + ".part", claim["file_key"], guard)
        finally:
            guard.close()

    def _save(self, claim, raw, free):
        with self.factory() as db:
            row = self._live(db, claim)
            if row.kind == "import":
                preview = Preview.model_validate_json(raw)
                ingest_preview(db, row.id, claim["generation"], claim["execution"], self.owner, preview, budget_for(free))
            else:
                row.state, row.stage, row.finished_at = "succeeded", "cleaning", now()
                row.result_hash, row.result_bytes = hashlib.sha256(raw).hexdigest(), len(raw)
                row.retained_bytes = len(raw)
                db.add(row)
                enforce_budget(db, row.school_id, free)
            db.commit()

    def _fail(self, claim, code):
        with self.factory() as db:
            initial = db.get(TransferTask, claim["id"])
            tenant_write_lock(db, initial.school_id)
            quota_lock(db)
            row = locked(db, TransferTask, claim["id"])
            if row.execution_id == claim["execution"] and row.generation == claim["generation"] and row.state != "succeeded":
                row.state, row.stage, row.error_code, row.finished_at = "failed", "cleaning", code, now()
                db.add(row)
                db.commit()

    def _finish_cleanup(self, task_id, execution):
        with self.factory() as db:
            initial = db.get(TransferTask, task_id)
            tenant_write_lock(db, initial.school_id)
            quota_lock(db)
            row = locked(db, TransferTask, task_id)
            if row.execution_id != execution:
                return
            # Called only after real stop + controller release and all host writers closed.
            row.stop_confirmed, row.reserved_bytes = True, 0
            row.lease_owner, row.lease_until, row.stage = None, None, row.state
            db.add(row)
            db.commit()

    async def _cleanup(self, task_id, execution):
        try:
            state = await asyncio.wait_for(self.runner.stop(execution), 10)
            if state.execution_id != execution or not state.stop_confirmed or state.state == "running":
                return False
            # Remove unpublished export files before releasing its reservation.
            with self.factory() as db:
                row = db.get(TransferTask, task_id)
                remove = row.kind == "export" and row.state != "succeeded"
            if remove:
                attempt = await _io(self.storage.fence.try_acquire, task_id)
                if attempt.status != "acquired":
                    return False
                try:
                    for suffix in (".part", ".blob"):
                        await _io(self.storage.remove_unreferenced, task_id.hex + suffix, attempt.guard)
                finally:
                    attempt.guard.close()
            if not await asyncio.wait_for(self.runner.release(execution), 10):
                return False
            await _io(self._finish_cleanup, task_id, execution)
            return True
        except (OSError, HTTPException, TimeoutError, RunnerUnavailable):
            return False

    def _recovery(self):
        with self.factory() as db:
            row = db.exec(select(TransferTask).where(unfinished(TransferTask), TransferTask.execution_id.is_not(None),
                or_(TransferTask.lease_until.is_(None), TransferTask.lease_until <= now())).order_by(
                TransferTask.created_at, TransferTask.id).limit(1)).first()
            if row is None:
                return None
            tenant_write_lock(db, row.school_id)
            quota_lock(db)
            row = locked(db, TransferTask, row.id)
            if row.lease_until is not None and row.lease_until > now():
                return None
            if row.state == "running":
                row.state, row.error_code, row.generation = "failed", "WORKER_INTERRUPTED", row.generation + 1
            row.stage, row.lease_owner, row.lease_until = "cleaning", self.owner, now() + timedelta(seconds=20)
            result = row.id, row.execution_id
            db.add(row)
            db.commit()
            return result

    def _reap_unstarted(self):
        with self.factory() as db:
            rows = db.exec(select(TransferTask).where(TransferTask.execution_id.is_(None), TransferTask.reserved_bytes > 0,
                or_(TransferTask.state.in_(["failed", "canceled", "expired"]),
                    and_(TransferTask.kind == "import", TransferTask.expires_at <= now()))).limit(50)).all()
            tasks = [(row.id, row.kind) for row in rows]
        for task_id, kind in tasks:
            if kind == "import":
                reap_upload(environment(self.runtime).io, task_id)
            else:
                with self.factory() as db:
                    row = db.get(TransferTask, task_id)
                    tenant_write_lock(db, row.school_id)
                    quota_lock(db)
                    row = locked(db, TransferTask, task_id)
                    if row.execution_id is None and row.state in {"failed", "canceled", "expired"}:
                        row.stop_confirmed, row.reserved_bytes = True, 0
                        db.add(row)
                        db.commit()

    async def tick(self):
        await _io(self._reap_unstarted)
        recovered = await _io(self._recovery)
        if recovered:
            await self._cleanup(*recovered)
            return True
        claim = await _io(self._claim)
        if claim is None:
            return False
        try:
            await self.runner.capabilities()  # verifies the closed three-kind protocol
            task = QuestionTransferExecution("question_" + claim["kind"], claim["id"], claim["execution"],
                claim["generation"], claim["hash"], claim["format"])
            source = self._source(claim)
            try:
                state = await self._await_live(self.runner.start(task, source), claim, 300)
            finally:
                await source.aclose()
            deadline = monotonic() + 30
            while state.state == "running" and monotonic() < deadline:
                await asyncio.sleep(.25)
                await _io(self._heartbeat, claim)
                state = await self._await_live(self.runner.inspect(claim["execution"]), claim, 10)
            if state.execution_id != claim["execution"] or state.state != "succeeded" or not state.stop_confirmed:
                raise HTTPException(409, "INVALID_RESULT")
            raw = await self._await_live(self.runner.result(claim["execution"]), claim, 10)
            if claim["kind"] == "export":
                await _io(self._seal_export, claim, raw)
            free = await _io(self.storage.free_bytes)
            await _io(self._save, claim, raw, free)
        except asyncio.CancelledError:
            await _io(self._fail, claim, "WORKER_INTERRUPTED")
            raise
        except Exception:
            await _io(self._fail, claim, "WORKER_INTERRUPTED")
            self.last_error = "WORKER_INTERRUPTED"
        finally:
            if not await self._cleanup(claim["id"], claim["execution"]):
                self.last_error = "CLEANUP_UNCONFIRMED"
        return True
