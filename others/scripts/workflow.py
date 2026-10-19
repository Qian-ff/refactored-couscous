"""Local Git helpers for the seven SafeLabPlatform roles. Python 3.10+, stdlib."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

PROJECT = Path(__file__).resolve().parents[2]


def git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never")
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True,
        text=True, encoding="utf-8", errors="replace", env=env,
    )
    if check and result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Git failed")
    return result


def manifest(root: Path) -> dict:
    return json.loads((root / "others/contracts/ownership.json").read_text(encoding="utf-8"))


def committed_json(root: Path, reference: str, path: str, optional: bool = False) -> dict | None:
    result = git(root, "show", f"{reference}:{path}", check=False)
    if result.returncode and optional:
        return None
    if result.returncode:
        raise RuntimeError(f"Missing published {path} at {reference}")
    return json.loads(result.stdout)


def baseline_sha(root: Path, reference: str | None = None) -> str:
    reference = reference or "main"
    result = git(root, "rev-parse", "--verify", "--end-of-options", reference + "^{commit}", check=False)
    if result.returncode:
        raise RuntimeError("Unknown baseline: " + reference)
    return result.stdout.strip()


def readiness(root: Path, baseline: str) -> dict:
    head = git(root, "rev-parse", "HEAD").stdout.strip()
    changes = git(root, "status", "--porcelain").stdout.splitlines()
    contains = git(root, "merge-base", "--is-ancestor", baseline, head, check=False)
    if contains.returncode not in (0, 1):
        raise RuntimeError("Cannot compare worktree to baseline")
    counts = git(root, "rev-list", "--left-right", "--count", baseline + "..." + head).stdout.split()
    version = committed_json(root, head, "others/contracts/version.json", optional=True)
    return {
        "path": str(root), "head": head, "clean": not changes, "changes": changes,
        "baseline": baseline, "contains_baseline": contains.returncode == 0,
        "behind": int(counts[0]), "ahead": int(counts[1]),
        "contract_version": version.get("version") if version else None,
    }


def repository(path: Path) -> Path:
    return Path(git(path, "rev-parse", "--show-toplevel").stdout.strip()).resolve()


def selected(path: str, paths: list[str]) -> bool:
    return any(p == "." or path == p or path.startswith(p.rstrip("/") + "/") for p in paths)


def owned(path: str, scopes: list[str]) -> bool:
    return "*" in scopes or any(
        path == scope.rstrip("/") or (scope.endswith("/") and path.startswith(scope))
        for scope in scopes
    )


def paths_from_git(root: Path, *args: str) -> list[str]:
    return [p for p in git(root, *args).stdout.split("\0") if p]


def normalized_paths(root: Path, paths: list[str]) -> list[str]:
    normalized = []
    for value in paths:
        candidate = (root / value).resolve()
        if not candidate.is_relative_to(root):
            raise RuntimeError(f"Path leaves this worktree: {value}")
        relative = candidate.relative_to(root).as_posix()
        if relative == ".git" or relative.startswith(".git/"):
            raise RuntimeError("Git metadata is not a source path")
        normalized.append(relative)
    return list(dict.fromkeys(normalized))


def checkpoint(root: Path, role: str, message: str, paths: list[str], note: str, wip: bool,
               baseline: str | None = None) -> dict:
    # Read published main rules, even when a task worktree still has an old copy.
    published = committed_json(root, "main", "others/contracts/ownership.json")
    rules = manifest(root) if role == "A" else published
    owner = rules["roles"][role]
    branch = git(root, "branch", "--show-current").stdout.strip()
    if branch != owner["branch"]:
        raise RuntimeError(f"Role {role} requires {owner['branch']}; current branch: {branch}")
    if role != "A":
        if manifest(root) != published:
            raise RuntimeError("Outdated ownership rules; preserve changes and synchronize the published baseline")
        baseline = baseline_sha(root, baseline)
        if not readiness(root, baseline)["contains_baseline"]:
            raise RuntimeError("Worktree has not synchronized baseline " + baseline)
    if not message.strip() or not note.strip():
        raise RuntimeError("A commit message and truthful check note are required")
    for key in ("user.name", "user.email"):
        if not git(root, "config", "--get", key, check=False).stdout.strip():
            raise RuntimeError(f"Missing {key}; obtain the user's project-local identity first")
    requested = normalized_paths(root, paths)
    already_staged = paths_from_git(root, "diff", "--cached", "--name-only", "-z")
    unrelated = [p for p in already_staged if not selected(p, requested)]
    if unrelated:
        raise RuntimeError("Unrelated staged files; preserve and review them: " + ", ".join(unrelated))
    candidates = paths_from_git(
        root, "ls-files", "-z", "--modified", "--deleted", "--others",
        "--exclude-standard", "--", *requested,
    )
    outside = [p for p in candidates + already_staged if not owned(p, owner["owned_paths"])]
    if outside:
        raise RuntimeError("Paths outside this role; ask A to integrate: " + ", ".join(sorted(set(outside))))
    git(root, "diff", "--check", "--", *requested)
    git(root, "add", "--", *requested)
    staged = paths_from_git(root, "diff", "--cached", "--name-only", "-z")
    if not staged:
        head = git(root, "rev-parse", "--verify", "HEAD", check=False)
        return {"status": "no_changes", "branch": branch, "commit": head.stdout.strip() or None}
    if any(not selected(p, requested) or not owned(p, owner["owned_paths"]) for p in staged):
        raise RuntimeError("Staged paths changed unexpectedly; review the index before committing")
    git(root, "diff", "--cached", "--check")
    final_message = ("wip: " if wip else "") + message.strip()
    git(root, "commit", "-m", final_message, "-m", "Checks: " + note.strip())
    return {
        "status": "committed", "branch": branch,
        "commit": git(root, "rev-parse", "HEAD").stdout.strip(),
        "files": staged, "checks": note, "wip": wip,
    }


def new_worktree(root: Path, role: str, baseline: str | None = None) -> dict:
    common = Path(git(root, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout.strip())
    main = common.parent.resolve()
    rules = manifest(main)
    owner = rules["roles"][role]
    if role == "A":
        raise RuntimeError("A uses the primary worktree")
    git(main, "rev-parse", "--verify", rules["base_branch"])
    parent = (main / rules["worktree_root"]).resolve()
    target = (parent / owner["worktree"]).resolve()
    if not target.is_relative_to(parent) or target == parent:
        raise RuntimeError("Invalid worktree destination")
    if target.exists():
        top = repository(target)
        branch = git(target, "branch", "--show-current").stdout.strip()
        if top == target and branch == owner["branch"]:
            return {"status": "already_exists", "role": role, "branch": branch,
                    **readiness(target, baseline_sha(main, baseline))}
        raise RuntimeError(f"Destination is occupied; keep existing files: {target}")
    if git(main, "status", "--porcelain").stdout.strip():
        raise RuntimeError("Commit or separately preserve primary-worktree changes before creating worktrees")
    parent.mkdir(parents=True, exist_ok=True)
    exists = git(main, "show-ref", "--verify", "--quiet", "refs/heads/" + owner["branch"], check=False)
    if exists.returncode == 0:
        git(main, "worktree", "add", str(target), owner["branch"])
    elif exists.returncode == 1:
        git(main, "worktree", "add", "-b", owner["branch"], str(target), rules["base_branch"])
    else:
        raise RuntimeError("Unable to inspect the task branch")
    return {
        "status": "created", "role": role, "branch": owner["branch"], "path": str(target),
        "baseline": git(target, "rev-parse", "HEAD").stdout.strip(),
    }


def status(root: Path, baseline: str | None = None) -> dict:
    resolved = baseline_sha(root, baseline)
    rules = committed_json(root, "main", "others/contracts/ownership.json")
    branches = {"refs/heads/" + value["branch"]: role for role, value in rules["roles"].items()}
    worktrees = []
    for block in git(root, "worktree", "list", "--porcelain").stdout.strip().split("\n\n"):
        fields = dict(line.split(" ", 1) for line in block.splitlines() if " " in line)
        path = Path(fields["worktree"])
        worktrees.append({"role": branches.get(fields.get("branch")),
                          "branch": fields.get("branch"), **readiness(path, resolved)})
    return {
        "root": str(root),
        "branch": git(root, "branch", "--show-current").stdout.strip(),
        "commit": git(root, "rev-parse", "--verify", "HEAD", check=False).stdout.strip() or None,
        "changes": git(root, "status", "--short").stdout.splitlines(),
        "origin": git(root, "remote", "get-url", "origin", check=False).stdout.strip() or None,
        "baseline": resolved,
        "worktrees": worktrees,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("status")
    inspect.add_argument("--baseline", help="Published commit SHA or ref; default main")
    work = commands.add_parser("worktree", help="Create one isolated task worktree, or all B-G")
    choice = work.add_mutually_exclusive_group(required=True)
    choice.add_argument("--role", choices=list("BCDEFG"))
    choice.add_argument("--all", action="store_true")
    work.add_argument("--baseline", help="Baseline used to report existing-worktree readiness")
    commit = commands.add_parser("checkpoint", help="Commit only the selected role-owned changes")
    commit.add_argument("--role", choices=list("ABCDEFG"), required=True)
    commit.add_argument("--message", required=True)
    commit.add_argument("--check-note", required=True)
    commit.add_argument("--paths", nargs="+", required=True)
    commit.add_argument("--wip", action="store_true")
    commit.add_argument("--baseline", help="Required ancestor for task commits; default main")
    args = parser.parse_args()
    try:
        root = repository(Path.cwd())
        if args.command == "status":
            result = status(root, args.baseline)
        elif args.command == "worktree":
            roles = list("BCDEFG") if args.all else [args.role]
            result = [new_worktree(root, role, args.baseline) for role in roles]
        else:
            result = checkpoint(root, args.role, args.message, args.paths, args.check_note, args.wip, args.baseline)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
