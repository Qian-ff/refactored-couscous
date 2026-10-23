"""Check preparation files, links, role ownership and ignore rules; no app readiness claim."""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    failures: list[str] = []
    required = [
        "README.md", "AGENTS.md", ".gitignore", ".gitattributes", ".editorconfig",
        "web/README.md", "desktop/README.md", "android/README.md",
        "others/backend/README.md", "others/ai_worker/README.md",
        "others/contracts/README.md", "others/contracts/ownership.json",
        "others/contracts/domain-model.md", "others/contracts/api-conventions.md",
        "others/docs/design.md", "others/docs/start-here.md",
        "others/docs/git-workflow.md", "others/docs/licensing.md",
        "others/docs/environment.md", "others/scripts/Use-ProjectEnvironment.ps1",
        "others/docs/shared-environment.md", "others/docs/a2-start.md", "others/scripts/shared_env.py",
        "others/docs/ai/README.md", "others/deploy/.env.example",
        "others/deploy/README.md", "others/config/local.example.json",
        "others/scripts/workflow.py", "others/scripts/preflight.py",
        "others/qa/acceptance.md", "others/qa/test_workflow.py",
        "others/docs/coordination.md", "others/docs/coordination-rollout.md",
        "others/docs/ai/executor.md", "others/docs/ai/work-package-template.md",
        "others/contracts/execution-delegations.json",
    ]
    for name in required:
        file = ROOT / name
        if not file.is_file() or not file.stat().st_size:
            failures.append("Missing/empty required file: " + name)
    try:
        rules = json.loads((ROOT / "others/contracts/ownership.json").read_text(encoding="utf-8"))
        if (set(rules["roles"]) != set("ABCDG") or rules["max_active_chats"] != 4
                or set(rules.get("executors", {})) != {"A-executor"}
                or set(rules.get("retired_roles", {})) != {"E", "F"}):
            failures.append("Role roster or concurrency differs from the agreed plan")
        branches = [v["branch"] for v in [*rules["roles"].values(), *rules["executors"].values()]]
        if len(branches) != len(set(branches)):
            failures.append("Roles share a branch")
        scopes = []
        for role, data in rules["roles"].items():
            if data["worktree"] is not None and not isinstance(data["worktree"], str):
                failures.append("Invalid worktree location for role " + role)
            prompts = list((ROOT / "others/docs/ai").glob(role + "-*.md"))
            if len(prompts) != 1:
                failures.append("Expected one task brief for role " + role)
            for scope in data["owned_paths"]:
                if role != "A":
                    if scope.startswith("/") or ".." in Path(scope).parts or scope == "*":
                        failures.append("Unsafe ownership scope: " + scope)
                    scopes.append((role, scope))
        for i, (left_role, left) in enumerate(scopes):
            for right_role, right in scopes[i + 1:]:
                if left_role != right_role and (
                    left == right or (left.endswith("/") and right.startswith(left))
                    or (right.endswith("/") and left.startswith(right))
                ):
                    failures.append(f"Overlapping role scopes: {left_role}:{left} / {right_role}:{right}")
        executor = rules["executors"]["A-executor"]
        if (executor["owner_role"] != "A" or executor["branch"] != "codex/a-executor"
                or executor.get("owned_paths") or executor["worktree"] is not None):
            failures.append("Executor must use an independent registered branch and explicit per-package delegation")
        if not (ROOT / executor["brief"]).is_file():
            failures.append("Missing executor brief")
        grants = json.loads((ROOT / executor["delegations"]).read_text(encoding="utf-8"))
        for package, grant in grants["packages"].items():
            paths = grant.get("allowed_paths", [])
            if (grant.get("executor") not in rules["executors"] or not paths
                    or not re.fullmatch(r"[0-9a-f]{40}", grant.get("baseline_sha", ""))
                    or any(not isinstance(p, str) or not p or p in (".", "*")
                           or "*" in p or "\\" in p or ":" in p or p.startswith("/")
                           or ".." in p.split("/") or p == ".git" or p.startswith(".git/") for p in paths)):
                failures.append("Unsafe execution delegation: " + package)
        if (rules["retired_roles"]["E"]["replacement"] != "C"
                or rules["retired_roles"]["F"]["replacement"] != "A-executor"):
            failures.append("Retired E/F replacements differ from approved plan")
    except (OSError, ValueError, KeyError) as error:
        failures.append("Invalid ownership manifest: " + str(error))
    documents = [ROOT / "README.md", ROOT / "AGENTS.md"]
    documents += list((ROOT / "others/docs").rglob("*.md"))
    documents += list((ROOT / "others/contracts").glob("*.md"))
    for document in documents:
        if not document.exists():
            continue
        text = document.read_text(encoding="utf-8")
        for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
            if "://" in link or link.startswith("#"):
                continue
            target = link.split("#", 1)[0]
            resolved = (document.parent / target).resolve()
            if not resolved.is_relative_to(ROOT) or not resolved.exists():
                failures.append(f"Broken/local-outside link: {document.relative_to(ROOT)} -> {link}")
    checks = {
        ".env": True, ".env.local": True, "others/deploy/.env.example": False,
        "web/node_modules/test/index.js": True, "desktop/release/test.exe": True,
        "android/local.properties": True, "others/backend/.venv/test.py": True,
        "others/worktrees/example/test.md": True, "others/reports/preflight.json": True,
        "others/config/local.json": True, "others/config/local.example.json": False,
    }
    for name, expected in checks.items():
        result = subprocess.run(
            ["git", "-C", str(ROOT), "check-ignore", "--no-index", "-q", "--", name],
            capture_output=True,
        )
        if result.returncode not in (0, 1):
            failures.append("Git ignore check failed for " + name)
        elif (result.returncode == 0) != expected:
            failures.append("Unexpected ignore result: " + name)
    if failures:
        print("\n".join("FAIL: " + value for value in failures))
        return 1
    print(f"PASS: preparation files, local links, 5 business roles + 1 executor, retired E/F, scope isolation and {len(checks)} ignore cases")
    print("Application, model and installer readiness are not covered by this check.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
