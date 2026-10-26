"""Active T2 must never redirect B/C/D contract checks into A-executor's environment."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("c1_contract_tools", SCRIPTS / "contracts.py")
contracts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contracts)


class CandidateSelectionTests(unittest.TestCase):
    def test_only_registered_executor_branch_with_active_package_uses_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "executor"
            primary = Path(directory) / "main"
            file = root / "others/contracts/execution-delegations.json"
            file.parent.mkdir(parents=True)
            file.write_text(json.dumps({"packages": {"c1-runtime-public-integration": {
                "executor": "A-executor", "status": "active"}}}), encoding="utf-8")
            for branch in ("codex/b-core-a2", "codex/c-content-ai-a2", "codex/d-learning-ui-a2", "main"):
                with self.subTest(branch=branch), patch.object(contracts.subprocess, "check_output", return_value=branch):
                    self.assertFalse(contracts.uses_c1_candidate(root, primary))
            with patch.object(contracts.subprocess, "check_output", return_value="codex/a-executor"):
                self.assertTrue(contracts.uses_c1_candidate(root, primary))
                self.assertFalse(contracts.uses_c1_candidate(primary, primary))
                file.write_text(json.dumps({"packages": {"c1-runtime-public-integration": {
                    "executor": "A-executor", "status": "completed"}}}), encoding="utf-8")
                self.assertFalse(contracts.uses_c1_candidate(root, primary))


if __name__ == "__main__":
    unittest.main()
