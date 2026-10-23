"""A-owned internal ASR adapter. C must enforce user/course/exam gates around every job/result.

No HTTP business route is registered here. Cloud uses a mounted SSH Unix socket; developer
trees use A's shared loopback config. Neither config nor worker credentials go to a client.
"""
from dataclasses import dataclass, field
import http.client
import json
import os
from pathlib import Path
import re
import socket
import time
from typing import Callable
from uuid import uuid4

PROTOCOL = "labconnect-asr-1"


class AsrError(RuntimeError):
    def __init__(self, code: str, status: int = 503):
        self.code, self.status = code, status
        super().__init__(code)


class UnixConnection(http.client.HTTPConnection):
    def __init__(self, path: str, timeout: float):
        super().__init__("localhost", timeout=timeout)
        self.path = path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self.path)


@dataclass(frozen=True)
class AsrClient:
    config: dict = field(repr=False)
    secret: str = field(repr=False)

    @classmethod
    def from_environment(cls):
        root = Path(os.environ.get("LABCONNECT_SHARED_ROOT", Path(__file__).resolve().parents[4]))
        default = root / "others/runtime/cloud-asr/client.json"
        path = Path(os.environ.get("LABCONNECT_ASR_CONFIG", str(default)))
        try:
            config = json.loads(path.read_text(encoding="utf-8"))
            secret = Path(config["key_file"]).read_text(encoding="utf-8").strip()
            if (config["protocol"] != PROTOCOL or not re.fullmatch(r"[A-Za-z0-9_-]{43,128}", secret)
                    or config["transport"] not in {"loopback", "unix"}):
                raise ValueError()
            if config["transport"] == "unix" and not re.fullmatch(
                    r"/run/labconnect-asr/tunnel-[0-9a-f]{32}\.sock", config["socket_path"]):
                raise ValueError()
            if config["transport"] == "loopback" and not 1024 <= int(config["port"]) <= 65535:
                raise ValueError()
            return cls(config, secret)
        except (OSError, ValueError, KeyError, TypeError):
            raise AsrError("asr_unconfigured") from None

    def request(self, method: str, path: str, data: bytes | None = None, *, timeout: float = 3,
                headers: dict | None = None) -> dict:
        connection = (UnixConnection(self.config["socket_path"], timeout) if self.config["transport"] == "unix"
                      else http.client.HTTPConnection("127.0.0.1", int(self.config["port"]), timeout=timeout))
        try:
            connection.request(method, path, data, headers={"Authorization": "Bearer " + self.secret,
                "Content-Type": "audio/wav", **(headers or {})})
            response = connection.getresponse()
            raw = response.read(65537)
            if len(raw) > 65536:
                raise AsrError("asr_protocol")
            value = json.loads(raw)
            if response.status >= 400:
                code = value.get("error", "asr_protocol")
                raise AsrError(code if re.fullmatch(r"[a-z_]{1,64}", code) else "asr_protocol", response.status)
            return value
        except (OSError, http.client.HTTPException):
            raise AsrError("asr_unavailable") from None
        except (ValueError, TypeError):
            raise AsrError("asr_protocol") from None
        finally:
            connection.close()

    def health(self):
        value = self.request("GET", "/v1/health")
        if (value.get("protocol") != PROTOCOL or value.get("status") != "ready"
                or any(value.get(key) != self.config[key] for key in ("instance_id", "source_sha", "worker_fingerprint"))):
            raise AsrError("asr_identity_mismatch")
        return value

    def submit(self, audio: bytes, *, timeout_seconds: float = 15, job_id: str | None = None):
        if len(audio) > 964096:
            raise AsrError("audio_size", 413)
        key = job_id or str(uuid4())
        self.request("POST", "/v1/jobs/" + key, audio,
                     headers={"X-ASR-Timeout-Seconds": str(timeout_seconds)})
        return key

    def result(self, job_id: str):
        return self.request("GET", "/v1/jobs/" + job_id)

    def cancel(self, job_id: str):
        return self.request("DELETE", "/v1/jobs/" + job_id)

    def transcribe(self, audio: bytes, *, timeout_seconds: float = 15,
                   cancelled: Callable[[], bool] = lambda: False) -> str:
        if not 0.05 <= timeout_seconds <= 30:
            raise AsrError("deadline", 400)
        if cancelled():
            raise AsrError("asr_canceled", 409)
        self.health()
        key = str(uuid4())
        deadline = time.monotonic() + timeout_seconds
        try:
            self.submit(audio, timeout_seconds=timeout_seconds, job_id=key)
            while True:
                if cancelled():
                    raise AsrError("asr_canceled", 409)
                if time.monotonic() >= deadline:
                    raise AsrError("inference_timeout", 504)
                result = self.result(key)
                if result["state"] == "succeeded":
                    if not isinstance(result.get("text"), str):
                        raise AsrError("asr_protocol")
                    return result["text"]
                if result["state"] != "running":
                    raise AsrError(result.get("error", "inference_failed"), 504 if result["state"] == "timed_out" else 503)
                time.sleep(0.05)
        finally:
            try:
                self.cancel(key)
            except AsrError:
                pass  # Worker deadline and 60-second result TTL remain the fallback after a disconnected tunnel.
