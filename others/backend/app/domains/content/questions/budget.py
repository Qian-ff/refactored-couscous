"""A supplies one deployment-wide accounting function; absent integration fails closed."""
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import HTTPException

from app.domains.content.quota import quota_lock


@dataclass(frozen=True)
class ContentBudget:
    # Callback uses a disk probe captured before the transaction and includes all C1/C02 retained/reserved rows.
    enforce: Callable | None = None

    def admit(self, db, school_id):
        if self.enforce is None:
            raise HTTPException(503, "CONTENT_BUDGET_UNAVAILABLE：公共统一计量尚未接入")
        quota_lock(db)
        db.flush()
        self.enforce(db, school_id)
