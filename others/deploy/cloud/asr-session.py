"""Remote lifetime/permissions for one SSH reverse Unix socket. No TCP listener or SSH config change."""
import fcntl
import json
import os
from pathlib import Path
import re
import signal
import stat
import sys
import time

ROOT = Path("/opt/labconnect/shared/asr")


def main():
    session, source_sha, fingerprint = sys.argv[1:]
    if (not re.fullmatch(r"[0-9a-f]{32}", session) or not re.fullmatch(r"[0-9a-f]{40}", source_sha)
            or not re.fullmatch(r"[0-9a-f]{64}", fingerprint)):
        raise SystemExit("Invalid ASR session identity")
    socket = ROOT / ("tunnel-" + session + ".sock")
    active = ROOT / "client.json"
    stop = ROOT / ("stop-" + session)
    done = False

    def finish(*_):
        nonlocal done
        done = True

    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, finish)
    try:
        with (ROOT / "session.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if not stat.S_ISSOCK(socket.lstat().st_mode):
                raise RuntimeError("SSH did not create the expected socket")
            os.chown(socket, 10001, 10001)
            socket.chmod(0o600)
            value = {"protocol": "labconnect-asr-1", "transport": "unix", "instance_id": session,
                     "worker_fingerprint": fingerprint,
                     "source_sha": source_sha, "key_file": "/run/labconnect-asr/service.key",
                     "socket_path": "/run/labconnect-asr/" + socket.name}
            pending = ROOT / ("client-" + session + ".pending")
            pending.write_text(json.dumps(value) + "\n")
            os.chown(pending, 10001, 10001)
            pending.chmod(0o400)
            os.replace(pending, active)
            while not done and not stop.exists():
                # A closed SSH channel breaks this write; cleanup stays tied to this session.
                print("ASR private session alive: " + session, flush=True)
                time.sleep(1)
    finally:
        try:
            if active.exists() and json.loads(active.read_text()).get("instance_id") == session:
                active.unlink()
        finally:
            socket.unlink(missing_ok=True)
            stop.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
