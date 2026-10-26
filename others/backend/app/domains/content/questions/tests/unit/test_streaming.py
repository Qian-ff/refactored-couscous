import hashlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from fastapi import HTTPException

from app.domains.content.questions import streaming
from app.domains.content.storage import PrivateStorage


async def pieces(data):
    yield data[:4]
    yield data[4:]


def stored(storage, task_id, data):
    with storage.fence.try_acquire(task_id).guard as guard:
        with storage.create(task_id.hex + ".part", guard) as output:
            output.write(data)
            storage.flush(output, guard)
        storage.seal(task_id.hex + ".part", task_id.hex + ".blob", guard)


class LocalStreamingTests(unittest.IsolatedAsyncioTestCase):
    async def test_upload_writes_the_exact_file_and_seals_before_finish(self):
        with tempfile.TemporaryDirectory() as directory:
            storage = PrivateStorage(Path(directory))
            runtime = SimpleNamespace(storage=storage, factory=None)
            task_id, data = uuid4(), b"sample CSV bytes"
            snapshot = {"generation": 1, "expected_bytes": len(data), "input_hash": hashlib.sha256(data).hexdigest(),
                        "format": "csv", "file_key": task_id.hex + ".blob"}

            def finish(*_args):
                self.assertEqual(storage.path(snapshot["file_key"]).read_bytes(), data)
                self.assertFalse(storage.path(task_id.hex + ".part").exists())
                return {"task_id": str(task_id), "state": "queued", "generation": 1}

            with patch.object(streaming, "_check"), patch.object(streaming, "_claim", return_value=snapshot), \
                 patch.object(streaming, "_heartbeat"), patch.object(streaming, "_finish", side_effect=finish), \
                 patch.object(streaming, "cleanup_upload"):
                result = await streaming.receive(runtime, (), task_id, pieces(data))
            self.assertEqual(result["state"], "queued")

    async def test_wrong_upload_hash_never_seals_and_closes_before_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            storage = PrivateStorage(Path(directory))
            runtime, task_id = SimpleNamespace(storage=storage, factory=None), uuid4()
            snapshot = {"generation": 1, "expected_bytes": 5, "input_hash": "a" * 64,
                        "format": "csv", "file_key": task_id.hex + ".blob"}

            def cleanup(_runtime, _task_id, guard, _writer):
                storage.remove_unreferenced(task_id.hex + ".part", guard)

            with patch.object(streaming, "_check"), patch.object(streaming, "_claim", return_value=snapshot), \
                 patch.object(streaming, "cleanup_upload", side_effect=cleanup), self.assertRaises(HTTPException) as wrong:
                await streaming.receive(runtime, (), task_id, pieces(b"wrong"))
            self.assertEqual(wrong.exception.status_code, 409)
            self.assertFalse(storage.path(task_id.hex + ".blob").exists())
            self.assertFalse(storage.path(task_id.hex + ".part").exists())

    async def test_download_verifies_file_and_rechecks_access_between_chunks(self):
        with tempfile.TemporaryDirectory() as directory:
            storage, task_id, data = PrivateStorage(Path(directory)), uuid4(), b"x" * 600000
            stored(storage, task_id, data)
            runtime = SimpleNamespace(storage=storage, factory=None)
            ticket = {"file_key": task_id.hex + ".blob", "expected_bytes": len(data), "expected_hash": hashlib.sha256(data).hexdigest(),
                      "mime": "text/csv; charset=utf-8", "filename": "labconnect-questions.csv"}
            with patch.object(streaming, "_download_ticket", return_value=ticket) as authorization:
                response = await streaming.download(runtime, (), task_id)
                received = b"".join([chunk async for chunk in response.body_iterator])
                self.assertEqual(received, data)
                self.assertGreaterEqual(authorization.call_count, 4)
                self.assertEqual(response.headers["content-length"], str(len(data)))
            with patch.object(streaming, "_download_ticket", side_effect=[ticket, ticket, HTTPException(403, "revoked")]):
                response = await streaming.download(runtime, (), task_id)
                received = b"".join([chunk async for chunk in response.body_iterator])
                self.assertEqual(len(received), 262144)
                self.assertLess(len(received), int(response.headers["content-length"]))


if __name__ == "__main__":
    unittest.main()
