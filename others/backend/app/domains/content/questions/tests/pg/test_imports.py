"""Requires A副2's actual migrated non-owner PostgreSQL environment; not run as pure tests."""
from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import func
from sqlmodel import select

from app.domains.content.models import now
from app.domains.content.questions.imports import ImportConfirm, confirm_import, preview_hash
from app.domains.content.questions.models import ImportBatch, ImportCreatedQuestion, Question, TransferTask
from app.domains.content.questions.schemas import canonical_bytes
from app.domains.content.questions.tests.pg.test_workflows import SEMANTIC_BUDGET, bank, identity
from app.domains.content.questions.tests.unit.test_transfer_codec import content
from app.domains.content.questions.transfer_codec import export_template, parse_template


def ready_batch(db, teacher, library_id):
    raw = export_template([content(stem="Synthetic import-only prompt")], "csv")
    preview = parse_template(raw, "csv")
    batch = ImportBatch(library_id=library_id, actor_id=teacher.user.id, login_session_id=teacher.login.id,
        work_role=teacher.work_role, input_hash=preview.input_hash, state="ready", revision=2, row_count=1,
        normalized_rows=[row.model_dump(mode="json") for row in preview.rows], expires_at=now() + timedelta(hours=1))
    batch.retained_bytes = len(canonical_bytes({"rows": batch.normalized_rows, "errors": batch.errors}))
    db.add(batch)
    db.flush()
    task_id = uuid4()
    task = TransferTask(id=task_id, batch_id=batch.id, kind="import", format="csv", library_id=library_id,
        school_id=teacher.user.school_id, owner_id=teacher.user.id, login_session_id=teacher.login.id,
        work_role=teacher.work_role, input_hash=preview.input_hash, expected_bytes=len(raw), file_key=task_id.hex + ".blob",
        # Synthetic completed-task fixture, not evidence of real upload/runner execution.
        state="succeeded", input_sealed=True, result_hash=preview.digest(), result_bytes=len(canonical_bytes(preview)),
        execution_id=uuid4(), stop_confirmed=True, reserved_bytes=0, retained_bytes=len(raw), finished_at=now(), expires_at=batch.expires_at)
    db.add(task)
    db.flush()
    batch.preview_hash = preview_hash(batch, task)
    db.add(batch)
    db.commit()
    return batch.id, ImportConfirm(revision=2, library_id=library_id, input_hash=batch.input_hash, preview_hash=batch.preview_hash)


def test_confirm_import_is_atomic_and_replay_never_creates_second_questions(db):
    admin, teacher = identity(db, "admin", "administrator"), identity(db, "teacher", "teacher")
    library_id = bank(db, admin)
    batch_id, request = ready_batch(db, teacher, library_id)
    result = confirm_import(db, teacher, batch_id, request, "c1-import-confirm", SEMANTIC_BUDGET)
    assert confirm_import(db, teacher, batch_id, request, "c1-import-confirm", SEMANTIC_BUDGET) == result
    assert result["created_count"] == 1
    assert "payload" not in result
    rows = db.exec(select(ImportCreatedQuestion).where(ImportCreatedQuestion.batch_id == batch_id)).all()
    assert len(rows) == 1
    assert db.get(Question, rows[0].question_id) is not None
    other, changed = ready_batch(db, teacher, library_id)
    with pytest.raises(HTTPException) as conflict:
        confirm_import(db, teacher, other, changed, "c1-import-new-duplicate", SEMANTIC_BUDGET)
    assert conflict.value.status_code == 409
    assert db.get(ImportBatch, other).state == "ready"


def test_missing_accounting_rolls_back_batch_and_all_question_insertions(db):
    admin, teacher = identity(db, "admin", "administrator"), identity(db, "teacher", "teacher")
    batch_id, request = ready_batch(db, teacher, bank(db, admin))
    before = db.exec(select(func.count()).select_from(Question)).one()
    with pytest.raises(HTTPException) as missing:
        confirm_import(db, teacher, batch_id, request, "c1-import-no-accounting")
    assert missing.value.status_code == 503
    assert db.exec(select(func.count()).select_from(Question)).one() == before
    assert db.get(ImportBatch, batch_id).state == "ready"
    assert not db.exec(select(ImportCreatedQuestion).where(ImportCreatedQuestion.batch_id == batch_id)).all()
