"""C02-only isolated dependency validation; never changes the shared environments."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from shared_env import BOOTSTRAP, WORKER_BOOTSTRAP, database_test_lock
from workflow import primary_root

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = "c02-public-integration"
BASELINE = "e42dee58eefdeadf1fb5bbd462fefe47c8331703"


def fingerprint(project: Path) -> str:
    digest = hashlib.sha256()
    for name in ("pyproject.toml", "uv.lock"):
        digest.update(name.encode())
        digest.update((project / name).read_bytes())
    return digest.hexdigest()


def validate(root: Path = ROOT) -> Path:
    branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=root, text=True).strip()
    grant = json.loads((root / "others/contracts/execution-delegations.json").read_text())["packages"][PACKAGE]
    if branch != "codex/a-executor" or grant["status"] != "active" or grant["executor"] != "A-executor":
        raise RuntimeError("C02 candidate environment requires the active A-executor grant")
    subprocess.run(["git", "merge-base", "--is-ancestor", BASELINE, "HEAD"], cwd=root, check=True)
    primary = primary_root(root)
    if root.resolve() == primary.resolve():
        raise RuntimeError("Candidate environment must not be created in main")
    return primary


def paths(surface: str):
    project = ROOT / "others" / ("ai_worker" if surface == "worker" else "backend")
    environment = ROOT / "others/runtime/c02-public/envs" / surface
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    return project, environment, python


def prepare(surface: str, primary: Path) -> int:
    project, environment, python = paths(surface)
    uv = primary / "others/cache/tools/uv" / ("uv.exe" if os.name == "nt" else "uv")
    reference = primary / "others" / ("ai_worker" if surface == "worker" else "backend")
    reference_python = reference / (".venv/Scripts/python.exe" if os.name == "nt" else ".venv/bin/python")
    env = os.environ.copy()
    env.update(UV_CACHE_DIR=str(primary / "others/cache/uv"), UV_PROJECT_ENVIRONMENT=str(environment))
    subprocess.run([str(uv), "sync", "--frozen", "--all-groups", "--no-install-project",
                    "--project", str(project), "--python", str(reference_python)], env=env, check=True)
    stamp = {"surface": surface, "fingerprint": fingerprint(project), "python": str(python),
             "source": str(project), "shared_environment_modified": False}
    (environment / "c02-inputs.json").write_text(json.dumps(stamp, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stamp))
    return 0


def run(surface: str, module: str, arguments: list[str], primary: Path) -> int:
    project, environment, python = paths(surface)
    stamp = json.loads((environment / "c02-inputs.json").read_text())
    if stamp["fingerprint"] != fingerprint(project) or not python.is_file():
        raise RuntimeError("C02 candidate dependency inputs changed; prepare this candidate again")
    bootstrap = WORKER_BOOTSTRAP if surface == "worker" else BOOTSTRAP
    if surface == "worker" and module != "__probe__" and not module.startswith("content."):
        raise RuntimeError("C02 worker helper only executes the content package")
    command = [str(python), "-c", bootstrap, str(ROOT), str(primary), module, *arguments]
    if module == "pytest":
        admin = ROOT / "others/runtime/c02-public/database-admin.json"
        if not admin.is_file():
            raise RuntimeError("Prepare the dedicated C02 database and separate management configuration first")
        env = os.environ.copy()
        env["LABCONNECT_C02_TEST_ADMIN_CONFIG"] = str(admin)
        with database_test_lock(primary):
            return subprocess.run(command, cwd=ROOT, env=env).returncode
    return subprocess.run(command, cwd=ROOT).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    for name in ("prepare", "probe"):
        action = actions.add_parser(name)
        action.add_argument("--surface", choices=("backend", "worker"), default="backend")
    for name in ("backend", "worker"):
        action = actions.add_parser(name)
        action.add_argument("arguments", nargs=argparse.REMAINDER)
    options = parser.parse_args()
    primary = validate()
    if options.action == "prepare":
        return prepare(options.surface, primary)
    if options.action == "probe":
        return run(options.surface, "__probe__", [], primary)
    if not options.arguments:
        parser.error("Execution requires a module")
    return run(options.action, options.arguments[0], options.arguments[1:], primary)


if __name__ == "__main__":
    sys.exit(main())
