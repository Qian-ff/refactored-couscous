"""Internal C/D handoff only; deliberately no placeholder HTTP routes or generated SDK."""
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID


@dataclass(frozen=True)
class TutoringStatus:
    state: Literal["unavailable"]
    as_of: datetime
    reason: str
    implemented: bool = False


def tutoring_status(student_id: UUID) -> TutoringStatus:
    """B1 cannot verify ongoing exams. C must pause students, irrespective of client flags.

    B2 replaces this service with the account-level gate described in a2-protocols.
    C may independently validate staff use in its own current-identity authorization.
    """
    return TutoringStatus(state="unavailable", as_of=datetime.now(UTC), reason="B2_EXAM_STATE_NOT_IMPLEMENTED")
