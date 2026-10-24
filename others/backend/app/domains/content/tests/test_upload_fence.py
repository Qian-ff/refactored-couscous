import asyncio
import json
import os
import queue
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from uuid import uuid4

from app.domains.content.storage import PrivateStorage
from app.domains.content.upload_fence import FenceUnavailable, UploadFence
from app.domains.content.uploads import _io


class FenceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.fence = UploadFence(self.root)
        self.upload = uuid4()

    def acquired(self):
        result = self.fence.try_acquire(self.upload)
        self.assertEqual(result.status, "acquired")
        self.addCleanup(result.guard.close)
        return result.guard

    def test_same_process_independent_handles_exclude_and_lock_file_stays(self):
        first = self.acquired()
        lock_identity = first.path.stat().st_ino
        self.assertEqual(self.fence.try_acquire(self.upload).status, "busy")
        first.close()
        self.assertTrue(first.path.exists())
        second = self.acquired()
        self.assertEqual(second.path.stat().st_ino, lock_identity)

    def test_storage_rejects_wrong_or_closed_guard(self):
        storage = PrivateStorage(self.root)
        guard = self.acquired()
        with self.assertRaises(FenceUnavailable):
            storage.create(uuid4().hex + ".part", guard)
        guard.close()
        with self.assertRaises(FenceUnavailable):
            storage.create(self.upload.hex + ".part", guard)

    def child(self):
        environment = {key: value for key, value in os.environ.items() if key.upper() in {
            "SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "LANG", "LC_ALL"}}
        child = subprocess.Popen([sys.executable, "-m", "app.domains.content.tests.fence_child",
                                  "--root", str(self.root), "--upload", str(self.upload)],
                                 cwd=Path(__file__).resolve().parents[4], env=environment,
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                 creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)

        def dispose():
            if child.poll() is None:
                child.kill()
            child.wait(timeout=10)
            child.stdin.close()
            child.stdout.close()
        self.addCleanup(dispose)
        result = queue.Queue(maxsize=1)
        threading.Thread(target=lambda: result.put(child.stdout.readline(4096)), daemon=True).start()
        line = result.get(timeout=10)
        self.assertTrue(line, "owned lock helper did not report readiness")
        return child, json.loads(line)

    def test_distinct_process_observes_cleaner_lock(self):
        self.acquired()
        child, state = self.child()
        self.assertEqual(state["status"], "busy")
        self.assertEqual(child.wait(timeout=5), 0)

    def test_frozen_holder_keeps_lock_until_process_termination(self):
        child, state = self.child()
        self.assertEqual(state["status"], "acquired")
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.OpenThread.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            kernel.OpenThread.restype = wintypes.HANDLE
            kernel.SuspendThread.argtypes = [wintypes.HANDLE]
            kernel.SuspendThread.restype = wintypes.DWORD
            kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel.CloseHandle.restype = wintypes.BOOL
            handle = kernel.OpenThread(2, False, state["thread_id"])
            self.assertTrue(handle)
            try:
                self.assertNotEqual(kernel.SuspendThread(handle), 0xFFFFFFFF)
            finally:
                kernel.CloseHandle(handle)
        else:
            os.kill(child.pid, signal.SIGSTOP)
        self.assertEqual(self.fence.try_acquire(self.upload).status, "busy")
        child.kill()
        child.wait(timeout=10)
        deadline = time.monotonic() + 5
        while True:
            recovered = self.fence.try_acquire(self.upload)
            if recovered.status == "acquired":
                recovered.guard.close()
                break
            self.assertEqual(recovered.status, "busy")
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.05)


class CancellationFenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_cancel_does_not_unlock_while_actual_thread_still_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            storage, upload = PrivateStorage(Path(directory)), uuid4()
            attempt = storage.fence.try_acquire(upload)
            self.assertEqual(attempt.status, "acquired")
            guard = attempt.guard
            entered, release = threading.Event(), threading.Event()

            def write():
                with storage.create(upload.hex + ".part", guard) as file:
                    entered.set()
                    release.wait(3)
                    file.write(b"finished")
                    storage.flush(file, guard)

            async def owner():
                try:
                    await _io(write)
                finally:
                    guard.close()

            task = asyncio.create_task(owner())
            try:
                self.assertTrue(await asyncio.to_thread(entered.wait, 2))
                task.cancel()
                await asyncio.sleep(0)
                self.assertEqual(storage.fence.try_acquire(upload).status, "busy")
            finally:
                release.set()
            with self.assertRaises(asyncio.CancelledError):
                await task
            recovered = storage.fence.try_acquire(upload)
            self.assertEqual(recovered.status, "acquired")
            with recovered.guard:
                with storage.open(upload.hex + ".part") as file:
                    self.assertEqual(file.read(), b"finished")
                storage.remove_unreferenced(upload.hex + ".part", recovered.guard)


if __name__ == "__main__":
    unittest.main()
