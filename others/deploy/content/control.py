"""Private fixed-template Docker executor. Never load a business .env in this process."""
from __future__ import annotations

import argparse
import asyncio
from dataclasses import asdict
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time
from uuid import UUID

from output_files import UnsafeOutput, read_output

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "others/backend"))
from app.core.content_runner import (FRAME, MAX_OUTPUT, PROTOCOL, C1_PROTOCOL, TASK_KINDS, json_bytes,  # noqa: E402
                                     read_frame, validate_task, write_frame, task_input_limit,
                                     main_control_configuration)
from app.domains.content.parse_runner import RunnerCapabilities, RunnerUnavailable  # noqa: E402


class Controller:
    def __init__(self, config):
        if (config.get("protocol") not in {PROTOCOL, C1_PROTOCOL} or len(config.get("key", "")) < 32
                or not re.fullmatch("sha256:[0-9a-f]{64}", config.get("image", ""))):
            raise RunnerUnavailable()
        self.config = config
        self.source_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        self.root = Path(config["root"]).resolve(strict=True)
        self.instance = config["instance"]
        if not re.fullmatch("[0-9a-f]{32}", self.instance):
            raise RunnerUnavailable()
        self.tasks, self.journal = self.root / "tasks", self.root / "journal"
        self.tasks.mkdir(mode=0o700, exist_ok=True)
        self.journal.mkdir(mode=0o700, exist_ok=True)
        self.docker = shutil.which("docker")
        if not self.docker:
            raise RunnerUnavailable()
        self.lock = asyncio.Lock()
        self.receivers = {}
        self.result_readers = set()
        self.connections = 0
        # Keep this stable file and handle for the service lifetime; never unlink a lock object.
        self.instance_lock = (self.root / "instance.lock").open("a+b")
        self.instance_lock.write(b"\0")
        self.instance_lock.flush()
        self.instance_lock.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(self.instance_lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(self.instance_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def name(self, execution_id):
        return "labconnect-parse-" + self.instance + "-" + UUID(execution_id).hex

    def directory(self, execution_id):
        path = (self.tasks / str(UUID(execution_id))).resolve()
        if path.parent != self.tasks.resolve() or path == self.tasks.resolve():
            raise RunnerUnavailable()
        return path

    def load(self, execution_id):
        path = self.journal / (str(UUID(execution_id)) + ".json")
        return json.loads(path.read_text()) if path.exists() else None

    def save(self, record):
        target = self.journal / (str(UUID(record["execution_id"])) + ".json")
        temporary = target.with_suffix(".new")
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(record, handle, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(target)
        if os.name == "posix":
            descriptor = os.open(self.journal, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)

    def records(self):
        return [json.loads(path.read_text()) for path in sorted(self.journal.glob("*.json"))]

    @staticmethod
    def docker_environment():
        return {name: value for name, value in os.environ.items() if name.upper() in
                {"PATH", "SYSTEMROOT", "WINDIR", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "TEMP", "TMP"}}

    async def docker_call(self, *arguments, allow_absent=False):
        process = await asyncio.create_subprocess_exec(self.docker, *arguments,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=self.docker_environment())

        async def bounded(stream):
            result = bytearray()
            while chunk := await stream.read(min(16384, FRAME + 1 - len(result))):
                result.extend(chunk)
                if len(result) > FRAME:
                    raise RunnerUnavailable()
            return bytes(result)

        tasks = [asyncio.create_task(bounded(process.stdout)), asyncio.create_task(bounded(process.stderr)),
                 asyncio.create_task(process.wait())]
        try:
            stdout, stderr, code = await asyncio.wait_for(asyncio.gather(*tasks), 12)
            if code:
                if allow_absent and (b"No such object:" in stderr or b"No such container:" in stderr):
                    # Distinguish confirmed absence from an unavailable Docker daemon.
                    await self.docker_call("info", "--format", "{{.ServerVersion}}")
                    return None
                raise RunnerUnavailable()
            return stdout
        except TimeoutError:
            raise RunnerUnavailable() from None
        finally:
            if process.returncode is None:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
            for task in tasks:
                if not task.done():
                    task.cancel()
            # asyncio has no public PIPE close: close transports before wait to avoid a full-pipe deadlock.
            for stream in (process.stdout, process.stderr):
                stream._transport.close()
            await asyncio.gather(*tasks, return_exceptions=True)
            await process.wait()

    async def container(self, execution_id):
        raw = await self.docker_call("inspect", "--type", "container", "--format", "{{json .}}",
                                     self.name(execution_id), allow_absent=True)
        if raw is None:
            return None
        value = json.loads(raw)
        if (value["Image"] != self.config["image"]
                or value["Config"]["Labels"].get("labconnect.parse.instance") != self.instance):
            raise RunnerUnavailable()
        return value

    @staticmethod
    def state(record):
        return {name: record[name] for name in ("execution_id", "state", "stop_confirmed", "output_bytes", "error_code")}

    async def inspect_locked(self, execution_id):
        record = self.load(execution_id)
        if record is None:
            raise RunnerUnavailable()
        if record.get("released"):
            return record
        container = await self.container(execution_id)
        if container is not None and container["State"]["Running"]:
            # The wrapper also enforces 60s; this deadline fences a stalled wrapper/container.
            if time.time() > record.get("parse_deadline", record.get("receive_deadline", 0)):
                record["error_code"] = "TIMEOUT"
                return await self.stop_locked(execution_id, record)
            return record
        record.update(state="stopped" if record.get("stopped") else "failed", stop_confirmed=True)
        if not record.get("stopped"):
            status = self.output(execution_id, "status.json", 4096, missing_ok=True)
            if status is not None:
                result = json.loads(status)
                if (container is not None and container["State"]["ExitCode"] == 0
                        and result == {"state": "succeeded"}):
                    output = self.output(execution_id, "result.json", MAX_OUTPUT)
                    record.update(state="succeeded", output_bytes=len(output), error_code=None)
                else:
                    record["error_code"] = result.get("error_code", "WORKER_INTERRUPTED")
            else:
                record["error_code"] = "WORKER_INTERRUPTED"
        self.save(record)
        return record

    def output(self, execution_id, name, maximum, *, missing_ok=False):
        try:
            return read_output(self.tasks, execution_id, name, maximum, missing_ok=missing_ok)
        except UnsafeOutput:
            raise RunnerUnavailable() from None

    async def stop_locked(self, execution_id, record=None):
        record = record or self.load(execution_id) or {"execution_id": execution_id, "task": None,
            "state": "stopped", "stop_confirmed": False, "output_bytes": 0, "error_code": None}
        record["stopped"] = True
        self.save(record)  # Fence any delayed start before touching the external execution unit.
        container = await self.container(execution_id)
        if container is not None and container["State"]["Running"]:
            await self.docker_call("stop", "--time", "1", self.name(execution_id))
            container = await self.container(execution_id)
        if container is not None and container["State"]["Running"]:
            raise RunnerUnavailable()
        record.update(state="stopped", stop_confirmed=True)
        self.save(record)
        receiver = self.receivers.get(execution_id)
        if receiver and receiver.stdin:
            receiver.stdin.close()
        return record

    async def recover(self):
        actual = (await self.docker_call("image", "inspect", "--format", "{{.Id}}", self.config["image"])).decode().strip()
        if actual != self.config["image"]:
            raise RunnerUnavailable()
        async with self.lock:
            for record in self.records():
                if not record.get("released"):
                    await self.stop_locked(record["execution_id"], record)

    async def capabilities(self):
        await self.docker_call("info", "--format", "{{.ServerVersion}}")
        return asdict(RunnerCapabilities("labconnect.parse/1", self.config["image"], True, True, True, True,
            True, True, True, True, 384 * 1024 * 1024, 1, 64 * 1024 * 1024, 64, 60, MAX_OUTPUT, FRAME))

    async def begin(self, task):
        execution_id = task["execution_id"]
        async with self.lock:
            existing = self.load(execution_id)
            if existing:
                if existing.get("stopped") or existing.get("task") != task or existing.get("receiving"):
                    raise RunnerUnavailable()
                return None
            if any(not record.get("released") for record in self.records()):
                raise RunnerUnavailable()
            record = {"execution_id": execution_id, "task": task, "state": "running", "stop_confirmed": False,
                "output_bytes": 0, "error_code": None, "receiving": True, "receive_deadline": time.time() + 300}
            self.save(record)
            path = self.directory(execution_id)
            path.mkdir(mode=0o700)
            # Linux bind mount is writable only by the fixed sandbox uid; Windows ACL stays host-private.
            if os.name == "posix":
                os.chown(path, 65532, 65532)
            await self.docker_call("create", "--name", self.name(execution_id), "--label",
                "labconnect.parse.instance=" + self.instance, "--label", "labconnect.parse.execution=" + execution_id,
                "--pull=never", "--interactive", "--network=none", "--read-only", "--user=65532:65532",
                "--cap-drop=ALL", "--security-opt=no-new-privileges:true", "--memory=402653184",
                "--memory-swap=402653184", "--cpus=1", "--pids-limit=64", "--log-driver=none",
                # Sealed memfd input <=20MiB plus work tmpfs <=44MiB: total temporary memory <=64MiB.
                "--tmpfs", "/work:rw,noexec,nosuid,nodev,size=46137344,uid=65532,gid=65532,mode=0700",
                "--mount", "type=bind,source=" + str(path) + ",target=/output",
                self.config["image"], task["format"], task.get("encoding", "utf-8"), task["input_sha256"],
                *([task.get("task_kind", "material_parse")] if self.config["protocol"] == C1_PROTOCOL else []))
            process = await asyncio.create_subprocess_exec(self.docker, "start", "--interactive", self.name(execution_id),
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL, env=self.docker_environment())
            self.receivers[execution_id] = process
            # Serialize the actual Docker start, not only its intent, against stop/tombstones.
            for _attempt in range(50):
                container = await self.container(execution_id)
                if container is not None and container["State"]["Running"]:
                    return process
                if process.returncode is not None:
                    break
                await asyncio.sleep(.1)
            await self.stop_locked(execution_id, record)
            raise RunnerUnavailable()

    async def receive(self, task, reader, process):
        execution_id = task["execution_id"]
        digest, size = hashlib.sha256(), 0
        maximum = task_input_limit(task)
        try:
            async with asyncio.timeout(300):
                while True:
                    frame = await read_frame(reader, FRAME)
                    if not frame:
                        break
                    size += len(frame)
                    if size > maximum:
                        raise RunnerUnavailable()
                    digest.update(frame)
                    if process:
                        await write_frame(process.stdin, frame)
                if not size or digest.hexdigest() != task["input_sha256"]:
                    raise RunnerUnavailable()
                if process:
                    await write_frame(process.stdin, b"")
                    process.stdin.close()
                    for _attempt in range(50):
                        accepted = self.output(execution_id, "accepted", 4096, missing_ok=True)
                        if accepted is not None:
                            receipt = json.loads(accepted)
                            expected = {"kernel_seals": 15, "input_bytes": size, "input_sha256": digest.hexdigest()}
                            if "task_kind" in task:
                                expected.update(task_kind=task["task_kind"], work_tmpfs_bytes=46137344)
                            if receipt != expected:
                                raise RunnerUnavailable()
                            break
                        await asyncio.sleep(.1)
                    else:
                        raise RunnerUnavailable()
            async with self.lock:
                record = self.load(execution_id)
                if record.get("stopped"):
                    raise RunnerUnavailable()
                if process:
                    record.update(receiving=False, parse_deadline=time.time() + (30 if "task_kind" in task else 60))
                    record["input_receipt"] = receipt
                    self.save(record)
                return await self.inspect_locked(execution_id)
        except BaseException:
            async with self.lock:
                await self.stop_locked(execution_id)
            raise
        finally:
            if process:
                self.receivers.pop(execution_id, None)

    async def release_locked(self, execution_id):
        if execution_id in self.result_readers:
            return False
        record = await self.stop_locked(execution_id)
        container = await self.container(execution_id)
        if container is not None:
            await self.docker_call("rm", self.name(execution_id))
        if await self.container(execution_id) is not None:
            raise RunnerUnavailable()
        directory = self.directory(execution_id)
        if directory.exists():
            # directory() verifies the absolute target is this instance's exact UUID task child.
            shutil.rmtree(directory)
        if directory.exists():
            return False
        record["released"] = True
        record["receiving"] = False
        self.save(record)
        return True

    async def handle(self, reader, writer):
        if self.connections >= 8:
            writer.close()
            return
        self.connections += 1
        try:
            request = json.loads(await read_frame(reader, 16384, 5))
            if (not isinstance(request, dict) or request.get("protocol") != self.config["protocol"]
                    or not isinstance(request.get("key"), str)
                    or not hmac.compare_digest(request["key"], self.config["key"])):
                raise RunnerUnavailable()
            operation = request.get("operation")
            if operation == "start":
                if set(request) != {"protocol", "key", "operation", "task"}:
                    raise RunnerUnavailable()
                task = validate_task(request["task"])
                if "task_kind" in task and self.config["protocol"] != C1_PROTOCOL:
                    raise RunnerUnavailable()
                process = await self.begin(task)
                try:
                    await write_frame(writer, json_bytes({"ok": True, "ready": True}))
                    record = await self.receive(task, reader, process)
                except BaseException:
                    # Only a start accepted for this exact binding may stop its execution.
                    if self.load(task["execution_id"]):
                        async with self.lock:
                            await self.stop_locked(task["execution_id"])
                    raise
                await write_frame(writer, json_bytes({"ok": True, "state": self.state(record)}))
            elif operation == "capabilities":
                if set(request) != {"protocol", "key", "operation"}:
                    raise RunnerUnavailable()
                await write_frame(writer, json_bytes({"ok": True, "capabilities": await self.capabilities(),
                                                      "controller_sha256": self.source_sha256,
                                                      "task_kinds": list(TASK_KINDS) if self.config["protocol"] == C1_PROTOCOL else ["material_parse"]}))
            elif operation in {"inspect", "stop", "release", "result"}:
                if set(request) != {"protocol", "key", "operation", "execution_id"}:
                    raise RunnerUnavailable()
                execution_id = request["execution_id"]
                if not isinstance(execution_id, str) or str(UUID(execution_id)) != execution_id:
                    raise RunnerUnavailable()
                async with self.lock:
                    if operation == "release":
                        response = {"ok": True, "released": await self.release_locked(execution_id)}
                    else:
                        record = (await self.stop_locked(execution_id) if operation == "stop" else
                                  await self.inspect_locked(execution_id))
                        response = {"ok": True, "state": self.state(record)}
                    if operation == "result":
                        if record["state"] != "succeeded" or record.get("released"):
                            raise RunnerUnavailable()
                        if execution_id in self.result_readers:
                            raise RunnerUnavailable()
                        self.result_readers.add(execution_id)
                if operation == "result":
                    try:
                        output = self.output(execution_id, "result.json", MAX_OUTPUT)
                        await write_frame(writer, json_bytes({"ok": True}))
                        for offset in range(0, len(output), FRAME):
                            await write_frame(writer, output[offset:offset + FRAME])
                        await write_frame(writer, b"")
                    finally:
                        self.result_readers.discard(execution_id)
                else:
                    await write_frame(writer, json_bytes(response))
            else:
                raise RunnerUnavailable()
        except (Exception, asyncio.CancelledError):
            try:
                await write_frame(writer, json_bytes({"ok": False, "error_code": "PARSER_UNAVAILABLE"}))
            except (OSError, TimeoutError):
                pass
        finally:
            self.connections -= 1
            writer.close()


def control_port(config):
    port = 18768 if config["protocol"] == C1_PROTOCOL else 18767
    client = {key: config.get(key) for key in ("protocol", "key", "host", "port")}
    if config["protocol"] == C1_PROTOCOL and config.get("port") == 18767 and main_control_configuration(client):
        port = 18767
    if config.get("host") != "127.0.0.1" or config.get("port") != port:
        raise RunnerUnavailable()
    return port


async def serve(config):
    controller = Controller(config)
    await controller.recover()
    if "socket" in config:
        if os.name == "nt" or not Path(config["socket"]).is_absolute():
            raise RunnerUnavailable()
        path = Path(config["socket"])
        if path.exists():
            if not path.is_socket():
                raise RunnerUnavailable()
            # Never unlink another live controller's socket, even when its installation root differs.
            try:
                _reader, existing = await asyncio.wait_for(asyncio.open_unix_connection(path), 1)
            except ConnectionRefusedError:
                if path.stat().st_uid != os.geteuid():
                    raise RunnerUnavailable() from None
            else:
                existing.close()
                raise RunnerUnavailable()
            path.unlink()
        server = await asyncio.start_unix_server(controller.handle, path=path)
        group = config.get("client_gid")
        if group is not None:
            if type(group) is not int or not 0 <= group <= 2147483647:
                raise RunnerUnavailable()
            os.chown(path, -1, group)
            path.chmod(0o660)
        else:
            path.chmod(0o600)
    else:
        port = control_port(config)
        server = await asyncio.start_server(controller.handle, host="127.0.0.1", port=port)
    print(json.dumps({"protocol": config["protocol"], "ready": True, "image": config["image"]}), flush=True)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    asyncio.run(serve(json.loads(args.config.read_text(encoding="utf-8"))))
