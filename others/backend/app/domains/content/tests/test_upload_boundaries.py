import asyncio
import tempfile
import threading
import unittest
from pathlib import Path
from time import monotonic
from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import ValidationError

from app.domains.content.schemas import UploadCreate
from app.domains.content.storage import PrivateStorage
from app.domains.content.uploads import _io, _next_chunk


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.storage = PrivateStorage(Path(self.directory.name))

    def test_sealed_file_exact_bytes_and_no_replacement(self):
        key = uuid4().hex
        attempt = self.storage.fence.try_acquire(UUID(hex=key))
        self.assertEqual(attempt.status, "acquired")
        guard = attempt.guard
        self.addCleanup(guard.close)
        data = "中文实验安全".encode()
        with self.storage.create(key + ".part", guard) as file:
            file.write(data)
            self.storage.flush(file, guard)
        self.storage.seal(key + ".part", key + ".blob", guard)
        with self.storage.open(key + ".blob") as file:
            self.assertEqual(file.read(), data)
        self.assertFalse(self.storage.path(key + ".part").exists())
        with self.storage.create(key + ".part", guard) as file:
            file.write(b"replacement")
        with self.assertRaises(FileExistsError):
            self.storage.seal(key + ".part", key + ".blob", guard)
        with self.storage.open(key + ".blob") as file:
            self.assertEqual(file.read(), data)

    def test_opaque_keys_cannot_escape_root(self):
        for key in ("../private", "/private", "C:\\private", uuid4().hex + ".exe"):
            with self.subTest(key=key), self.assertRaises(HTTPException):
                self.storage.path(key)

    def test_upload_input_type_and_name(self):
        base = dict(library_id=uuid4(), title="Safety", original_name="safe.txt", format="txt",
                    expected_hash="a" * 64, expected_bytes=100)
        UploadCreate(**base)
        for change in ({"original_name": "../safe.txt"}, {"original_name": "safe.docm"},
                       {"expected_bytes": 1048577}, {"expected_hash": "not-a-hash"}):
            with self.subTest(change=change), self.assertRaises(ValidationError):
                UploadCreate(**(base | change))


class ThreadCancellationTests(unittest.IsolatedAsyncioTestCase):
    async def test_network_wait_renews_lease_before_idle_timeout(self):
        release = asyncio.Event()
        renewals = []

        async def source():
            await release.wait()
            yield b"chunk"

        async def heartbeat():
            renewals.append(True)
            release.set()

        chunk = await asyncio.wait_for(_next_chunk(aiter(source()), monotonic() + 10, heartbeat), 8)
        self.assertEqual(chunk, b"chunk")
        self.assertEqual(renewals, [True])

    async def test_cancel_waits_for_real_write_completion(self):
        entered, release, finished = threading.Event(), threading.Event(), threading.Event()

        def write():
            entered.set()
            release.wait(3)
            finished.set()

        task = asyncio.create_task(_io(write))
        try:
            self.assertTrue(await asyncio.to_thread(entered.wait, 2))
            task.cancel()
            await asyncio.sleep(0)
            self.assertFalse(task.done())
        finally:
            release.set()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertTrue(finished.is_set())

    async def test_cancel_disposes_created_handle(self):
        entered, release = threading.Event(), threading.Event()
        disposed = []

        def create():
            entered.set()
            release.wait(3)
            return "synthetic-handle"

        task = asyncio.create_task(_io(create, dispose_on_cancel=disposed.append))
        try:
            self.assertTrue(await asyncio.to_thread(entered.wait, 2))
            task.cancel()
            await asyncio.sleep(0)
        finally:
            release.set()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(disposed, ["synthetic-handle"])


if __name__ == "__main__":
    unittest.main()
