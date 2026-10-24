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
    return getattr(request.app.state, "content_runtime", None) or ContentRuntime()


Runtime = Annotated[ContentRuntime, Depends(get_runtime)]
