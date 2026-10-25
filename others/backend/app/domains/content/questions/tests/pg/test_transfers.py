"""Semantic PG candidates only: no claim about real shared admission, runner or physical cleanup."""
from uuid import UUID

import pytest
from fastapi import HTTPException
from sqlalchemy import func
from sqlmodel import select

from app.domains.content.questions.lifecycle import change_parent
from app.domains.content.questions.models import TransferTask
from app.domains.content.questions.schemas import ParentChange
from app.domains.content.questions.tests.pg.test_workflows import SEMANTIC_BUDGET, bank, identity, publication
from app.domains.content.questions.transfers import (
    ExportCreate, ImportCreate, TaskGeneration, TransferAdmission, cancel_transfer, create_export, create_import, require_task,
)

SEMANTIC_ADMISSION = TransferAdmission(lambda _db, _owner, *, receiving: None)


def test_missing_shared_admission_never_creates_an_import_task(db):
    admin, teacher = identity(db, "admin", "administrator"), identity(db, "teacher", "teacher")
    library_id = bank(db, admin)
    before = db.exec(select(func.count()).select_from(TransferTask)).one()
    with pytest.raises(HTTPException) as missing:
        create_import(db, teacher, ImportCreate(library_id=library_id, format="csv", expected_bytes=50,
            input_hash="a" * 64), "c1-transfer-no-queue", SEMANTIC_BUDGET)
    assert missing.value.status_code == 503
    assert db.exec(select(func.count()).select_from(TransferTask)).one() == before


def test_cancel_preserves_reservation_until_trusted_stop_and_cleanup(db):
    admin, teacher = identity(db, "admin", "administrator"), identity(db, "teacher", "teacher")
    created = create_import(db, teacher, ImportCreate(library_id=bank(db, admin), format="csv", expected_bytes=50,
        input_hash="a" * 64), "c1-transfer-create", SEMANTIC_BUDGET, SEMANTIC_ADMISSION)
    task_id = UUID(created["task_id"])
    result = cancel_transfer(db, teacher, task_id, TaskGeneration(generation=1), "c1-transfer-cancel")
    assert cancel_transfer(db, teacher, task_id, TaskGeneration(generation=1), "c1-transfer-cancel") == result
    task = db.get(TransferTask, task_id)
    assert task.state == "canceled" and task.generation == 2
    assert task.reserved_bytes == 33554432 and not task.stop_confirmed


def test_export_task_cannot_restore_read_access_after_source_retirement(db):
    admin, teacher = identity(db, "admin", "administrator"), identity(db, "teacher", "teacher")
    library_id = bank(db, admin)
    created, submitted, _published = publication(db, teacher, admin, library_id)
    task = create_export(db, teacher, ExportCreate(library_id=library_id, format="csv",
        version_ids=[UUID(submitted["version_id"])], authorization_statement="Synthetic teaching export"),
        "c1-export-create", SEMANTIC_BUDGET, SEMANTIC_ADMISSION)
    require_task(db, teacher, UUID(task["task_id"]))
    change_parent(db, admin, "question", UUID(created["question_id"]), ParentChange(revision=1, retired=True), "c1-export-retire")
    with pytest.raises(HTTPException) as retired:
        require_task(db, teacher, UUID(task["task_id"]))
    assert retired.value.status_code == 403
