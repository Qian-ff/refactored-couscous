"""One checked-in version source; runtime identity is captured at process startup."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[4]
VERSION = json.loads((ROOT / "others/config/application.json").read_text(encoding="utf-8"))["version"]


def development_identity() -> dict[str, str]:
    def git(*args):
        result = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True,
                                encoding="utf-8", errors="replace")
        if result.returncode:
            raise RuntimeError("Cannot identify the development checkout")
        return result.stdout.strip()
    # Fingerprint identifies the tree without publishing a user's absolute directory.
    return {"source_sha": git("rev-parse", "HEAD"),
            "worktree_id": hashlib.sha256(str(ROOT.resolve()).casefold().encode()).hexdigest()[:20],
            "contract": VERSION}


BUILD = development_identity() if os.environ.get("APP_ENV", "development") != "production" else {
    "source_sha": os.environ.get("LABCONNECT_SOURCE_SHA", "unrecorded"), "contract": VERSION}
