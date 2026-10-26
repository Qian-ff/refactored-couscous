"""Real PG regression candidate; requires T1's migrated/non-owner test entry, not run yet."""
from datetime import timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

from sqlmodel import Session

from app.domains.content.models import now
from app.domains.content.questions.models import TransferTask
from app.domains.content.questions.streaming import cleanup_upload, receiving_count
from app.domains.content.questions.tests.pg.test_workflows import SEMANTIC_BUDGET, bank, identity
from app.domains.content.questions.tests.pg.test_transfers import SEMANTIC_ADMISSION
from app.domains.content.questions.transfers import ImportCreate, TaskGeneration, cancel_transfer, create_import
from app.domains.content.storage import PrivateStorage


def test_canceled_receiver_keeps_slot_until_actual_file_cleanup_finishes(db, tmp_path):
    admin, teacher = identity(db, "admin", "administrator"), identity(db, "teacher", "teacher")
    library_id = bank(db, admin)
    baseline = receiving_count(db)
    created = create_import(db, teacher, ImportCreate(library_id=library_id, format="csv", expected_bytes=7,
        input_hash="a" * 64), "c1-slot-create", SEMANTIC_BUDGET, SEMANTIC_ADMISSION)
    task_id, writer = UUID(created["task_id"]), uuid4()
    task = db.get(TransferTask, task_id)
    task.state, task.stage = "receiving", "receiving"
    task.lease_owner, task.lease_until = writer, now() + timedelta(seconds=20)
    db.add(task)
    db.commit()
    assert receiving_count(db) == baseline + 1
    db.commit()

    storage = PrivateStorage(tmp_path)
    attempt = storage.fence.try_acquire(task_id)
    assert attempt.status == "acquired"
    with attempt.guard as guard:
        with storage.create(task_id.hex + ".part", guard) as output:
            output.write(b"pending")
            storage.flush(output, guard)
            cancel_transfer(db, teacher, task_id, TaskGeneration(generation=1), "c1-slot-cancel")
            assert receiving_count(db) == baseline + 1
            # A passed lease deadline also does not prove that this real file writer has closed.
            task = db.get(TransferTask, task_id, populate_existing=True)
            task.lease_until = now() - timedelta(seconds=1)
            db.add(task)
            db.commit()
            assert receiving_count(db) == baseline + 1
            assert storage.path(task_id.hex + ".part").exists()
            db.commit()

        # The fixture connection remains inside its outer rollback transaction. Each real
        # cleanup/read session uses a savepoint, so this candidate never needs the main DB.
        connection = db.get_bind()

        def factory():
            return Session(bind=connection, join_transaction_mode="create_savepoint")

        removal_checks = []

        def observed_remove(key, actual_guard):
            with factory() as reader:
                current = reader.get(TransferTask, task_id)
                assert current.stage == "cleanup" and current.lease_owner is not None
                assert receiving_count(reader) == baseline + 1
            storage.remove_unreferenced(key, actual_guard)
            removal_checks.append(key)

        runtime = SimpleNamespace(factory=factory, storage=SimpleNamespace(root=storage.root, remove_unreferenced=observed_remove))
        assert cleanup_upload(runtime, task_id, guard, writer)
        assert len(removal_checks) == 2
        assert not storage.path(task_id.hex + ".part").exists()
    with factory() as reader:
        current = reader.get(TransferTask, task_id)
        assert current.lease_owner is None and current.stop_confirmed
        assert receiving_count(reader) == baseline
