"""Private framed adapter. The API has no Docker socket, command, image or mount control."""
from __future__ import annotations

import asyncio
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
from uuid import UUID

from app.domains.content.parse_runner import ExecutionState, RunnerCapabilities, RunnerUnavailable

PROTOCOL = "labconnect.parse-control/1"
C1_PROTOCOL = "labconnect.content-control/2"
TASK_KINDS = ("material_parse", "question_import", "question_export")
FRAME = 65536
MAX_INPUT = 20 * 1024 * 1024
MAX_OUTPUT = 16 * 1024 * 1024


def main_control_configuration(configuration):
    """Only the actual primary/main may bind the v2 protocol to the original port."""
    root = Path(__file__).resolve().parents[4]
    try:
        common = subprocess.check_output(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
                                         cwd=root, text=True, stderr=subprocess.DEVNULL).strip()
        branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=root,
                                         text=True, stderr=subprocess.DEVNULL).strip()
        return (Path(common).resolve().parent == root and branch == "main"
                and configuration == json.loads((root / "others/runtime/content-parser/parser-client.json").read_text()))
    except (OSError, ValueError, subprocess.CalledProcessError):
        return False


async def read_frame(reader, maximum, timeout=30):
    length = struct.unpack(">I", await asyncio.wait_for(reader.readexactly(4), timeout))[0]
    if length > maximum:
        raise RunnerUnavailable()
    return await asyncio.wait_for(reader.readexactly(length), timeout)


async def write_frame(writer, body):
    writer.write(struct.pack(">I", len(body)) + body)
    await asyncio.wait_for(writer.drain(), 30)


def json_bytes(value):
    return json.dumps(value, separators=(",", ":"), ensure_ascii=True).encode()


def validate_task(value):
    if isinstance(value, dict) and "task_kind" in value:
        expected = {"task_kind", "task_id", "execution_id", "generation", "input_sha256", "format"}
        if set(value) != expected or value["task_kind"] not in TASK_KINDS[1:] or value["format"] not in {"csv", "xlsx"}:
            raise RunnerUnavailable()
        for name in ("task_id", "execution_id"):
            if not isinstance(value[name], str) or str(UUID(value[name])) != value[name]:
                raise RunnerUnavailable()
        if (type(value["generation"]) is not int or value["generation"] < 1
                or not isinstance(value["input_sha256"], str) or not re.fullmatch("[0-9a-f]{64}", value["input_sha256"])):
            raise RunnerUnavailable()
        return value
    expected = {"execution_id", "job_id", "version_id", "generation", "input_sha256", "format", "encoding"}
    if not isinstance(value, dict) or set(value) != expected:
        raise RunnerUnavailable()
    for name in ("execution_id", "job_id", "version_id"):
        if not isinstance(value[name], str) or str(UUID(value[name])) != value[name]:
            raise RunnerUnavailable()
    if (type(value["generation"]) is not int or value["generation"] < 1
            or not isinstance(value["input_sha256"], str)
            or not re.fullmatch("[0-9a-f]{64}", value["input_sha256"])
            or value["format"] not in {"pdf", "pptx", "docx", "txt", "text"}
            or value["encoding"] not in {"utf-8", "gb18030"}):
        raise RunnerUnavailable()
    return value


def task_input_limit(task):
    kind = task.get("task_kind", "material_parse")
    if kind == "question_export":
        return MAX_OUTPUT
    if kind == "question_import":
        return 1048576 if task["format"] == "csv" else 5242880
    return 1048576 if task["format"] in {"txt", "text"} else MAX_INPUT


