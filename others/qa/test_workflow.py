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
        self.sandbox = Path(self.temp.name).resolve()
        self.repo = self.sandbox / "repository"
        self.repo.mkdir()
        # Validate the absolute cleanup target before TemporaryDirectory can delete it.
        assert self.repo.is_relative_to(self.parent) and self.repo != self.parent
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Workflow Test Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        target = self.repo / "others/contracts/ownership.json"
        target.parent.mkdir(parents=True)
        self.rules = json.loads((ROOT / "others/contracts/ownership.json").read_text(encoding="utf-8"))
        # Keep legacy managed-path scenarios, independently of the host's external locations.
        self.rules["roles"]["B"]["worktree"] = "core"
        self.b_branch = self.rules["roles"]["B"]["branch"]
        target.write_text(json.dumps(self.rules), encoding="utf-8")
        (self.repo / ".gitignore").write_text("/others/worktrees/\n", encoding="utf-8")
        self.git("add", ".gitignore", "others/contracts/ownership.json")
        self.git("commit", "-m", "test fixture baseline")

    def tearDown(self) -> None:
        assert self.sandbox.is_relative_to(self.parent) and self.sandbox != self.parent
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

    def publish_external_b(self) -> str:
        self.rules["version"] += 1
        self.rules["roles"]["B"]["worktree"] = None
        self.write("others/contracts/ownership.json", json.dumps(self.rules))
        self.git("add", "others/contracts/ownership.json")
        self.git("commit", "-m", "publish external B registration")
        return self.git("rev-parse", "main")

    def external_tree(self, name: str = "external tree", reference: str = "main") -> Path:
        target = (self.sandbox / name).resolve()
        assert target.is_relative_to(self.sandbox) and target != self.sandbox
        self.git("worktree", "add", "--detach", str(target), reference)
        return target

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
        with self.assertRaisesRegex(RuntimeError, "requires " + self.b_branch):
            workflow.checkpoint(self.repo, "B", "test", ["web/src/features/admin"], "check: PASS", False)

    def test_role_scope_is_enforced(self) -> None:
        target = Path(workflow.new_worktree(self.repo, "B")["path"])
        file = target / "desktop/example.txt"
        file.parent.mkdir(parents=True)
        file.write_text("keep", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "outside this role"):
            workflow.checkpoint(target, "B", "test", ["desktop/example.txt"], "check: PASS", False)

    def test_path_cannot_leave_worktree(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "leaves this worktree"):
            workflow.normalized_paths(self.repo, ["../outside.txt"])

    def test_status_reports_dirty_and_outdated_worktrees(self) -> None:
        target = Path(workflow.new_worktree(self.repo, "B")["path"])
        self.write("baseline.txt")
        self.git("add", "baseline.txt")
        self.git("commit", "-m", "new published baseline")
        (target / "uncommitted.txt").write_text("keep me", encoding="utf-8")
        report = workflow.status(self.repo, self.git("rev-parse", "main"))
        task = next(item for item in report["worktrees"] if item["role"] == "B")
        self.assertFalse(task["clean"])
        self.assertFalse(task["contains_baseline"])
        self.assertEqual(task["behind"], 1)
        self.assertIn("?? uncommitted.txt", task["changes"])
        again = workflow.new_worktree(self.repo, "B")
        self.assertEqual(again["status"], "already_exists")
        self.assertFalse(again["contains_baseline"])
        self.assertEqual((target / "uncommitted.txt").read_text(), "keep me")

    def test_published_scope_change_rejects_stale_task_rules(self) -> None:
        target = Path(workflow.new_worktree(self.repo, "B")["path"])
        rules = json.loads((self.repo / "others/contracts/ownership.json").read_text(encoding="utf-8"))
        rules["version"] += 1
        self.write("others/contracts/ownership.json", json.dumps(rules))
        self.git("add", "others/contracts/ownership.json")
        self.git("commit", "-m", "publish new ownership")
        file = target / "web/src/features/admin/keep.txt"
        file.parent.mkdir(parents=True)
        file.write_text("preserve", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "Outdated ownership"):
            workflow.checkpoint(target, "B", "test", ["web/src/features/admin"], "check", False)
        self.assertEqual(file.read_text(), "preserve")

    def test_unsynchronized_and_invalid_baselines_are_rejected(self) -> None:
        target = Path(workflow.new_worktree(self.repo, "B")["path"])
        self.write("baseline.txt")
        self.git("add", "baseline.txt")
        self.git("commit", "-m", "advance main")
        with self.assertRaisesRegex(RuntimeError, "has not synchronized"):
            workflow.checkpoint(target, "B", "test", ["web/src/features/admin"], "check", False)
        with self.assertRaisesRegex(RuntimeError, "Unknown baseline"):
            workflow.status(self.repo, "nonexistent-baseline")

    def test_isolated_worktree_and_role_commit(self) -> None:
        result = workflow.new_worktree(self.repo, "B")
        target = Path(result["path"])
        self.assertEqual(workflow.git(target, "branch", "--show-current").stdout.strip(), self.b_branch)
        self.assertTrue((target / ".git").is_file())
        file = target / "web/src/features/admin/example.txt"
        file.parent.mkdir(parents=True)
        file.write_text("role-owned\n", encoding="utf-8")
        committed = workflow.checkpoint(target, "B", "test: role work", ["web/src/features/admin"], "fixture: PASS", False)
        self.assertEqual(committed["branch"], self.b_branch)
        self.assertFalse((self.repo / "web/src/features/admin/example.txt").exists())
        self.assertNotEqual(committed["commit"], self.git("rev-parse", "main"))
        self.assertEqual(workflow.new_worktree(self.repo, "B")["status"], "already_exists")

    def test_external_registration_and_owned_commit(self) -> None:
        baseline = self.publish_external_b()
        target = self.external_tree()
        registered = workflow.register_worktree(self.repo, "B", target, baseline)
        self.assertEqual(registered["status"], "registered")
        self.assertEqual(registered["branch"], self.b_branch)
        self.assertEqual(workflow.new_worktree(self.repo, "B")["path"], str(target))
        self.assertEqual(workflow.register_worktree(self.repo, "B", target)["status"], "already_registered")
        file = target / "web/src/features/admin/record.txt"
        file.parent.mkdir(parents=True)
        file.write_text("role-owned", encoding="utf-8")
        workflow.checkpoint(target, "B", "test external commit", ["web/src/features/admin"], "PASS", False, baseline)
        row = next(w for w in workflow.status(self.repo, baseline)["worktrees"] if w["role"] == "B")
        self.assertTrue(row["registered"])
        self.assertTrue(row["ready"])
        self.assertTrue(row["ownership_current"])
        self.assertFalse((self.repo / "web/src/features/admin/record.txt").exists())

    def test_external_role_is_not_automatically_created(self) -> None:
        self.publish_external_b()
        with self.assertRaisesRegex(RuntimeError, "must register"):
            workflow.new_worktree(self.repo, "B")
        self.assertFalse((self.repo / "others/worktrees/core").exists())

    def test_registration_preserves_dirty_target(self) -> None:
        self.publish_external_b()
        target = self.external_tree()
        (target / "keep.txt").write_text("keep my changes", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "Target worktree has changes"):
            workflow.register_worktree(self.repo, "B", target)
        self.assertEqual(workflow.git(target, "branch", "--show-current").stdout.strip(), "")
        self.assertEqual((target / "keep.txt").read_text(), "keep my changes")

    def test_registration_rejects_foreign_repository(self) -> None:
        self.publish_external_b()
        foreign = self.sandbox / "foreign"
        foreign.mkdir()
        workflow.git(foreign, "init", "-b", "main")
        with self.assertRaisesRegex(RuntimeError, "not an existing task worktree"):
            workflow.register_worktree(self.repo, "B", foreign)

    def test_registration_preserves_existing_branch_history(self) -> None:
        baseline = self.publish_external_b()
        target = self.external_tree()
        self.git("branch", self.b_branch, "main~1")
        original = self.git("rev-parse", self.b_branch)
        with self.assertRaisesRegex(RuntimeError, "different commit"):
            workflow.register_worktree(self.repo, "B", target, baseline)
        self.assertEqual(self.git("rev-parse", self.b_branch), original)
        self.assertEqual(workflow.git(target, "branch", "--show-current").stdout.strip(), "")

    def test_registration_preserves_occupied_role_branch(self) -> None:
        self.publish_external_b()
        first = self.external_tree("first")
        workflow.register_worktree(self.repo, "B", first)
        second = self.external_tree("second")
        with self.assertRaisesRegex(RuntimeError, "already used"):
            workflow.register_worktree(self.repo, "B", second)
        self.assertEqual(workflow.git(first, "branch", "--show-current").stdout.strip(), self.b_branch)
        self.assertEqual(workflow.git(second, "branch", "--show-current").stdout.strip(), "")

    def test_registration_requires_primary_and_clean_main(self) -> None:
        self.publish_external_b()
        target = self.external_tree()
        with self.assertRaisesRegex(RuntimeError, "Only A"):
            workflow.register_worktree(target, "B", target)
        self.write("keep-main.txt", "keep main work")
        with self.assertRaisesRegex(RuntimeError, "Commit the primary worktree"):
            workflow.register_worktree(self.repo, "B", target)
        self.assertEqual((self.repo / "keep-main.txt").read_text(), "keep main work")

    def test_registration_does_not_hide_stale_ownership_or_sync_files(self) -> None:
        old = self.git("rev-parse", "main")
        self.publish_external_b()
        target = self.external_tree(reference=old)
        workflow.register_worktree(self.repo, "B", target, old)
        row = next(w for w in workflow.status(self.repo, old)["worktrees"] if w["role"] == "B")
        self.assertTrue(row["contains_baseline"])
        self.assertFalse(row["ownership_current"])
        self.assertFalse(row["ready"])
        self.assertEqual(workflow.git(target, "rev-parse", "HEAD").stdout.strip(), old)
        with self.assertRaisesRegex(RuntimeError, "Outdated ownership"):
            workflow.checkpoint(target, "B", "must wait", ["web"], "not ready", False, old)

    def test_registration_preserves_other_branch_and_rejects_old_baseline(self) -> None:
        self.publish_external_b()
        target = self.external_tree()
        workflow.git(target, "switch", "-c", "other-feature")
        with self.assertRaisesRegex(RuntimeError, "different branch"):
            workflow.register_worktree(self.repo, "B", target)
        self.write("new-baseline.txt")
        self.git("add", "new-baseline.txt")
        self.git("commit", "-m", "advance required baseline")
        with self.assertRaisesRegex(RuntimeError, "requested registration baseline"):
            workflow.register_worktree(self.repo, "B", target)
        self.assertEqual(workflow.git(target, "branch", "--show-current").stdout.strip(), "other-feature")


if __name__ == "__main__":
    unittest.main()
