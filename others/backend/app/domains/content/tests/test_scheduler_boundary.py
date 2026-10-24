import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.domains.content.parse_result import ResultError
from app.domains.content.parse_runner import ExecutionState
from app.domains.content.scheduler import ContentScheduler


class SchedulerBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_unconfirmed_stop_does_not_release_or_clear_budget(self):
        job, execution = uuid4(), uuid4()
        runner = AsyncMock()
        runner.stop.return_value = ExecutionState(execution, "running", False)
        driver = ContentScheduler(None, None, runner)
        with patch("app.domains.content.scheduler.task_store.cleaned") as cleaned:
            self.assertFalse(await driver._reap(job, execution))
            runner.release.assert_not_awaited()
            cleaned.assert_not_called()

    async def test_cleanup_confirmation_precedes_budget_release(self):
        job, execution = uuid4(), uuid4()
        runner = AsyncMock()
        runner.stop.return_value = ExecutionState(execution, "stopped", True)
        runner.release.return_value = False
        driver = ContentScheduler(None, None, runner)
        with patch("app.domains.content.scheduler.task_store.cleaned") as cleaned, \
                patch("app.domains.content.scheduler.task_store.stopped"):
            self.assertFalse(await driver._reap(job, execution))
            cleaned.assert_not_called()
            runner.release.return_value = True
            self.assertTrue(await driver._reap(job, execution))
            cleaned.assert_called_once_with(None, job, execution)

    async def test_mismatched_execution_handle_rejected(self):
        with self.assertRaises(ResultError):
            ContentScheduler._check_state(ExecutionState(uuid4(), "succeeded", True), uuid4())


if __name__ == "__main__":
    unittest.main()
