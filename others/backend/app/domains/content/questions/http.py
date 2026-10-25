"""Staff-only C1 HTTP dependencies; A mounts routers and supplies runtime integration."""
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Query, Request

from app.domains.content.questions.budget import ContentBudget
from app.domains.content.questions.policy import staff
from app.domains.content.questions.transfers import TransferAdmission
from app.domains.content.questions.streaming import TransferIO
from app.domains.core.auth import CurrentIdentity, Identity


def staff_identity(identity: CurrentIdentity):
    staff(identity)
    return identity


StaffIdentity = Annotated[Identity, Depends(staff_identity)]
CommandKey = Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=128)]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0, le=2147483647)]
Keyword = Annotated[str, Query(max_length=100)]


@dataclass(frozen=True)
class C1Environment:
    budget: ContentBudget = ContentBudget()
    admission: TransferAdmission = TransferAdmission()
    io: TransferIO | None = None

    def require_io(self):
        if self.io is None:
            raise HTTPException(503, "CONTENT_TRANSFER_IO_UNAVAILABLE：文件运行环境尚未接入")
        return self.io


def get_environment(request: Request):
    value = getattr(request.app.state, "c1_environment", None)
    if not isinstance(value, C1Environment):
        raise HTTPException(503, "CONTENT_C1_UNAVAILABLE：C1公共运行环境尚未接入")
    return value


Environment = Annotated[C1Environment, Depends(get_environment)]
