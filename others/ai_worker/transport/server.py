"""Private loopback ASR service: one child at a time, bounded lifetime, memory-only audio/results."""
import argparse
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import math
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import threading
import time
from uuid import UUID
import wave

PROTOCOL = "labconnect-asr-1"
MAX_SECONDS = 30
MAX_BYTES = 16000 * 2 * MAX_SECONDS + 4096
RESULT_TTL = 60


def source_fingerprint():
    root = Path(__file__).resolve().parents[1]
    digest = hashlib.sha256()
    names = ["pyproject.toml", "uv.lock", "models.lock.json"]
    names += [p.relative_to(root).as_posix() for p in (root / "transport").glob("*.py")]
    for name in sorted(names):
        digest.update(name.encode() + b"\0" + (root / name).read_bytes() + b"\0")
    return digest.hexdigest()


class Rejected(Exception):
    def __init__(self, code, status=400):
        self.code, self.status = code, status


def validate_audio(data):
    if not 44 <= len(data) <= MAX_BYTES:
        raise Rejected("audio_size", 413)
    try:
        if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
            raise ValueError()
        # Refuse truncated or trailing payloads instead of trusting a filename/header alone.
        if int.from_bytes(data[4:8], "little") + 8 != len(data):
            raise ValueError()
        with wave.open(io.BytesIO(data), "rb") as audio:
            if (audio.getnchannels(), audio.getframerate(), audio.getsampwidth(), audio.getcomptype()) != (1, 16000, 2, "NONE"):
                raise ValueError()
            frames = audio.getnframes()
            if not 1600 <= frames <= 16000 * MAX_SECONDS or len(audio.readframes(frames)) != frames * 2:
                raise ValueError()
    except (ValueError, wave.Error, EOFError, OSError):
        raise Rejected("audio_format") from None


def check_model():
    worker = Path(__file__).resolve().parents[1]
    lock = json.loads((worker / "models.lock.json").read_text())["paraformer"]
    directory = Path(os.environ["LABCONNECT_MODEL_ROOT"]) / "paraformer-2023-09-14"
    for name in ("model.int8.onnx", "tokens.txt"):
        expected = lock["files"][name]
        with (directory / name).open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
                raise RuntimeError("model_hash_mismatch")
    return lock["revision"]


