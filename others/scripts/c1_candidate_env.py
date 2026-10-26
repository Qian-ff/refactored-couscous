"""Fixed C1 isolated environments; shared dependencies and main services remain untouched."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from content_candidate_env import fingerprint
from shared_env import BOOTSTRAP, WORKER_BOOTSTRAP, database_test_lock
from workflow import primary_root

ROOT = Path(__file__).resolve().parents[2]
BASELINE = "c22328671a5d32715c4b5dbc10b66d5f4d46aa84"


def validate(root: Path = ROOT) -> Path:
    branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=root, text=True).strip()
    grant = json.loads((root / "others/contracts/execution-delegations.json").read_text())["packages"]["c1-runtime-public-integration"]
    if branch != "codex/a-executor" or grant["status"] != "active" or grant["executor"] != "A-executor":
        raise RuntimeError("C1 candidate environment requires the active A-executor T2 grant")
    subprocess.run(["git", "merge-base", "--is-ancestor", BASELINE, "HEAD"], cwd=root, check=True)
    primary = primary_root(root)
    if root.resolve() == primary.resolve():
        raise RuntimeError("C1 candidate must not change main's environment")
    return primary


def paths(surface: str):
    if surface not in {"backend", "worker"}:
        raise ValueError("Unknown C1 environment")
    project = ROOT / "others" / ("ai_worker" if surface == "worker" else "backend")
    environment = ROOT / "others/runtime/c1-public/envs" / surface
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    return project, environment, python


def prepare(surface: str, primary: Path):
    project, environment, python = paths(surface)
    uv = primary / "others/cache/tools/uv" / ("uv.exe" if os.name == "nt" else "uv")
    reference = primary / "others" / ("ai_worker" if surface == "worker" else "backend")
    reference_python = reference / (".venv/Scripts/python.exe" if os.name == "nt" else ".venv/bin/python")
    env = os.environ.copy()
    env.update(UV_CACHE_DIR=str(primary / "others/cache/uv"), UV_PROJECT_ENVIRONMENT=str(environment))
    subprocess.run([str(uv), "--no-config", "sync", "--frozen", "--all-groups", "--no-install-project",
                    "--project", str(project), "--python", str(reference_python)], env=env, check=True)
    stamp = {"surface": surface, "fingerprint": fingerprint(project), "python": str(python),
             "source": str(project), "shared_environment_modified": False}
    (environment / "c1-inputs.json").write_text(json.dumps(stamp, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stamp))


def run(surface: str, module: str, arguments: list[str], primary: Path):
    project, environment, python = paths(surface)
    stamp = json.loads((environment / "c1-inputs.json").read_text())
    if stamp["fingerprint"] != fingerprint(project) or not python.is_file():
        raise RuntimeError("C1 inputs changed; prepare the isolated environment again")
    if surface == "worker" and module != "__probe__" and not module.startswith("content."):
        raise RuntimeError("C1 worker helper only executes the fixed content package")
    bootstrap = WORKER_BOOTSTRAP if surface == "worker" else BOOTSTRAP
    command = [str(python), "-c", bootstrap, str(ROOT), str(primary), module, *arguments]
    env = os.environ.copy()
    if module == "pytest":
        admin = ROOT / "others/runtime/c1-public/database-admin.json"
        if not admin.is_file():
            raise RuntimeError("Prepare the fixed C1 test profile first")
        env["LABCONNECT_C02_TEST_ADMIN_CONFIG"] = str(admin)
        with database_test_lock(primary):
            return subprocess.run(command, cwd=ROOT, env=env).returncode
    return subprocess.run(command, cwd=ROOT, env=env).returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    for name in ("prepare", "probe"):
        action = actions.add_parser(name)
        action.add_argument("--surface", choices=("backend", "worker"), default="backend")
    for name in ("backend", "worker"):
        actions.add_parser(name).add_argument("arguments", nargs=argparse.REMAINDER)
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
