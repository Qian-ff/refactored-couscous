import asyncio
import unittest
from dataclasses import replace
from uuid import uuid4

from app.domains.content.parse_runner import RunnerCapabilities, RunnerUnavailable, UnavailableRunner


class RunnerContractTests(unittest.TestCase):
    def setUp(self):
        self.capabilities = RunnerCapabilities(
            "labconnect.parse/1", "sha256:" + "a" * 64,
            True, True, True, True, True, True, True, True,
            384 * 1024 * 1024, 1, 64 * 1024 * 1024, 64, 60, 16 * 1024 * 1024, 64 * 1024,
        )

    def test_declared_limits_validation(self):
        self.capabilities.require_supported()
        for change in ({"no_network": False}, {"memory_bytes": 0}, {"memory_bytes": 1024**3},
                       {"stop_confirmation": False}, {"global_exclusion": False},
                       {"image_digest": "latest"}, {"cpu_limit": float("nan")},
                       {"pids_limit": True}, {"stderr_bytes": 1024 * 1024}):
            with self.subTest(change=change), self.assertRaises(RunnerUnavailable):
                replace(self.capabilities, **change).require_supported()

    def test_missing_adapter_never_claims_execution_or_stop(self):
        runner = UnavailableRunner()
        for method, args in ((runner.capabilities, ()), (runner.inspect, (uuid4(),)),
                             (runner.stop, (uuid4(),)), (runner.result, (uuid4(),))):
            with self.subTest(method=method.__name__), self.assertRaises(RunnerUnavailable):
                asyncio.run(method(*args))


if __name__ == "__main__":
    unittest.main()
