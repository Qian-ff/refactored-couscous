"""Verify that shared dependencies never silently select another checkout's backend."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "others/scripts"))
import shared_env  # noqa: E402


class SharedEnvironmentTest(unittest.TestCase):
    def setUp(self):
        self.parent = (ROOT / "others/.tmp").resolve()
        self.parent.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="shared-env-test-", dir=self.parent)
        self.sandbox = Path(self.temp.name).resolve()
        assert self.sandbox.is_relative_to(self.parent) and self.sandbox != self.parent
        self.primary = self.sandbox / "primary"
        self.child = self.sandbox / "child"
        self.primary.mkdir()
        self.child.mkdir()

    def tearDown(self):
        assert self.sandbox.is_relative_to(self.parent) and self.sandbox != self.parent
        self.temp.cleanup()

    def test_dependency_mismatch_stops_reuse_without_changing_either_tree(self):
        for name in shared_env.BACKEND_INPUTS:
            for root in (self.primary, self.child):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("same", encoding="utf-8")
        shared_env.require_compatible(self.child, self.primary, shared_env.BACKEND_INPUTS)
        lock = self.child / shared_env.BACKEND_INPUTS[1]
        lock.write_text("branch-only version", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "Dependency inputs differ"):
            shared_env.require_compatible(self.child, self.primary, shared_env.BACKEND_INPUTS)
        self.assertEqual(lock.read_text(), "branch-only version")
        self.assertEqual((self.primary / shared_env.BACKEND_INPUTS[1]).read_text(), "same")

    def test_competing_database_test_process_is_rejected_and_lock_is_released(self):
        code = "from pathlib import Path; from shared_env import database_test_lock; " \
               "guard=database_test_lock(Path(__import__('sys').argv[1])); guard.__enter__()"
        with shared_env.database_test_lock(self.primary):
            result = subprocess.run([sys.executable, "-c", code, str(self.primary)],
                                    cwd=ROOT / "others/scripts", capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Another shared backend test run is active", result.stderr)
        with shared_env.database_test_lock(self.primary):
            pass

    def bootstrap(self, child: Path):
        interpreter = ROOT / "others/backend/.venv/Scripts/python.exe"
        if not interpreter.exists():
            self.skipTest("Shared Python environment is not configured on this machine")
        return subprocess.run([str(interpreter), "-c", shared_env.BOOTSTRAP,
                               str(child), str(self.primary), "__probe__"],
                              capture_output=True, text=True, encoding="utf-8")

    def fixture_configuration(self, directory: Path, content: str):
        target = (directory / ".env").resolve()
        assert self.sandbox.is_relative_to((ROOT / "others/.tmp").resolve())
        assert target.is_relative_to(self.sandbox) and target != (ROOT / ".env").resolve()
        target.write_text(content, encoding="utf-8")

    def test_shared_interpreter_selects_each_checkout_and_keeps_secrets_out_of_report(self):
        secret = "fixture-secret-must-not-appear"
        self.fixture_configuration(self.primary, "DATABASE_URL=fixture\nSECRET_KEY=" + secret)
        for name in ("first", "second"):
            child = self.sandbox / name
            package = child / "others/backend/app"
            package.mkdir(parents=True)
            (package / "__init__.py").write_text("", encoding="utf-8")
            result = self.bootstrap(child)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(Path(report["app_source"]), package / "__init__.py")
            self.assertTrue(report["configuration_loaded"])
            self.assertNotIn(secret, result.stdout + result.stderr)

    def test_missing_child_package_cannot_fall_back_to_primary_editable_install(self):
        (self.child / "others/backend").mkdir(parents=True)
        result = self.bootstrap(self.child)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Backend import resolved outside the selected worktree", result.stderr)

    def test_schema_export_uses_selected_tree_even_with_shared_interpreter(self):
        interpreter = ROOT / "others/backend/.venv/Scripts/python.exe"
        if not interpreter.exists():
            self.skipTest("Shared backend is not configured")
        fixture_shared = self.sandbox / "schema-fixture-only"
        fixture_shared.mkdir()
        self.fixture_configuration(fixture_shared, "DATABASE_URL=fixture\nSECRET_KEY=private-fixture")
        for name in ("first", "second"):
            child = self.sandbox / (name + "-schema")
            package = child / "others/backend/app"
            package.mkdir(parents=True)
            (package / "__init__.py").write_text("", encoding="utf-8")
            (package / "main.py").write_text(
                "from types import SimpleNamespace\napp=SimpleNamespace(openapi=lambda: "
                + repr({"info":{"version":name}}) + ")\n", encoding="utf-8")
            result = subprocess.run([str(interpreter),"-c",shared_env.BOOTSTRAP,
                str(child),str(fixture_shared),"__openapi__"], capture_output=True,text=True,encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["info"]["version"], name)
            self.assertNotIn("private-fixture", result.stdout)

    def test_worker_runs_selected_tree_module_with_shared_model_cache(self):
        interpreter = ROOT / "others/ai_worker/.venv/Scripts/python.exe"
        if not interpreter.exists():
            self.skipTest("Separate worker environment has not been prepared")
        for name in ("first", "second"):
            child = self.sandbox / name
            package = child / "others/ai_worker/speech"
            package.mkdir(parents=True)
            (package / "__init__.py").write_text("", encoding="utf-8")
            (package / "binding_probe.py").write_text(
                "import json,os; print(json.dumps({'source':__file__,'models':os.environ['LABCONNECT_MODEL_ROOT']}))",
                encoding="utf-8")
            result = subprocess.run([str(interpreter), "-c", shared_env.WORKER_BOOTSTRAP,
                str(child), str(self.primary), "speech.binding_probe"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(Path(report["source"]), package / "binding_probe.py")
            self.assertEqual(Path(report["models"]), self.primary / "others/models")

    def test_worker_rejects_module_from_the_interpreter_installation(self):
        interpreter = ROOT / "others/ai_worker/.venv/Scripts/python.exe"
        if not interpreter.exists():
            self.skipTest("Separate worker environment has not been prepared")
        (self.child / "others/ai_worker").mkdir(parents=True)
        result = subprocess.run([str(interpreter), "-c", shared_env.WORKER_BOOTSTRAP,
            str(self.child), str(self.primary), "json"], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Worker module resolved outside the selected worktree", result.stderr)


if __name__ == "__main__":
    unittest.main()
