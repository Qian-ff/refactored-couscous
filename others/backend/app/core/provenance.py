"""Dependency-free, shared build identity for API, Vite, launchers and browser checks."""
import hashlib
import json
from pathlib import Path
import subprocess


def identity(root: Path, surface: str) -> dict[str, str]:
    root = root.resolve()
    result = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True,
                            text=True, encoding="utf-8", errors="replace", check=True)
    names = ["others/config/application.json", "others/config/branding.json", "others/scripts/provenance.py",
             "others/scripts/web-environment.mjs"]
    if surface == "api":
        names += ["others/backend/pyproject.toml", "others/backend/uv.lock"]
        names += [p.relative_to(root).as_posix() for p in (root / "others/backend/app").rglob("*.py")]
    elif surface == "web":
        names += ["package.json", "pnpm-lock.yaml", "web/package.json", "web/vite.config.ts"]
        names += [p.relative_to(root).as_posix() for p in (root / "web/src").rglob("*") if p.is_file()]
    else:
        raise ValueError("Unknown source surface")
    digest = hashlib.sha256()
    for name in sorted(set(names)):
        digest.update(name.encode() + b"\0" + (root / name).read_bytes() + b"\0")
    return {"source_sha": result.stdout.strip(), "surface": surface,
            "worktree_id": hashlib.sha256(str(root).casefold().encode()).hexdigest()[:20],
            "source_fingerprint": digest.hexdigest(),
            "contract": json.loads((root / "others/config/application.json").read_text(encoding="utf-8"))["version"]}
