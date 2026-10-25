"""Owned synthetic process for kernel-lock tests; no business environment is needed."""
import argparse
import json
import os
import sys
from pathlib import Path
from uuid import UUID

from app.domains.content.upload_fence import UploadFence


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--upload", type=UUID, required=True)
    args = parser.parse_args()
    attempt = UploadFence(args.root).try_acquire(args.upload)
    thread_id = 0
    if os.name == "nt":
        import ctypes
        thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
    print(json.dumps({"status": attempt.status, "thread_id": thread_id}), flush=True)
    if attempt.guard is not None:
        with attempt.guard:
            sys.stdin.readline(16)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
