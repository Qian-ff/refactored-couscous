"""The two fixed question execution bindings; shared runner owns transport and lifecycle."""
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class QuestionTransferExecution:
    task_kind: str
    task_id: UUID
    execution_id: UUID
    generation: int
    input_sha256: str
    format: str