class Jobs:
    def __init__(self):
        self.lock = threading.RLock()
        self.items = {}
        self.active = None
        self.closed = False

    def prune(self):
        now = time.monotonic()
        for key, item in list(self.items.items()):
            if key != self.active and item["expires"] < now:
                del self.items[key]

    def submit(self, key, data, timeout):
        validate_audio(data)
        if not math.isfinite(timeout) or not 0.05 <= timeout <= MAX_SECONDS:
            raise Rejected("deadline")
        with self.lock:
            self.prune()
            if key in self.items:
                raise Rejected("job_exists", 409)
            if self.active or self.closed or len(self.items) >= 32:
                raise Rejected("worker_busy", 429)
            item = {"state": "running", "expires": time.monotonic() + RESULT_TTL,
                    "process": None, "canceled": False}
            self.items[key] = item
            self.active = key
            threading.Thread(target=self.run, args=(key, item, data, timeout), daemon=True).start()
            return {"id": key, "state": "running"}

    def run(self, key, item, data, timeout):
        process = None
        started = time.monotonic()
        state, result = "failed", {"error": "inference_failed"}
        try:
            with self.lock:
                if item["canceled"] or self.closed:
                    return
                process = subprocess.Popen([sys.executable, "-m", "transport.infer"],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
                item["process"] = process
            output, _ = process.communicate(data, timeout=max(0.001, timeout - (time.monotonic() - started)))
            if process.returncode == 0 and len(output) <= 65536:
                text = json.loads(output)["text"]
                if isinstance(text, str) and len(text) <= 8000:
                    state, result = "succeeded", {"text": text}
        except subprocess.TimeoutExpired:
            state, result = "timed_out", {"error": "inference_timeout"}
        except (OSError, ValueError, KeyError):
            pass
        finally:
            if process is not None:
                if process.poll() is None:
                    process.kill()
                process.communicate()
            # No WAV, stderr, model output or transcript is written to a log/file.
            data = b""
            with self.lock:
                item["process"] = None
                if item["canceled"] or self.closed:
                    self.items.pop(key, None)
                else:
                    item.update(state=state, result=result, expires=time.monotonic() + RESULT_TTL)
                if self.active == key:
                    self.active = None

    def get(self, key):
        with self.lock:
            self.prune()
            if key not in self.items:
                raise Rejected("job_not_found", 404)
            item = self.items[key]
            if item["canceled"]:
                raise Rejected("job_not_found", 404)
            return {"id": key, "state": item["state"], **item.get("result", {})}

    def remove(self, key):
        with self.lock:
            item = self.items.get(key)
            if item:
                item["canceled"] = True
                if item["process"] is not None and item["process"].poll() is None:
                    item["process"].kill()
                if key != self.active:
                    del self.items[key]

    def close(self):
        with self.lock:
            self.closed = True
            for key in list(self.items):
                self.remove(key)
        # The sole child is always reaped by run(), including shutdown/cancel.
        deadline = time.monotonic() + 5
        while self.active and time.monotonic() < deadline:
            time.sleep(0.02)


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, config):
        self.config = config
        self.secret = Path(config["key_file"]).read_text().strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]{43,128}", self.secret):
            raise ValueError("worker_key_format")
        self.model_revision = check_model()
        self.fingerprint = source_fingerprint()
        self.jobs = Jobs()
        self.slots = threading.BoundedSemaphore(4)
        super().__init__(("127.0.0.1", config["port"]), Handler)

    def process_request(self, request, address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        super().process_request(request, address)

    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            self.slots.release()

    def handle_error(self, request, address):
        pass  # HTTP errors never log headers, audio or recognized text.

    def service_actions(self):
        with self.jobs.lock:
            self.jobs.prune()


class Handler(BaseHTTPRequestHandler):
    server_version = "LabConnectPrivateWorker/1"

    def log_message(self, *args):
        pass

    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def respond(self, status, value):
        payload = json.dumps(value, ensure_ascii=True).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(payload)
        self.close_connection = True

    def dispatch(self):
        try:
            supplied = self.headers.get("Authorization", "")
            if not hmac.compare_digest(supplied.encode(), ("Bearer " + self.server.secret).encode()):
                raise Rejected("worker_unauthorized", 401)
            if self.command == "GET" and self.path == "/v1/health":
                with self.server.jobs.lock:
                    self.server.jobs.prune()
                    return self.respond(200, {"status": "ready", "protocol": PROTOCOL,
                        "instance_id": self.server.config["instance_id"], "source_sha": self.server.config["source_sha"],
                        "worker_fingerprint": self.server.fingerprint,
                        "model_revision": self.server.model_revision, "active_jobs": int(bool(self.server.jobs.active)),
                        "retained_results": len(self.server.jobs.items), "audio_files": 0, "pid": os.getpid()})
            if self.command == "POST" and self.path == "/v1/control/shutdown":
                if self.headers.get("X-Worker-Instance") != self.server.config["instance_id"]:
                    raise Rejected("instance_mismatch", 409)
                self.respond(200, {"status": "stopping"})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            match = re.fullmatch(r"/v1/jobs/([0-9a-f-]{36})", self.path)
            if not match or str(UUID(match[1])) != match[1]:
                raise Rejected("not_found", 404)
            key = match[1]
            if self.command == "POST":
                if self.headers.get("Transfer-Encoding") or self.headers.get("Content-Type") != "audio/wav":
                    raise Rejected("audio_format")
                lengths = self.headers.get_all("Content-Length", [])
                if len(lengths) != 1 or not lengths[0].isdigit():
                    raise Rejected("audio_length")
                length = int(lengths[0])
                if not 44 <= length <= MAX_BYTES:
                    raise Rejected("audio_size", 413)
                data = self.rfile.read(length)
                if len(data) != length:
                    raise Rejected("audio_length")
                value = self.server.jobs.submit(key, data, float(self.headers.get("X-ASR-Timeout-Seconds", "15")))
                return self.respond(202, value)
            if self.command == "GET":
                return self.respond(200, self.server.jobs.get(key))
            if self.command == "DELETE":
                self.server.jobs.remove(key)
                return self.respond(200, {"id": key, "state": "deleted"})
            raise Rejected("method", 405)
        except Rejected as error:
            self.respond(error.status, {"error": error.code})
        except (ValueError, OverflowError):
            self.respond(400, {"error": "invalid_request"})
        except (BrokenPipeError, ConnectionResetError, socket.timeout):
            self.close_connection = True

    do_GET = do_POST = do_DELETE = dispatch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    server = Server(config)
    try:
        server.serve_forever(poll_interval=0.1)
    finally:
        server.jobs.close()
        server.server_close()


if __name__ == "__main__":
    main()
