"""Local Git helpers for active SafeLabPlatform roles and scoped A executors."""
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


def identity(rules: dict, role: str) -> dict:
    if role in rules.get("retired_roles", {}):
        replacement = rules["retired_roles"][role]["replacement"]
        raise RuntimeError(f"Role {role} is retired; use {replacement}. Historical trees are preserved")
    identities = {**rules["roles"], **rules.get("executors", {})}
    if role not in identities:
        raise RuntimeError("Unknown active identity: " + role)
    return identities[role]


def executor_scope(root: Path, role: str, package: str | None) -> list[str]:
    name = "others/contracts/execution-delegations.json"
    published = committed_json(root, "main", name)
    local = json.loads((root / name).read_text(encoding="utf-8"))
    if local != published:
        raise RuntimeError("Outdated execution delegation; synchronize A's published work package")
    grant = published.get("packages", {}).get(package)
    if not grant or grant.get("executor") != role or grant.get("status") != "active":
        raise RuntimeError("An active A-approved work package is required for " + role)
    paths = grant.get("allowed_paths", [])
    if not paths or any(not isinstance(p, str) or not p or p in ("*", ".")
                        or "*" in p or "\\" in p or ":" in p or p.startswith("/")
                        or ".." in p.split("/") or p == ".git" or p.startswith(".git/") for p in paths):
        raise RuntimeError("Execution delegation requires explicit safe source paths")
    baseline = baseline_sha(root, grant["baseline_sha"])
    if git(root, "merge-base", "--is-ancestor", baseline, "HEAD", check=False).returncode:
        raise RuntimeError("Executor has not synchronized the work-package baseline")
    return paths


def committed_json(root: Path, reference: str, path: str, optional: bool = False) -> dict | None:
    result = git(root, "show", f"{reference}:{path}", check=False)
    if result.returncode and optional:
        return None
    if result.returncode:
        raise RuntimeError(f"Missing published {path} at {reference}")
    return json.loads(result.stdout)


