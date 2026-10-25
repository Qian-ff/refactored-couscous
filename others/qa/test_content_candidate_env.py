"""Candidate locks are distinct from main and checked before every invocation."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("content_candidate_env", SCRIPTS / "content_candidate_env.py")
candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)


class CandidateEnvironmentTests(unittest.TestCase):
    def test_lock_and_descriptor_both_change_fingerprint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pyproject.toml").write_text("project")
            (root / "uv.lock").write_text("lock")
            first = candidate.fingerprint(root)
            (root / "uv.lock").write_text("new-lock")
            second = candidate.fingerprint(root)
            (root / "pyproject.toml").write_text("new-project")
            self.assertNotEqual(first, second)
            self.assertNotEqual(second, candidate.fingerprint(root))

    def test_environments_stay_in_this_checkout_ignored_runtime(self):
        for surface in ("backend", "worker"):
            _project, environment, _python = candidate.paths(surface)
            self.assertTrue(environment.is_relative_to(candidate.ROOT / "others/runtime/c02-public/envs"))
            self.assertNotIn(".venv", environment.parts)


if __name__ == "__main__":
    unittest.main()
