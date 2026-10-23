"""A-only private ASR operations; project credentials/config, no global installs or public worker ports."""
import argparse
import hashlib
import json
import os
import secrets
import shlex
import subprocess
import sys
import time
from uuid import uuid4

import cloud

ROOT = cloud.ROOT
RUNTIME = ROOT / "others/runtime/cloud-asr"


def save(path, value):
    temporary = path.with_suffix(".pending")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")
    temporary.replace(path)


def client():
    sys.path.insert(0, str(ROOT / "others/backend"))
    from app.core.asr_client import AsrClient
    return AsrClient.from_environment()


def require_a():
    if cloud.git("branch", "--show-current") != "main":
        raise RuntimeError("Only A/main manages the shared worker and cloud transport")


def cloud_health():
    result = cloud.remote("docker exec labconnect-cloud-api-1 .venv/bin/python -c "
        + shlex.quote("import json; from app.core.asr_client import AsrClient; print(json.dumps(AsrClient.from_environment().health()))")
        + "\n", capture=True)
    return json.loads(result.stdout)


def prepare(local_only=False):
    require_a()
    RUNTIME.mkdir(parents=True, exist_ok=True)
    key = RUNTIME / "service.key"
    if not key.exists():
        key.write_text(secrets.token_urlsafe(48) + "\n", encoding="ascii", newline="\n")
    if os.name == "nt":
        cloud.run(["icacls", str(RUNTIME), "/inheritance:r", "/grant:r",
                   os.environ["USERNAME"] + ":(OI)(CI)F"], stdout=subprocess.DEVNULL)
    else:
        RUNTIME.chmod(0o700)
        key.chmod(0o600)
    if local_only:
        return
    checksum = hashlib.sha256(key.read_bytes()).hexdigest()
    result = cloud.remote(r'''set -eu
python3 - "$1" <<'PY'
import hashlib,os,sys
from pathlib import Path
directory=Path('/opt/labconnect/shared/asr')
directory.mkdir(parents=True,exist_ok=True)
os.chown(directory,10001,10001)
directory.chmod(0o700)
key=directory/'service.key'
if key.exists():
    if hashlib.sha256(key.read_bytes()).hexdigest() != sys.argv[1]:
        raise SystemExit('Existing ASR key differs; preserved. Explicit rotation is required.')
    print('configured')
else:
    print('empty')
PY
''', checksum, capture=True)
    if result.stdout.strip() == b"empty":
        cloud.upload(key, "/opt/labconnect/shared/asr/service.key")
        cloud.remote("set -eu\nchown 10001:10001 /opt/labconnect/shared/asr/service.key\nchmod 400 /opt/labconnect/shared/asr/service.key\n")
    print("ASR service key prepared privately; existing credentials preserved.")


def start(local_only=False):
    require_a()
    sys.path.insert(0, str(ROOT / "others/ai_worker"))
    from transport.server import source_fingerprint
    fingerprint = source_fingerprint()
    if (RUNTIME / "state.json").exists():
        state = json.loads((RUNTIME / "state.json").read_text())
        try:
            health = client().health()
        except RuntimeError:
            raise RuntimeError("Previous worker state exists. Run stop and inspect before restarting.") from None
        if state.get("worker_fingerprint") != fingerprint:
            raise RuntimeError("Worker runs an older source. Stop/start before accepting this baseline.")
        if state["cloud_tunnel"] == local_only:
            raise RuntimeError("Different local/cloud mode is already running. Stop before switching modes.")
        if state["cloud_tunnel"] and cloud_health()["instance_id"] != state["instance_id"]:
            raise RuntimeError("Cloud session identity differs; inspect before reconnecting")
        print(json.dumps({"status": "already_running", "local": health, "cloud_tunnel": state["cloud_tunnel"]}))
        return
    if not local_only and cloud.git("status", "--porcelain"):
        raise RuntimeError("Cloud sessions require committed, clean A/main source")
    prepare(local_only)
    instance = uuid4().hex
    sha = cloud.git("rev-parse", "HEAD")
    config = {"protocol": "labconnect-asr-1", "transport": "loopback", "port": 18765,
              "worker_fingerprint": fingerprint,
              "instance_id": instance, "source_sha": sha, "key_file": str(RUNTIME / "service.key")}
    save(RUNTIME / "worker.json", config)
    save(RUNTIME / "client.json", config)
    env = {**os.environ, "LABCONNECT_MODEL_ROOT": str(ROOT / "others/models"),
           "LABCONNECT_SHARED_ROOT": str(ROOT), "PYTHONPATH": str(ROOT / "others/ai_worker"),
           "PYTHONDONTWRITEBYTECODE": "1"}
    interpreter = ROOT / "others/ai_worker/.venv/Scripts/python.exe"
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    worker = tunnel = None
    try:
        with (RUNTIME / "worker.log").open("ab") as log:
            worker = subprocess.Popen([str(interpreter), "-m", "transport.server", "--config", str(RUNTIME / "worker.json")],
                cwd=ROOT / "others/ai_worker", env=env, stdin=subprocess.DEVNULL,
                stdout=log, stderr=log, creationflags=flags)
        deadline = time.monotonic() + 30
        while True:
            if worker.poll() is not None:
                raise RuntimeError("Worker failed. Inspect ignored cloud-asr/worker.log.")
            try:
                health = client().health()
                break
            except RuntimeError:
                if time.monotonic() >= deadline:
                    raise RuntimeError("Worker startup timeout") from None
                time.sleep(0.2)
        if not local_only:
            connection = cloud.connection()
            command = "python3 /opt/labconnect/current/asr-session.py " + " ".join(map(shlex.quote, [instance, sha, fingerprint]))
            args = ["ssh", *cloud.transport_options(), "-T", "-o", "ExitOnForwardFailure=yes",
                    "-o", "ServerAliveCountMax=2", "-R",
                    "/opt/labconnect/shared/asr/tunnel-" + instance + ".sock:127.0.0.1:18765",
                    "-p", str(connection.get("port", 22)), connection["user"] + "@" + connection["host"], command]
            with (RUNTIME / "tunnel.log").open("ab") as log:
                tunnel = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=log, stderr=log, creationflags=flags)
            deadline = time.monotonic() + 20
            while True:
                if tunnel.poll() is not None:
                    raise RuntimeError("Tunnel failed. Inspect ignored cloud-asr/tunnel.log.")
                result = cloud.remote(r'''python3 - "$1" <<'PY'
import json,sys
from pathlib import Path
p=Path('/opt/labconnect/shared/asr/client.json')
print('ready' if p.exists() and json.loads(p.read_text()).get('instance_id')==sys.argv[1] else 'waiting')
PY
''', instance, capture=True)
                if result.stdout.strip() == b"ready":
                    break
                if time.monotonic() >= deadline:
                    raise RuntimeError("Cloud session readiness timeout")
                time.sleep(0.2)
            if cloud_health()["instance_id"] != instance:
                raise RuntimeError("Cloud API cannot reach the expected worker")
        save(RUNTIME / "state.json", {"instance_id": instance, "source_sha": sha,
             "worker_fingerprint": fingerprint,
             "worker_pid": worker.pid, "tunnel_pid": tunnel.pid if tunnel else None,
             "cloud_tunnel": not local_only, "dirty_at_start": bool(cloud.git("status", "--porcelain"))})
        print(json.dumps({"status": "started", "local": health, "cloud_tunnel": not local_only}))
    except BaseException:
        if tunnel is not None:
            tunnel.terminate()
            tunnel.wait(timeout=10)
        if worker is not None:
            worker.terminate()
            worker.wait(timeout=10)
        raise