def primary_root(root: Path) -> Path:
    common = git(root, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout.strip()
    return Path(common).resolve().parent


def registered_worktrees(root: Path) -> list[dict[str, str]]:
    listing = git(root, "-c", "core.quotepath=false", "worktree", "list", "--porcelain").stdout
    result = []
    for block in listing.strip().split("\n\n"):
        fields = dict(line.split(" ", 1) for line in block.splitlines() if " " in line)
        if "worktree" in fields:
            result.append(fields)
    return result


def role_location(root: Path, role: str, rules: dict) -> Path | None:
    owner = identity(rules, role)
    if role == "A":
        return primary_root(root)
    if owner["worktree"] is None:
        matches = [row for row in registered_worktrees(root)
                   if row.get("branch") == "refs/heads/" + owner["branch"]]
        if len(matches) > 1:
            raise RuntimeError("Role branch is checked out in multiple worktrees; preserve and inspect them")
        return Path(matches[0]["worktree"]).resolve() if matches else None
    parent = (primary_root(root) / rules["worktree_root"]).resolve()
    target = (parent / owner["worktree"]).resolve()
    if not target.is_relative_to(parent) or target == parent:
        raise RuntimeError("Invalid worktree destination")
    return target


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
    ownership = committed_json(root, head, "others/contracts/ownership.json", optional=True)
    published = committed_json(root, "main", "others/contracts/ownership.json")
    return {
        "path": str(root), "head": head, "clean": not changes, "changes": changes,
        "baseline": baseline, "contains_baseline": contains.returncode == 0,
        "behind": int(counts[0]), "ahead": int(counts[1]),
        "contract_version": version.get("version") if version else None,
        "ownership_version": ownership.get("version") if ownership else None,
        "ownership_current": ownership == published,
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
               baseline: str | None = None, package: str | None = None) -> dict:
    # Read published main rules, even when a task worktree still has an old copy.
    published = committed_json(root, "main", "others/contracts/ownership.json")
    rules = manifest(root) if role == "A" else published
    owner = dict(identity(rules, role))
    branch = git(root, "branch", "--show-current").stdout.strip()
    if branch != owner["branch"]:
        raise RuntimeError(f"Role {role} requires {owner['branch']}; current branch: {branch}")
    if role_location(root, role, rules) != root.resolve():
        raise RuntimeError("This is not the registered worktree for role " + role)
    if role != "A":
        if manifest(root) != published:
            raise RuntimeError("Outdated ownership rules; preserve changes and synchronize the published baseline")
        baseline = baseline_sha(root, baseline)
        if not readiness(root, baseline)["contains_baseline"]:
            raise RuntimeError("Worktree has not synchronized baseline " + baseline)
    if role in rules.get("executors", {}):
        owner["owned_paths"] = executor_scope(root, role, package)
    elif package:
        raise RuntimeError("--package is only valid for an executor")
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
    main = primary_root(root)
    rules = manifest(main)
    owner = identity(rules, role)
    if role == "A":
        raise RuntimeError("A uses the primary worktree")
    git(main, "rev-parse", "--verify", rules["base_branch"])
    target = role_location(main, role, rules)
    if target is None:
        raise RuntimeError("Role " + role + " uses an external worktree; A must register an existing Git worktree first")
    if target.exists():
        top = repository(target)
        branch = git(target, "branch", "--show-current").stdout.strip()
        if top == target and branch == owner["branch"]:
            return {"status": "already_exists", "role": role, "branch": branch,
                    **readiness(target, baseline_sha(main, baseline))}
        raise RuntimeError(f"Destination is occupied; keep existing files: {target}")
    if git(main, "status", "--porcelain").stdout.strip():
        raise RuntimeError("Commit or separately preserve primary-worktree changes before creating worktrees")
    target.parent.mkdir(parents=True, exist_ok=True)
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


def register_worktree(root: Path, role: str, path: Path, baseline: str | None = None) -> dict:
    """A binds an existing, clean worktree without overwriting files or branch history."""
    main = primary_root(root)
    if root.resolve() != main or git(root, "branch", "--show-current").stdout.strip() != "main":
        raise RuntimeError("Only A in the primary main worktree can register task worktrees")
    rules = committed_json(main, "main", "others/contracts/ownership.json")
    if manifest(main) != rules or git(main, "status", "--porcelain").stdout.strip():
        raise RuntimeError("Commit the primary worktree and published ownership before registration")
    owner = identity(rules, role)
    if owner["worktree"] is not None:
        raise RuntimeError("Role " + role + " has a managed path; use the worktree command")
    target = path.resolve()
    entries = registered_worktrees(main)
    entry = next((row for row in entries if Path(row["worktree"]).resolve() == target), None)
    if entry is None or target == main:
        raise RuntimeError("Target is not an existing task worktree of this repository")
    if repository(target) != target or primary_root(target) != main:
        raise RuntimeError("Target belongs to a different repository or worktree")
    before = readiness(target, baseline_sha(main, baseline))
    if not before["clean"]:
        raise RuntimeError("Target worktree has changes; preserve and commit them before registration")
    if not before["contains_baseline"]:
        raise RuntimeError("Target has not synchronized the requested registration baseline")
    branch = git(target, "branch", "--show-current").stdout.strip()
    if branch and branch != owner["branch"]:
        raise RuntimeError("Target already has a different branch; preserve it: " + branch)
    occupied = [row for row in entries if row.get("branch") == "refs/heads/" + owner["branch"]
                and Path(row["worktree"]).resolve() != target]
    if occupied:
        raise RuntimeError("Role branch is already used by another worktree; preserve both")
    if not branch:
        exists = git(main, "show-ref", "--verify", "--quiet", "refs/heads/" + owner["branch"], check=False)
        if exists.returncode == 0:
            if baseline_sha(main, owner["branch"]) != before["head"]:
                raise RuntimeError("Existing role branch points to a different commit; preserve its history")
            git(target, "switch", owner["branch"])
        elif exists.returncode == 1:
            git(target, "switch", "-c", owner["branch"])
        else:
            raise RuntimeError("Unable to inspect the role branch")
    return {"status": "already_registered" if branch else "registered", "role": role,
            "branch": owner["branch"], **readiness(target, before["baseline"])}


def status(root: Path, baseline: str | None = None) -> dict:
    resolved = baseline_sha(root, baseline)
    rules = committed_json(root, "main", "others/contracts/ownership.json")
    identities = {**rules["roles"], **rules.get("executors", {})}
    branches = {"refs/heads/" + value["branch"]: role for role, value in identities.items()}
    retired = {"refs/heads/" + value["branch"]: (role, value)
               for role, value in rules.get("retired_roles", {}).items()}
    worktrees = []
    for fields in registered_worktrees(root):
        path = Path(fields["worktree"])
        role = branches.get(fields.get("branch"))
        report = {"role": role, "branch": fields.get("branch"), **readiness(path, resolved)}
        if fields.get("branch") in retired:
            old_role, old = retired[fields["branch"]]
            report.update(role=old_role, historical=True, replacement=old["replacement"])
        report["registered"] = bool(role and role_location(root, role, rules) == path.resolve())
        report["ready"] = bool(report["registered"] and report["clean"]
                               and report["contains_baseline"] and report["ownership_current"])
        if role in rules.get("executors", {}):
            name = "others/contracts/execution-delegations.json"
            report["delegation_current"] = committed_json(path, "HEAD", name, optional=True) == committed_json(root, "main", name, optional=True)
            report["ready"] = report["ready"] and report["delegation_current"]
        worktrees.append(report)
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
    work = commands.add_parser("worktree", help="Create a registered active identity's worktree; preserve retired trees")
    choice = work.add_mutually_exclusive_group(required=True)
    choice.add_argument("--role", help="Active business role; E/F are retired")
    choice.add_argument("--executor", help="A executor identity, e.g. A-executor")
    choice.add_argument("--all", action="store_true")
    work.add_argument("--baseline", help="Baseline used to report existing-worktree readiness")
    register = commands.add_parser("register", help="A binds an existing clean external Git worktree to a role")
    registration = register.add_mutually_exclusive_group(required=True)
    registration.add_argument("--role")
    registration.add_argument("--executor")
    register.add_argument("--path", type=Path, required=True)
    register.add_argument("--baseline", help="Required ancestor; registration does not merge or synchronize files")
    commit = commands.add_parser("checkpoint", help="Commit only the selected role-owned changes")
    committer = commit.add_mutually_exclusive_group(required=True)
    committer.add_argument("--role")
    committer.add_argument("--executor")
    commit.add_argument("--package", help="A-approved execution-delegations package ID")
    commit.add_argument("--message", required=True)
    commit.add_argument("--check-note", required=True)
    commit.add_argument("--paths", nargs="+", required=True)
    commit.add_argument("--wip", action="store_true")
    commit.add_argument("--baseline", help="Required ancestor for task commits; default main")
    args = parser.parse_args()
    try:
        root = repository(Path.cwd())
        if args.command != "status":
            rules = committed_json(root, "main", "others/contracts/ownership.json")
            executor = getattr(args, "executor", None)
            if executor and executor not in rules.get("executors", {}):
                raise RuntimeError("Unknown executor: " + executor)
            if getattr(args, "role", None) in rules.get("executors", {}):
                raise RuntimeError("Executor must use --executor and an explicit work package")
        if args.command == "status":
            result = status(root, args.baseline)
        elif args.command == "worktree":
            roles = ([r for r in rules["roles"] if r != "A"] + list(rules.get("executors", {}))) if args.all else [args.role or args.executor]
            result = [new_worktree(root, role, args.baseline) for role in roles]
        elif args.command == "register":
            result = register_worktree(root, args.role or args.executor, args.path, args.baseline)
        else:
            result = checkpoint(root, args.role or args.executor, args.message, args.paths, args.check_note, args.wip, args.baseline, args.package)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
