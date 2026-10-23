"""C/A integration seam. No subprocess fallback when the restricted adapter is absent."""
from dataclasses import dataclass
from collections.abc import AsyncIterator
from typing import Protocol
from uuid import UUID


class RunnerUnavailable(RuntimeError):
    def __init__(self):
        super().__init__("PARSER_UNAVAILABLE")


@dataclass(frozen=True)
class RunnerCapabilities:
    protocol: str
    image_digest: str
    non_root: bool
    read_only_root: bool
    no_network: bool
    task_only_mounts: bool
    environment_allowlist: bool
    no_container_socket: bool
    global_exclusion: bool
    stop_confirmation: bool
    memory_bytes: int
    cpu_limit: float
    temporary_bytes: int
    pids_limit: int
    timeout_seconds: int
    stdout_bytes: int
    stderr_bytes: int

    def require_supported(self):
        flags = (self.non_root, self.read_only_root, self.no_network, self.task_only_mounts,
                 self.environment_allowlist, self.no_container_socket, self.global_exclusion, self.stop_confirmation)
        integers = ((self.memory_bytes, 384 * 1024 * 1024), (self.temporary_bytes, 64 * 1024 * 1024),
                    (self.pids_limit, 64), (self.timeout_seconds, 60),
                    (self.stdout_bytes, 16 * 1024 * 1024), (self.stderr_bytes, 64 * 1024))
        digest = self.image_digest.removeprefix("sha256:")
        if (self.protocol != "labconnect.parse/1" or not self.image_digest.startswith("sha256:")
                or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest)
                or not all(flag is True for flag in flags)
                or any(type(value) is not int or not 0 < value <= maximum for value, maximum in integers)
                or type(self.cpu_limit) not in {int, float} or not 0 < self.cpu_limit <= 1):
            raise RunnerUnavailable()


@dataclass(frozen=True)
class ParseTask:
    job_id: UUID
    generation: int
    version_id: UUID
    input_sha256: str
    format: str
    encoding: str
    # C streams the authorized immutable input; A stages only these bytes in the task mount.


@dataclass(frozen=True)
class ExecutionState:
    execution_id: UUID
    state: str  # running/succeeded/failed/stopped
    stop_confirmed: bool
    output_bytes: int = 0
    error_code: str | None = None


class ParseRunner(Protocol):
    async def capabilities(self) -> RunnerCapabilities: ...
    async def start(self, task: ParseTask, source: AsyncIterator[bytes]) -> ExecutionState: ...
    async def inspect(self, execution_id: UUID) -> ExecutionState: ...
    async def stop(self, execution_id: UUID) -> ExecutionState: ...
    async def result(self, execution_id: UUID) -> bytes: ...


class UnavailableRunner:
    async def capabilities(self) -> RunnerCapabilities:
        raise RunnerUnavailable()

    async def start(self, task: ParseTask, source: AsyncIterator[bytes]) -> ExecutionState:
        raise RunnerUnavailable()

    async def inspect(self, execution_id: UUID) -> ExecutionState:
        raise RunnerUnavailable()

    async def stop(self, execution_id: UUID) -> ExecutionState:
        raise RunnerUnavailable()

    async def result(self, execution_id: UUID) -> bytes:
        raise RunnerUnavailable()
