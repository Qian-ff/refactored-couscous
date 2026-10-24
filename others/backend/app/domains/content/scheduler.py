"""Lifespan-owned driver. All untrusted parsing is delegated to A's restricted runner."""
import asyncio
import errno
import hashlib
from time import monotonic
from uuid import uuid4

from fastapi import HTTPException

from app.domains.content import task_store
from app.domains.content.parse_result import ResultError, validate_result
from app.domains.content.parse_runner import ParseTask, RunnerUnavailable
from app.domains.content.uploads import _io

SAFE_ERRORS = {"TIMEOUT", "RESOURCE_LIMIT", "PARSER_UNAVAILABLE", "UNSUPPORTED_TYPE", "NO_TEXT", "CORRUPT_FILE",
               "STORAGE_FULL", "ACCESS_REVOKED", "WORKER_INTERRUPTED", "INVALID_RESULT", "INVALID_ENCODING",
               "ENCRYPTED_FILE", "UNSUPPORTED_ENCODING"}


class ContentScheduler:
    def __init__(self, factory, storage, runner):
        self.factory, self.storage, self.runner = factory, storage, runner
        self.owner = uuid4()
        self.last_error_code = None

    async def _source(self, specification):
        digest, count = hashlib.sha256(), 0
        stream = None
        try:
            if "input" in specification:
                data = specification["input"]
                digest.update(data)
                count += len(data)
                yield data
            else:
                stream = await _io(self.storage.open, specification["key"],
                                   dispose_on_cancel=lambda file: file.close())
                while data := await _io(stream.read, 65536):
                    count += len(data)
                    if count > specification["bytes"]:
                        raise ResultError("CORRUPT_FILE")
                    digest.update(data)
                    yield data
            if count != specification["bytes"] or digest.hexdigest() != specification["hash"]:
                raise ResultError("CORRUPT_FILE")
        finally:
            if stream:
                await _io(stream.close)

    async def _live_call(self, awaitable, claim, deadline):
        task = asyncio.ensure_future(awaitable)
        try:
            while True:
                remaining = deadline - monotonic()
                if remaining <= 0:
                    raise TimeoutError()
                done, _pending = await asyncio.wait({task}, timeout=min(5, remaining))
                if task in done:
                    return task.result()
                await _io(task_store.heartbeat, self.factory, claim["job_id"], self.owner, claim["generation"])
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)

    @staticmethod
    def _check_state(state, execution_id):
        if (state.execution_id != execution_id or state.state not in {"running", "succeeded", "failed", "stopped"}
                or type(state.stop_confirmed) is not bool or type(state.output_bytes) is not int
                or not 0 <= state.output_bytes <= 16 * 1024 * 1024):
            raise ResultError()

    async def _reap(self, job_id, execution_id):
        try:
            state = await asyncio.wait_for(self.runner.stop(execution_id), 10)
            self._check_state(state, execution_id)
            if not state.stop_confirmed or state.state == "running":
                self.last_error_code = "WORKER_INTERRUPTED"
                return False
            await _io(task_store.stopped, self.factory, job_id, execution_id)
            released = await asyncio.wait_for(self.runner.release(execution_id), 10)
            if released is not True:
                self.last_error_code = "STORAGE_CLEANUP_FAILED"
                return False
            await _io(task_store.cleaned, self.factory, job_id, execution_id)
            return True
        except (RunnerUnavailable, TimeoutError, ResultError, OSError):
            self.last_error_code = "PARSER_UNAVAILABLE"
            return False

    async def tick(self):
        recovered = await _io(task_store.recovery_candidate, self.factory, self.owner)
        if recovered:
            await self._reap(recovered["job_id"], recovered["execution_id"])
            return True
        claim = await _io(task_store.claim, self.factory, self.owner)
        if claim is None:
            return False
        potential_start = False
        failed_code = None
        try:
            capabilities = await asyncio.wait_for(self.runner.capabilities(), 5)
            capabilities.require_supported()
            # Persist the execution ID before sending anything; stop must fence delayed starts.
            potential_start = True
            await _io(task_store.heartbeat, self.factory, claim["job_id"], self.owner, claim["generation"], True)
            last_heartbeat = monotonic()
            spec = claim["spec"]
            task = ParseTask(job_id=claim["job_id"], execution_id=claim["execution_id"],
                             generation=claim["generation"], version_id=claim["version_id"],
                             input_sha256=spec["hash"], format=spec["format"], encoding=spec["encoding"])
            deadline = monotonic() + 60
            source = self._source(spec)
            try:
                state = await self._live_call(self.runner.start(task, source), claim, deadline)
            finally:
                await source.aclose()
            while True:
                self._check_state(state, claim["execution_id"])
                if state.state == "succeeded" and state.stop_confirmed:
                    break
                if state.state in {"failed", "stopped"}:
                    raise ResultError(state.error_code if state.error_code in SAFE_ERRORS else "CORRUPT_FILE")
                if monotonic() >= deadline:
                    raise TimeoutError()
                await asyncio.sleep(1)
                if monotonic() - last_heartbeat >= 5:
                    await _io(task_store.heartbeat, self.factory, claim["job_id"], self.owner, claim["generation"])
                    last_heartbeat = monotonic()
                state = await self._live_call(self.runner.inspect(claim["execution_id"]), claim, deadline)
            raw = await self._live_call(self.runner.result(claim["execution_id"]), claim, deadline)
            result = validate_result(raw, spec["format"])
            free = await _io(self.storage.free_bytes)
            await _io(task_store.save_snapshot, self.factory, claim["job_id"], self.owner,
                      claim["generation"], result, len(raw), free)
        except RunnerUnavailable:
            failed_code = "PARSER_UNAVAILABLE"
        except TimeoutError:
            failed_code = "TIMEOUT"
        except ResultError as error:
            failed_code = error.code if error.code in SAFE_ERRORS else "INVALID_RESULT"
        except HTTPException as error:
            failed_code = ({401: "ACCESS_REVOKED", 403: "ACCESS_REVOKED", 413: "RESOURCE_LIMIT",
                            507: "STORAGE_FULL"}).get(error.status_code, "WORKER_INTERRUPTED")
        except OSError as error:
            failed_code = "STORAGE_FULL" if error.errno == errno.ENOSPC else "CORRUPT_FILE"
        except asyncio.CancelledError:
            failed_code = "WORKER_INTERRUPTED"
            raise
        except Exception:
            failed_code = "WORKER_INTERRUPTED"
        finally:
            try:
                if failed_code:
                    await _io(task_store.fail, self.factory, claim["job_id"], claim["execution_id"],
                              failed_code, not potential_start, claim["generation"])
            finally:
                if potential_start:
                    await self._reap(claim["job_id"], claim["execution_id"])
        return True

    async def serve(self, stop_event):
        """A lifespan sets stop_event and awaits this coroutine, including stop/cleanup confirmation."""
        while not stop_event.is_set():
            work = asyncio.create_task(self.tick())
            stopping = asyncio.create_task(stop_event.wait())
            try:
                done, _pending = await asyncio.wait({work, stopping}, return_when=asyncio.FIRST_COMPLETED)
                if stopping in done and not work.done():
                    work.cancel()
                await asyncio.gather(work, return_exceptions=False)
            except asyncio.CancelledError:
                if not stop_event.is_set():
                    raise
            except Exception:
                self.last_error_code = "WORKER_INTERRUPTED"
            finally:
                if not stopping.done():
                    stopping.cancel()
                if not work.done():
                    work.cancel()
                await asyncio.gather(stopping, work, return_exceptions=True)
            try:
                await asyncio.wait_for(stop_event.wait(), 1)
            except TimeoutError:
                pass