class DockerParseRunner:
    def __init__(self, configuration: dict):
        if (set(configuration) - {"protocol", "key", "host", "port", "socket"}
                or configuration.get("protocol") not in {PROTOCOL, C1_PROTOCOL}
                or not isinstance(configuration.get("key"), str) or len(configuration["key"]) < 32):
            raise RunnerUnavailable()
        if "socket" in configuration:
            if "host" in configuration or "port" in configuration or not Path(configuration["socket"]).is_absolute():
                raise RunnerUnavailable()
        else:
            port = configuration.get("port")
            expected = 18768 if configuration["protocol"] == C1_PROTOCOL else 18767
            main_v2 = (configuration["protocol"] == C1_PROTOCOL and port == 18767
                       and main_control_configuration(configuration))
            if configuration.get("host") != "127.0.0.1" or (port != expected and not main_v2):
                raise RunnerUnavailable()
        self.configuration = configuration

    async def _open(self, operation, **fields):
        settings = self.configuration
        connect = (asyncio.open_unix_connection(settings["socket"]) if "socket" in settings else
                   asyncio.open_connection(settings["host"], settings["port"]))
        reader, writer = await asyncio.wait_for(connect, 5)
        request = json_bytes({"protocol": settings["protocol"], "key": settings["key"], "operation": operation, **fields})
        if len(request) > 16384:
            writer.close()
            raise RunnerUnavailable()
        try:
            await write_frame(writer, request)
        except BaseException:
            writer.close()
            raise
        return reader, writer

    @staticmethod
    async def _response(reader):
        value = json.loads(await read_frame(reader, FRAME))
        if not isinstance(value, dict) or value.get("ok") is not True:
            raise RunnerUnavailable()
        return value

    @staticmethod
    def _state(value, execution_id):
        state = value["state"]
        if (set(state) != {"execution_id", "state", "stop_confirmed", "output_bytes", "error_code"}
                or state["execution_id"] != str(execution_id)
                or state["state"] not in {"running", "succeeded", "failed", "stopped"}
                or type(state["stop_confirmed"]) is not bool
                or type(state["output_bytes"]) is not int or not 0 <= state["output_bytes"] <= MAX_OUTPUT
                or state["error_code"] not in {None, "TIMEOUT", "RESOURCE_LIMIT", "WORKER_INTERRUPTED",
                    "INVALID_RESULT", "CORRUPT_FILE", "INVALID_ENCODING", "ENCRYPTED_FILE", "NO_TEXT",
                    "UNSUPPORTED_TYPE", "UNSUPPORTED_ENCODING"}):
            raise RunnerUnavailable()
        return ExecutionState(**{**state, "execution_id": UUID(state["execution_id"])})

    async def _call(self, operation, execution_id=None):
        writer = None
        try:
            fields = {} if execution_id is None else {"execution_id": str(execution_id)}
            reader, writer = await self._open(operation, **fields)
            value = await self._response(reader)
            if operation == "capabilities":
                if self.configuration["protocol"] == C1_PROTOCOL and value.get("task_kinds") != list(TASK_KINDS):
                    raise RunnerUnavailable()
                capabilities = RunnerCapabilities(**value["capabilities"])
                capabilities.require_supported()
                return capabilities
            if operation == "release":
                return value.get("released") is True
            if operation == "result":
                output = bytearray()
                while True:
                    frame = await read_frame(reader, FRAME)
                    if not frame:
                        return bytes(output)
                    if len(output) + len(frame) > MAX_OUTPUT:
                        raise RunnerUnavailable()
                    output.extend(frame)
            return self._state(value, execution_id)
        except (OSError, TimeoutError, ValueError, TypeError, KeyError, asyncio.IncompleteReadError):
            raise RunnerUnavailable() from None
        finally:
            if writer:
                writer.close()

    async def capabilities(self):
        return await self._call("capabilities")

    async def inspect(self, execution_id):
        return await self._call("inspect", execution_id)

    async def stop(self, execution_id):
        return await self._call("stop", execution_id)

    async def release(self, execution_id):
        return await self._call("release", execution_id)

    async def result(self, execution_id):
        return await self._call("result", execution_id)

    async def start(self, task, source):
        writer = None
        try:
            specification = {key: str(value) if isinstance(value, UUID) else value for key, value in asdict(task).items()}
            validate_task(specification)
            reader, writer = await self._open("start", task=specification)
            if (await self._response(reader)).get("ready") is not True:
                raise RunnerUnavailable()
            size, digest = 0, hashlib.sha256()
            async for data in source:
                if not isinstance(data, bytes):
                    raise RunnerUnavailable()
                size += len(data)
                if size > task_input_limit(specification):
                    raise RunnerUnavailable()
                digest.update(data)
                for offset in range(0, len(data), FRAME):
                    await write_frame(writer, data[offset:offset + FRAME])
            if size == 0 or digest.hexdigest() != task.input_sha256:
                raise RunnerUnavailable()
            await write_frame(writer, b"")
            return self._state(await self._response(reader), task.execution_id)
        except (OSError, TimeoutError, ValueError, TypeError, KeyError, asyncio.IncompleteReadError):
            raise RunnerUnavailable() from None
        finally:
            if writer:
                writer.close()
