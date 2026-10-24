"""A injects this runtime through app.state; C never reads new environment secrets."""
from dataclasses import dataclass, field
from typing import Annotated, Callable

from fastapi import Depends, HTTPException, Request
from sqlmodel import Session

from app.core.db import engine
from app.domains.content.parse_runner import ParseRunner, UnavailableRunner
from app.domains.content.storage import PrivateStorage


@dataclass
class ContentRuntime:
    factory: Callable = field(default_factory=lambda: lambda: Session(engine))
    storage: PrivateStorage | None = None
    runner: ParseRunner = field(default_factory=UnavailableRunner)
    unavailable_reason: str | None = None

    def require_storage(self):
        if self.storage is None:
            raise HTTPException(503, "STORAGE_UNAVAILABLE")
        return self.storage

    def free_bytes(self):
        if self.storage is None:
            return None
        try:
            return self.storage.free_bytes()
        except OSError:
            raise HTTPException(503, "STORAGE_UNAVAILABLE") from None


def get_runtime(request: Request):
    runtime = getattr(request.app.state, "content_runtime", None) or ContentRuntime()
    if runtime.unavailable_reason:
        raise HTTPException(503, runtime.unavailable_reason)
    return runtime


Runtime = Annotated[ContentRuntime, Depends(get_runtime)]
