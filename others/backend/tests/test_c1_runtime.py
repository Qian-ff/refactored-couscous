"""Ordinary fixed-protocol and mixed receiving/accounting checks, not a stress matrix."""
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from app.core.content_runner import validate_task, task_input_limit
from app.core.content_transfer_runtime import environment
from app.domains.content.parse_runner import RunnerUnavailable
from app.domains.content.runtime import ContentRuntime
from app.domains.content.storage import PrivateStorage
from app.domains.content.questions.transfers import ImportCreate, TaskGeneration, create_import, cancel_transfer
from app.domains.content.questions.models import TransferTask
from app.domains.content.questions.streaming import reap_upload
from app.domains.content.questions.tests.pg.test_workflows import bank, identity
from app.domains.content.quota import pending_receiver, receiving_slots, accounting_queries
from app.domains.content.models import now
from app.domains.content.schemas import UploadCreate
from app.domains.content.uploads import create_upload


def test_fixed_transfer_binding_has_no_fake_material_version_or_command():
    task = {"task_kind": "question_import", "task_id": str(uuid4()), "execution_id": str(uuid4()),
            "generation": 1, "input_sha256": "a" * 64, "format": "xlsx"}
    assert validate_task(task) == task
    assert task_input_limit(task) == 5242880
    assert task_input_limit({**task, "task_kind": "question_export"}) == 16777216
    for changed in ({**task, "command": "arbitrary"}, {**task, "version_id": str(uuid4())},
                    {**task, "task_kind": "arbitrary"}, {**task, "format": "pdf"}):
        with pytest.raises(RunnerUnavailable):
            validate_task(changed)


def test_unconfigured_http_write_stays_unavailable(client, auth, monkeypatch):
    from app.main import app
    monkeypatch.setattr(app.state, "c1_environment", None, raising=False)
    from app.domains.content.questions.tests.unit.test_schema import sample_question
    result = client.post("/api/v1/content/questions/drafts", headers={**auth(), "Idempotency-Key": "t2-unconfigured-write"},
        json={"library_id": str(uuid4()), "payload": sample_question()})
    assert result.status_code == 503


def test_canceled_unclosed_import_counts_until_real_guarded_cleanup(db, tmp_path):
    admin, teacher = identity(db, "admin", "administrator"), identity(db, "teacher", "teacher")
    library_id = bank(db, admin)
    runtime = ContentRuntime(factory=lambda: _BorrowedSession(db), storage=PrivateStorage(tmp_path))
    env = environment(runtime)
    created = create_import(db, teacher, ImportCreate(library_id=library_id, format="csv", expected_bytes=10,
        input_hash="a"*64), "t2-normal-import-create", env.budget, env.admission)
    row = db.get(TransferTask, UUID(created["task_id"]))
    assert pending_receiver(db, teacher.user.id)
    old_request = UploadCreate(library_id=library_id, title="T2 synthetic upload", original_name="synthetic.txt",
        format="txt", expected_bytes=10, expected_hash="a"*64)
    with pytest.raises(HTTPException) as old_busy:
        create_upload(db, teacher, old_request, "t2-old-sees-c1-receiver", runtime.free_bytes())
    assert old_busy.value.status_code == 409
    queries, _scoped, reservations = accounting_queries(teacher.user.school_id)
    assert sum(int(db.exec(query).one()) for query in queries) >= 33554432
    assert sum(int(db.exec(query).one()) for query in reservations) == 33554432
    row.state, row.lease_owner, row.lease_until = "receiving", uuid4(), now()
    db.add(row)
    db.flush()
    cancel_transfer(db, teacher, row.id, TaskGeneration(generation=1), "t2-normal-import-cancel")
    assert receiving_slots(db) == 1
    assert pending_receiver(db, teacher.user.id)
    with pytest.raises(HTTPException) as busy:
        env.admission.admit(db, teacher.user.id, receiving=True)
    assert busy.value.status_code == 409
    # No writer exists in this fixture; the real kernel guard proves cleanup may proceed.
    assert reap_upload(env.io, row.id)
    assert receiving_slots(db) == 0
    assert not pending_receiver(db, teacher.user.id)
    assert db.get(TransferTask, row.id, populate_existing=True).reserved_bytes == 0
    create_upload(db, teacher, old_request, "t2-old-receiver-create", runtime.free_bytes())
    with pytest.raises(HTTPException) as new_busy:
        create_import(db, teacher, ImportCreate(library_id=library_id, format="csv", expected_bytes=10,
            input_hash="b"*64), "t2-c1-sees-old-receiver", env.budget, env.admission)
    assert new_busy.value.status_code == 409


class _BorrowedSession:
    """Share the test's rollback-only DB connection; production IO always opens a fresh session."""
    def __init__(self, db):
        self.db = db

    def __enter__(self):
        return self.db

    def __exit__(self, *_args):
        pass
