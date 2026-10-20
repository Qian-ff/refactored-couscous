"""Reuse A's local configuration, backend interpreter and dependency cache from a Git worktree."""
from __future__ import annotations

import argparse
from contextlib import contextmanager, nullcontext
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from workflow import primary_root, repository

BACKEND_INPUTS = ("others/backend/pyproject.toml", "others/backend/uv.lock")
WEB_INPUTS = ("package.json", "pnpm-lock.yaml", "pnpm-workspace.yaml",
              "web/package.json", "desktop/package.json", "android/package.json")

# Execute with the shared interpreter, but bind imports and subprocesses to this checkout.
BOOTSTRAP = r'''
import importlib.util, json, os, runpy, sys
from pathlib import Path
from dotenv import load_dotenv
root, primary, module, *arguments = sys.argv[1:]
backend = Path(root) / "others/backend"
load_dotenv(Path(primary) / ".env", override=True)
os.chdir(backend)
sys.path.insert(0, str(backend))
os.environ["PYTHONPATH"] = str(backend) + os.pathsep + os.environ.get("PYTHONPATH", "")
source = Path(importlib.util.find_spec("app").origin).resolve()
if source != (backend / "app/__init__.py").resolve():
    raise RuntimeError("Backend import resolved outside the selected worktree")
if module == "__probe__":
    print(json.dumps({"python": sys.executable, "app_source": str(source),
        "configuration_loaded": bool(os.environ.get("DATABASE_URL") and os.environ.get("SECRET_KEY"))}))
else:
    sys.argv = [module, *arguments]
    runpy.run_module(module, run_name="__main__", alter_sys=True)
'''


def different_inputs(root: Path, primary: Path, inputs: tuple[str, ...]) -> list[str]:
    def digest(path: Path) -> bytes:
        return hashlib.sha256(path.read_bytes()).digest()
    return [name for name in inputs if digest(root / name) != digest(primary / name)]


def require_compatible(root: Path, primary: Path, inputs: tuple[str, ...]) -> None:
    different = different_inputs(root, primary, inputs)
    if different:
        raise RuntimeError("Dependency inputs differ from A; ask A to synchronize the environment: "
                           + ", ".join(different))


@contextmanager
def database_test_lock(primary: Path):
    """All shared pytest runs use the existing local test DB, so admit only one at a time."""
    path = primary / "others/runtime/shared-backend-tests.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        handle.write(b"\0")
        handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise RuntimeError("Another shared backend test run is active; retry after it finishes") from error
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def backend(root: Path, primary: Path, module: str, arguments: list[str]) -> int:
    require_compatible(root, primary, BACKEND_INPUTS)
    interpreter = primary / "others/backend/.venv/Scripts/python.exe"
    if not interpreter.is_file() or not (primary / ".env").is_file():
        raise RuntimeError("A must prepare its backend .venv and ignored .env first")
    lock = database_test_lock(primary) if module == "pytest" else nullcontext()
    with lock:
        return subprocess.run([str(interpreter), "-c", BOOTSTRAP, str(root), str(primary),
                               module, *arguments], cwd=root).returncode


def install_web(root: Path, primary: Path) -> int:
    require_compatible(root, primary, WEB_INPUTS)
    pnpm = shutil.which("pnpm.cmd") or shutil.which("pnpm")
    if not pnpm:
        raise RuntimeError("pnpm is unavailable; use the project's documented Node/pnpm versions")
    # Offline and without install scripts: this prepares web development, not native packaging.
    return subprocess.run([pnpm, "install", "--offline", "--frozen-lockfile", "--ignore-scripts",
                           "--package-import-method", "hardlink", "--store-dir",
                           str(primary / "others/cache/pnpm-store")], cwd=root).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status")
    commands.add_parser("probe", help="Verify the shared interpreter imports this worktree, without displaying secrets")
    commands.add_parser("install-web", help="Offline hardlink installation using A's existing cache")
    run = commands.add_parser("backend", help="Run a Python module using A's environment and this tree's code")
    run.add_argument("module", help="e.g. pytest, uvicorn or ruff")
    run.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        root = repository(Path.cwd())
        primary = primary_root(root)
        if args.command == "status":
            print(json.dumps({"worktree": str(root), "shared_root": str(primary),
                "backend_inputs_match": not different_inputs(root, primary, BACKEND_INPUTS),
                "web_inputs_match": not different_inputs(root, primary, WEB_INPUTS),
                "shared_config_present": (primary / ".env").is_file(),
                "local_settings_present": (primary / "others/config/local.json").is_file(),
                "demo_accounts_present": (primary / "others/runtime/demo-accounts.json").is_file(),
                "node_modules_present": (root / "node_modules").is_dir()}, indent=2))
            return 0
        if args.command == "install-web":
            return install_web(root, primary)
        return backend(root, primary, "__probe__" if args.command == "probe" else args.module,
                       [] if args.command == "probe" else args.arguments)
    except KeyboardInterrupt:
        return 130
    except (OSError, RuntimeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
