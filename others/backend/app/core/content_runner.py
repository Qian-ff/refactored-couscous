"""Private framed adapter. The API has no Docker socket, command, image or mount control."""
from __future__ import annotations

import asyncio
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import re
import struct
from uuid import UUID

from app.domains.content.parse_runner import ExecutionState, RunnerCapabilities, RunnerUnavailable

PROTOCOL = "labconnect.parse-control/1"
FRAME = 65536
MAX_INPUT = 20 * 1024 * 1024
MAX_OUTPUT = 16 * 1024 * 1024


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


class DockerParseRunner:
    def __init__(self, configuration: dict):
        if (set(configuration) - {"protocol", "key", "host", "port", "socket"}
                or configuration.get("protocol") != PROTOCOL
                or not isinstance(configuration.get("key"), str) or len(configuration["key"]) < 32):
            raise RunnerUnavailable()
        if "socket" in configuration:
            if "host" in configuration or "port" in configuration or not Path(configuration["socket"]).is_absolute():
                raise RunnerUnavailable()
        elif configuration.get("host") != "127.0.0.1" or configuration.get("port") != 18767:
            raise RunnerUnavailable()
        self.configuration = configuration

    async def _open(self, operation, **fields):
        settings = self.configuration
        connect = (asyncio.open_unix_connection(settings["socket"]) if "socket" in settings else
                   asyncio.open_connection(settings["host"], settings["port"]))
        reader, writer = await asyncio.wait_for(connect, 5)
        request = json_bytes({"protocol": PROTOCOL, "key": settings["key"], "operation": operation, **fields})
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
                if size > (1024 * 1024 if task.format in {"text", "txt"} else MAX_INPUT):
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
