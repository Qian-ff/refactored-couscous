"""Integration tests use disposable local repositories, never the user's branch or identity."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("safelab_workflow", ROOT / "others/scripts/workflow.py")
workflow = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(workflow)


class WorkflowTest(unittest.TestCase):
    def setUp(self) -> None:
        self.parent = (ROOT / "others/.tmp").resolve()
        self.parent.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="workflow-test-", dir=self.parent)
        self.repo = Path(self.temp.name).resolve()
        # Validate the absolute cleanup target before TemporaryDirectory can delete it.
        assert self.repo.is_relative_to(self.parent) and self.repo != self.parent
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Workflow Test Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        target = self.repo / "others/contracts/ownership.json"
        target.parent.mkdir(parents=True)
        target.write_text((ROOT / "others/contracts/ownership.json").read_text(encoding="utf-8"), encoding="utf-8")
        (self.repo / ".gitignore").write_text("/others/worktrees/\n", encoding="utf-8")
        self.git("add", ".gitignore", "others/contracts/ownership.json")
        self.git("commit", "-m", "test fixture baseline")

    def tearDown(self) -> None:
        assert self.repo.is_relative_to(self.parent) and self.repo != self.parent
        self.temp.cleanup()

    def git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(self.repo), *args], capture_output=True,
            encoding="utf-8", errors="replace",
        )
        if result.returncode:
            raise AssertionError(result.stderr)
        return result.stdout.strip()

    def write(self, relative: str, text: str = "example\n") -> None:
        file = self.repo / relative
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text, encoding="utf-8")

    def test_selected_commit_and_no_empty_commit(self) -> None:
        self.write("readme.txt")
        result = workflow.checkpoint(self.repo, "A", "test: checkpoint", ["readme.txt"], "fixture check: PASS", False)
        self.assertEqual(result["status"], "committed")
        self.assertEqual(self.git("status", "--porcelain"), "")
        result = workflow.checkpoint(self.repo, "A", "test: unchanged", ["readme.txt"], "no changes", False)
        self.assertEqual(result["status"], "no_changes")

    def test_unrelated_staged_change_is_preserved(self) -> None:
        self.write("one.txt")
        self.write("two.txt")
        self.git("add", "two.txt")
        with self.assertRaisesRegex(RuntimeError, "Unrelated staged"):
            workflow.checkpoint(self.repo, "A", "test", ["one.txt"], "check: PASS", False)
        self.assertEqual(self.git("diff", "--cached", "--name-only"), "two.txt")
        self.assertEqual(self.git("log", "-1", "--format=%s"), "test fixture baseline")

    def test_wrong_role_branch_is_rejected(self) -> None:
        self.write("web/src/features/admin/example.txt")
        with self.assertRaisesRegex(RuntimeError, "requires task/core"):
            workflow.checkpoint(self.repo, "B", "test", ["web/src/features/admin"], "check: PASS", False)

    def test_role_scope_is_enforced(self) -> None:
        self.git("switch", "-c", "task/core")
        self.write("desktop/example.txt")
        with self.assertRaisesRegex(RuntimeError, "outside this role"):
            workflow.checkpoint(self.repo, "B", "test", ["desktop/example.txt"], "check: PASS", False)

    def test_path_cannot_leave_worktree(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "leaves this worktree"):
            workflow.normalized_paths(self.repo, ["../outside.txt"])

    def test_isolated_worktree_and_role_commit(self) -> None:
        result = workflow.new_worktree(self.repo, "B")
        target = Path(result["path"])
        self.assertEqual(workflow.git(target, "branch", "--show-current").stdout.strip(), "task/core")
        self.assertTrue((target / ".git").is_file())
        file = target / "web/src/features/admin/example.txt"
        file.parent.mkdir(parents=True)
        file.write_text("role-owned\n", encoding="utf-8")
        committed = workflow.checkpoint(target, "B", "test: role work", ["web/src/features/admin"], "fixture: PASS", False)
        self.assertEqual(committed["branch"], "task/core")
        self.assertFalse((self.repo / "web/src/features/admin/example.txt").exists())
        self.assertNotEqual(committed["commit"], self.git("rev-parse", "main"))
        self.assertEqual(workflow.new_worktree(self.repo, "B")["status"], "already_exists")


if __name__ == "__main__":
    unittest.main()