def stop():
    require_a()
    state_path = RUNTIME / "state.json"
    if not state_path.exists():
        print("No project ASR process state; no unrelated process was stopped.")
        return
    state = json.loads(state_path.read_text())
    if state["cloud_tunnel"]:
        cloud.remote(r'''set -eu
python3 - "$1" <<'PY'
import re,sys
from pathlib import Path
session=sys.argv[1]
assert re.fullmatch('[0-9a-f]{32}',session)
(Path('/opt/labconnect/shared/asr')/('stop-'+session)).touch(mode=0o600)
PY
''', state["instance_id"])
    try:
        api = client()
        health = api.health()
        if health["instance_id"] != state["instance_id"]:
            raise RuntimeError("Different worker identity; preserved")
        api.request("POST", "/v1/control/shutdown", headers={"X-Worker-Instance": state["instance_id"]})
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                api.health()
            except RuntimeError:
                break
            time.sleep(0.2)
        else:
            raise RuntimeError("Worker did not stop; state preserved for investigation")
    except RuntimeError as error:
        if str(error) not in {"asr_unavailable", "asr_unconfigured"}:
            raise
    if state["cloud_tunnel"]:
        cloud.remote(r'''set -eu
python3 - "$1" <<'PY'
import json,sys,time
from pathlib import Path
p=Path('/opt/labconnect/shared/asr/client.json')
deadline=time.monotonic()+10
while p.exists() and json.loads(p.read_text()).get('instance_id')==sys.argv[1]:
    if time.monotonic()>=deadline: raise SystemExit('Cloud session did not stop; state preserved')
    time.sleep(0.1)
print('Private cloud session stopped and socket configuration cleaned.')
PY
''', state["instance_id"])
    for name in ("state.json", "client.json"):
        (RUNTIME / name).unlink(missing_ok=True)
    print("Stopped this worker/session. Service key and unrelated environments preserved.")


def verify(local_only=False, offline=False):
    sample = b"" if offline else (ROOT / "others/models/paraformer-2023-09-14/test_wavs/0.wav").read_bytes()
    suffix = ["--offline"] if offline else []
    if local_only:
        args = [sys.executable, str(ROOT / "others/scripts/shared_env.py"), "backend", "app.core.asr_probe", *suffix]
    else:
        value = cloud.connection()
        args = ["ssh", *cloud.transport_options(), "-p", str(value.get("port", 22)),
                value["user"] + "@" + value["host"],
                "docker exec -i labconnect-cloud-api-1 .venv/bin/python -m app.core.asr_probe " + " ".join(suffix)]
    result = cloud.run(args, input=sample, capture_output=True, cwd=ROOT)
    report = json.loads(result.stdout)
    folder = ROOT / "others/reports/cloud-asr"
    folder.mkdir(parents=True, exist_ok=True)
    name = ("local" if local_only else "cloud") + ("-offline" if offline else "-probe") + ".json"
    save(folder / name, report)
    print(json.dumps(report))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "start", "stop", "status", "verify"])
    parser.add_argument("--local-only", action="store_true")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            prepare(args.local_only)
        elif args.command == "start":
            start(args.local_only)
        elif args.command == "stop":
            stop()
        elif args.command == "verify":
            verify(args.local_only, args.offline)
        else:
            state = json.loads((RUNTIME / "state.json").read_text())
            print(json.dumps({"local": client().health(), "cloud": cloud_health() if state["cloud_tunnel"] else None,
                              "dirty_at_start": state["dirty_at_start"]}))
    except (RuntimeError, OSError, subprocess.SubprocessError):
        # Subprocess command lines can contain SSH paths. Never dump arbitrary credentials or bodies.
        print("ASR operation failed. Inspect the project status/logs and handoff instructions.", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
