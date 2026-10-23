"""Explicit A acceptance probe using the pinned public Chinese WAV on stdin; no user recording."""
from dataclasses import replace
import hashlib
import json
import sys
import time

from app.core.asr_client import AsrClient, AsrError

SAMPLE_SHA = "1a6bf94091d9c35e11aea5d494d05e3287b8f5c767f6de3bfd796d91b637500c"


def expect(code, operation):
    try:
        operation()
    except AsrError as error:
        assert error.code == code, (code, error.code)
        return
    raise AssertionError("Expected: " + code)


def idle(client):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        status = client.health()
        if status["active_jobs"] == 0 and status["retained_results"] == 0:
            return
        time.sleep(0.05)
    raise AssertionError("Worker failed to clean jobs/results")


def main():
    if "--offline" in sys.argv:
        try:
            AsrClient.from_environment().health()
        except AsrError as error:
            assert error.code in {"asr_unavailable", "asr_unconfigured"}
            print(json.dumps({"status": "passed", "offline_error": error.code}))
            return
        raise AssertionError("Offline worker unexpectedly available")
    audio = sys.stdin.buffer.read()
    assert hashlib.sha256(audio).hexdigest() == SAMPLE_SHA, "Only pinned public sample is accepted by this probe"
    client = AsrClient.from_environment()
    health = client.health()
    checks = ["authenticated_health", "worker_source_identity"]
    expect("worker_unauthorized", lambda: replace(client, secret="wrong-key").health())
    expect("worker_unauthorized", lambda: replace(client, secret="").health())
    checks += ["wrong_key_rejected", "missing_key_rejected"]
    expect("asr_identity_mismatch", lambda: replace(client, config={**client.config, "instance_id": "other"}).health())
    expect("audio_size", lambda: client.submit(audio * 8))
    expect("audio_format", lambda: client.submit(b"not a wave" * 10))
    expect("audio_format", lambda: client.submit(audio[:-2]))
    checks += ["identity_mismatch_rejected", "oversize_rejected", "invalid_wav_rejected", "truncated_wav_rejected"]
    started = time.monotonic()
    text = client.transcribe(audio)
    assert len(text.strip()) > 3 and any("\u4e00" <= char <= "\u9fff" for char in text)
    elapsed = round(time.monotonic() - started, 3)
    idle(client)
    checks += ["real_chinese_cpu_inference", "successful_result_deleted"]
    key = client.submit(audio)
    expect("worker_busy", lambda: client.submit(audio))
    client.cancel(key)
    expect("job_not_found", lambda: client.result(key))
    idle(client)
    checks += ["concurrency_bounded", "cancel_running_child", "cancel_result_inaccessible", "cancel_cleanup"]
    expect("inference_timeout", lambda: client.transcribe(audio, timeout_seconds=0.05))
    idle(client)
    checks += ["deadline_kills_inference", "timeout_cleanup"]
    calls = 0

    def cancelled():
        nonlocal calls
        calls += 1
        return calls >= 3

    expect("asr_canceled", lambda: client.transcribe(audio, cancelled=cancelled))
    idle(client)
    checks += ["caller_cancellation", "caller_cleanup"]
    assert client.health()["audio_files"] == 0
    checks.append("audio_memory_only")
    print(json.dumps({"status": "passed", "checks": checks, "count": len(checks), "worker": health,
                      "public_sample_sha256": SAMPLE_SHA, "elapsed_seconds": elapsed,
                      "public_sample_text": text}, ensure_ascii=True))


if __name__ == "__main__":
    main()
