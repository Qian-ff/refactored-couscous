"""Native OS output-handle and real child-pipe regression; no production service is touched."""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from control import Controller, FRAME, MAX_OUTPUT, PROTOCOL, RunnerUnavailable, json_bytes
from output_files import UnsafeOutput, read_output


class Writer:
    def __init__(self):
        self.data = bytearray()

    def write(self, data):
        self.data.extend(data)

    async def drain(self):
        pass

    def close(self):
        pass


class OutputTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.tasks = self.root / "tasks"
        self.tasks.mkdir()
        self.execution = str(uuid4())
        self.directory = self.tasks / self.execution
        self.directory.mkdir()
        self.marker = b"synthetic-private-host-data-outside-task"
        self.outside = self.root / "private.json"
        self.outside.write_text(json.dumps({"protocol": "labconnect.parse/1", "format": "txt", "parser_version": "test/1",
            "chunks": [{"ordinal": 1, "locator": {"kind": "paragraph", "position": 1, "part": 1},
                        "text": self.marker.decode(), "text_hash": hashlib.sha256(self.marker).hexdigest()}], "warnings": []}))

    def read(self, name="result.json", maximum=4096):
        return read_output(self.tasks, self.execution, name, maximum)

    def controller(self):
        controller = object.__new__(Controller)
        controller.tasks = self.tasks
        controller.journal = self.root / "journal"
        controller.journal.mkdir()
        controller.config = {"key": "synthetic-only-" + "x" * 32}
        controller.connections = 0
        controller.lock = asyncio.Lock()
        controller.result_readers = set()
        controller.receivers = {}
        controller.save({"execution_id": self.execution, "state": "running", "stop_confirmed": False,
                         "output_bytes": 0, "error_code": None})
        async def exited(_execution):
            return {"State": {"Running": False, "ExitCode": 0}}
        controller.container = exited
        return controller

    async def result_request(self, controller, writer=None):
        request = json_bytes({"protocol": PROTOCOL, "key": controller.config["key"],
                              "operation": "result", "execution_id": self.execution})
        reader = asyncio.StreamReader()
        reader.feed_data(struct.pack(">I", len(request)) + request)
        reader.feed_eof()
        writer = writer or Writer()
        await controller.handle(reader, writer)
        return bytes(writer.data)

    def normal_files(self):
        (self.directory / "status.json").write_text('{"state":"succeeded"}')
        (self.directory / "result.json").write_bytes(b'{"chunks":[]}')

    async def test_normal_result_and_release_exclusion(self):
        self.normal_files()
        controller = self.controller()
        started, resume = asyncio.Event(), asyncio.Event()
        class HeldWriter(Writer):
            async def drain(self):
                started.set()
                await resume.wait()
        writer = HeldWriter()
        pending = asyncio.create_task(self.result_request(controller, writer))
        await asyncio.wait_for(started.wait(), 2)
        try:
            self.assertIn(self.execution, controller.result_readers)
            self.assertFalse(await controller.release_locked(self.execution))
        finally:
            resume.set()
        result = await pending
        self.assertIn(b'{"chunks":[]}', result)
        self.assertFalse(controller.result_readers)
        self.assertEqual(controller.load(self.execution)["state"], "succeeded")

    async def test_external_result_symlink_is_not_returned(self):
        self.normal_files()
        (self.directory / "result.json").unlink()
        (self.directory / "result.json").symlink_to(self.outside)
        data = await self.result_request(self.controller())
        self.assertNotIn(self.marker, data)
        self.assertIn(b'"ok":false', data)

    async def test_result_replacement_after_inspect_is_revalidated(self):
        self.normal_files()
        controller = self.controller()
        output = controller.output
        count = 0
        def replace(execution, name, maximum, **kwargs):
            nonlocal count
            if name == "result.json":
                count += 1
                if count == 2:
                    (self.directory / name).unlink()
                    (self.directory / name).symlink_to(self.outside)
            return output(execution, name, maximum, **kwargs)
        controller.output = replace
        data = await self.result_request(controller)
        self.assertEqual(count, 2)
        self.assertNotIn(self.marker, data)
        self.assertIn(b'"ok":false', data)
        self.assertFalse(controller.result_readers)

    def test_symlinks_all_consumed_names(self):
        for name in ("result.json", "status.json", "accepted"):
            with self.subTest(name=name):
                path = self.directory / name
                path.symlink_to(self.outside)
                with self.assertRaises(UnsafeOutput):
                    self.read(name)

    def test_hardlinks_all_consumed_names(self):
        for name in ("result.json", "status.json", "accepted"):
            with self.subTest(name=name):
                os.link(self.outside, self.directory / name)
                with self.assertRaises(UnsafeOutput):
                    self.read(name)

    def test_fifo_without_waiting_for_writer(self):
        if os.name != "posix":
            self.skipTest("FIFO is a POSIX file type; Windows reparse tests cover native redirection")
        for name in ("result.json", "status.json", "accepted"):
            with self.subTest(name=name):
                os.mkfifo(self.directory / name)
                with self.assertRaises(UnsafeOutput):
                    self.read(name)

    def test_device_without_reading(self):
        if os.name != "posix":
            self.skipTest("POSIX device node; Windows uses disk-only handle validation")
        os.mknod(self.directory / "result.json", stat.S_IFCHR | 0o600, os.makedev(1, 3))
        with self.assertRaises(UnsafeOutput):
            self.read()

    def test_parent_reparse_or_symlink(self):
        self.directory.rmdir()
        external = self.root / "outside"
        external.mkdir()
        (external / "result.json").write_bytes(self.marker)
        self.directory.symlink_to(external, target_is_directory=True)
        with self.assertRaises(UnsafeOutput):
            self.read()

    def test_same_open_handle_under_name_replacement(self):
        path = self.directory / "result.json"
        path.write_bytes(b"normal-result")
        fstat = os.fstat
        replaced = False
        def swap(descriptor):
            nonlocal replaced
            value = fstat(descriptor)
            if not replaced:
                replaced = True
                try:
                    os.replace(self.outside, path)
                except PermissionError:
                    # Windows disallows deleting/replacing the pinned, non-delete-shared leaf.
                    self.assertEqual(os.name, "nt")
            return value
        with patch("output_files.os.fstat", side_effect=swap):
            try:
                value = self.read()
            except UnsafeOutput:
                value = b""
        self.assertNotIn(self.marker, value)
        self.assertTrue(replaced)

    def test_size_cap_empty_missing_and_directory(self):
        path = self.directory / "result.json"
        for data in (b"", b"x" * 4097):
            path.write_bytes(data)
            with self.assertRaises(UnsafeOutput):
                self.read()
        path.unlink()
        self.assertIsNone(read_output(self.tasks, self.execution, "result.json", 4096, missing_ok=True))
        path.mkdir()
        with self.assertRaises(UnsafeOutput):
            self.read()

    def test_normal_status_receipt_and_full_result(self):
        for name, data, maximum in (("status.json", b'{"state":"failed"}', 4096),
                                    ("accepted", b'{"kernel_seals":15}', 4096),
                                    ("result.json", b"x" * MAX_OUTPUT, MAX_OUTPUT)):
            (self.directory / name).write_bytes(data)
            self.assertEqual(hashlib.sha256(self.read(name, maximum)).digest(), hashlib.sha256(data).digest())


class DockerPipeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.controller = object.__new__(Controller)
        self.controller.docker = sys.executable

    async def test_fragmented_stdout_is_complete(self):
        data = await self.controller.docker_call("-c", "import os,time;os.write(1,b'{');time.sleep(.15);os.write(1,b'\"ok\":true}')")
        self.assertEqual(data, b'{"ok":true}')

    async def test_fragmented_stderr_missing_requires_healthy_daemon(self):
        create = asyncio.create_subprocess_exec
        health = []
        async def execute(binary, *args, **kwargs):
            if args[0] == "info":
                health.append(True)
                args = ("-c", "print('29.9.2')")
            return await create(binary, *args, **kwargs)
        with patch("control.asyncio.create_subprocess_exec", side_effect=execute):
            value = await self.controller.docker_call("-c", "import os,time;os.write(2,b'No ');time.sleep(.15);os.write(2,b'such container: synthetic');raise SystemExit(1)", allow_absent=True)
        self.assertIsNone(value)
        self.assertEqual(health, [True])
        with self.assertRaises(RunnerUnavailable):
            await self.controller.docker_call("-c", "import os;os.write(2,b'No such object: synthetic');raise SystemExit(1)", allow_absent=True)

    async def test_both_pipe_limits_and_child_reaping(self):
        create = asyncio.create_subprocess_exec
        children = []
        async def execute(*args, **kwargs):
            process = await create(*args, **kwargs)
            children.append(process)
            return process
        with patch("control.asyncio.create_subprocess_exec", side_effect=execute):
            for pipe in (1, 2):
                with self.subTest(pipe=pipe), self.assertRaises(RunnerUnavailable):
                    await asyncio.wait_for(self.controller.docker_call("-c", f"import os,time;os.write({pipe},b'x'*{FRAME});time.sleep(.1);os.write({pipe},b'x'*{FRAME * 8});time.sleep(30)"), 5)
        self.assertTrue(all(child.returncode is not None for child in children))

    async def test_timeout_reaps_child(self):
        create = asyncio.create_subprocess_exec
        children = []
        async def execute(*args, **kwargs):
            process = await create(*args, **kwargs)
            children.append(process)
            return process
        with patch("control.asyncio.create_subprocess_exec", side_effect=execute), self.assertRaises(RunnerUnavailable):
            await self.controller.docker_call("-c", "import time;time.sleep(30)")
        self.assertEqual(len(children), 1)
        self.assertIsNotNone(children[0].returncode)


if __name__ == "__main__":
    unittest.main(verbosity=2)
