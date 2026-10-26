"""P1 profile/tool checks only: no service, Docker, dependency install or database writes."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "others/backend"))
SPEC = importlib.util.spec_from_file_location("main_parser_prepare", ROOT / "others/deploy/content/prepare.py")
prepare = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prepare)


class MainParserProfileTests(unittest.TestCase):
    def test_fixed_primary_main_and_candidate_guards(self):
        with tempfile.TemporaryDirectory() as temporary:
            primary, child = Path(temporary) / "primary", Path(temporary) / "child"
            with patch.object(prepare, "ROOT", primary), patch.object(prepare, "primary_root", return_value=primary), \
                    patch.object(prepare.subprocess, "check_output", return_value="main\n"):
                settings = prepare.profile_settings("auto")
                self.assertEqual(settings["profile"], "main")
                self.assertEqual(settings["port"], 18767)
                self.assertEqual(Path(settings["worker"]), primary / "others/ai_worker/.venv/Scripts/python.exe")
                self.assertEqual(Path(settings["runtime"]), primary / "others/runtime/content-parser")
            for root, branch in [(primary, "feature"), (child, "main"), (child, "codex/a-executor")]:
                with self.subTest(root=root, branch=branch), patch.object(prepare, "ROOT", root), \
                        patch.object(prepare, "primary_root", return_value=primary), \
                        patch.object(prepare.subprocess, "check_output", return_value=branch):
                    with self.assertRaises(RuntimeError):
                        prepare.profile_settings("main")
            with patch.object(prepare, "primary_root", return_value=primary), \
                    patch.object(prepare.subprocess, "check_output", return_value="codex/a-executor"), \
                    patch("c1_candidate_env.validate", side_effect=RuntimeError("inactive")) as guard:
                with self.assertRaises(RuntimeError):
                    prepare.profile_settings("c1")
                guard.assert_called_once()

    def test_switch_keeps_unknown_executions_fenced(self):
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary)
            journal = runtime / "controller/journal"
            journal.mkdir(parents=True)
            old = {"image": "old", "protocol": "labconnect.parse-control/1", "root": str(runtime / "controller")}
            record = journal / "execution.json"
            for value in [{"released": False, "stop_confirmed": True}, {"released": True}]:
                record.write_text(json.dumps(value), encoding="utf-8")
                with self.assertRaises(RuntimeError):
                    prepare.require_released(runtime, old, "new", "labconnect.content-control/2")
            record.write_text(json.dumps({"released": True, "stop_confirmed": True}), encoding="utf-8")
            with self.assertRaises(RuntimeError):
                prepare.require_released(runtime, None, "new", "labconnect.content-control/2")
            before = record.read_bytes()
            prepare.require_released(runtime, old, "new", "labconnect.content-control/2")
            self.assertEqual(record.read_bytes(), before)

    def test_main_license_check_never_rewrites_accepted_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "installed/LICENSE"
            source.parent.mkdir()
            source.write_bytes(b"synthetic license\n")
            licenses = root / "accepted"
            licenses.mkdir()
            accepted = licenses / "demo-1-LICENSE"
            accepted.write_bytes(source.read_bytes())

            class Distribution:
                version = "1"
                files = [Path("demo.dist-info/LICENSE")]

                def locate_file(self, member):
                    return source

            packages = {"demo": {"version": "1", "source": {"registry": "https://pypi.org/simple"}, "wheels": []}}
            manifest = {"demo": {**packages["demo"], "files": {accepted.name: prepare.digest(accepted)}, "wheel_urls": []}}
            del manifest["demo"]["wheels"]
            evidence = licenses / "manifest.json"
            evidence.write_text(json.dumps(manifest), encoding="utf-8")
            before = {p.name: p.read_bytes() for p in licenses.iterdir()}
            with patch.object(prepare.importlib.metadata, "distribution", return_value=Distribution()):
                prepare.license_evidence(packages, licenses, readonly=True)
                source.write_bytes(b"changed license")
                with self.assertRaises(RuntimeError):
                    prepare.license_evidence(packages, licenses, readonly=True)
            self.assertEqual(before, {p.name: p.read_bytes() for p in licenses.iterdir()})

    def test_v2_main_port_requires_real_main_configuration(self):
        from app.core import content_runner as runner
        settings = {"protocol": runner.C1_PROTOCOL, "key": "x" * 40, "host": "127.0.0.1", "port": 18768}
        runner.DockerParseRunner(settings)
        with patch.object(runner, "main_control_configuration", return_value=False):
            with self.assertRaises(runner.RunnerUnavailable):
                runner.DockerParseRunner({**settings, "port": 18767})
        with patch.object(runner, "main_control_configuration", return_value=True):
            runner.DockerParseRunner({**settings, "port": 18767})
            with self.assertRaises(runner.RunnerUnavailable):
                runner.DockerParseRunner({**settings, "port": 18766})
        self.assertFalse(runner.main_control_configuration({**settings, "port": 18767}))
        with tempfile.TemporaryDirectory() as temporary:
            primary = Path(temporary).resolve()
            client = primary / "others/runtime/content-parser/parser-client.json"
            client.parent.mkdir(parents=True)
            main_settings = {**settings, "port": 18767}
            client.write_text(json.dumps(main_settings), encoding="utf-8")
            with patch.object(runner, "__file__", str(primary / "others/backend/app/core/content_runner.py")):
                with patch.object(runner.subprocess, "check_output", side_effect=[str(primary / ".git"), "main"]):
                    runner.DockerParseRunner(main_settings)
                with patch.object(runner.subprocess, "check_output", side_effect=[str(primary / ".git"), "main"]):
                    self.assertFalse(runner.main_control_configuration({**main_settings, "key": "different"}))
                with patch.object(runner.subprocess, "check_output", side_effect=[str(primary / ".git"), "feature"]):
                    self.assertFalse(runner.main_control_configuration(main_settings))


if __name__ == "__main__":
    unittest.main()
