import unittest
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError

from app.domains.content.questions import transfers
from app.domains.content.questions.transfers import ExportCreate, ImportCreate, TaskGeneration, TransferAdmission, check_retryable


class TransferTests(unittest.TestCase):
    def test_requests_bind_exact_format_size_fixed_versions_and_generation(self):
        valid = {"library_id": uuid4(), "format": "csv", "expected_bytes": 1048576, "input_hash": "a" * 64}
        ImportCreate.model_validate(valid)
        for change in ({"expected_bytes": 1048577}, {"expected_bytes": True}, {"format": "pdf"},
                       {"input_hash": "invalid"}, {"file_key": "../private"}):
            with self.subTest(change=change), self.assertRaises(ValidationError):
                ImportCreate.model_validate({**valid, **change})
        version_id = uuid4()
        with self.assertRaises(ValidationError):
            ExportCreate(library_id=uuid4(), format="xlsx", version_ids=[version_id, version_id], authorization_statement="teaching")
        with self.assertRaises(ValidationError):
            TaskGeneration(generation=True)

    def test_missing_global_queue_hook_fails_before_using_database(self):
        with self.assertRaises(HTTPException) as missing:
            TransferAdmission().admit(None, uuid4(), receiving=True)
        self.assertEqual(missing.exception.status_code, 503)

    def test_retry_requires_stop_cleanup_original_and_the_exact_generation(self):
        original = dict(generation=3, state="failed", stop_confirmed=True, reserved_bytes=0, kind="import", input_sealed=True)
        check_retryable(SimpleNamespace(**original), 3)
        for change in ({"generation": 4}, {"state": "succeeded"}, {"stop_confirmed": False},
                       {"reserved_bytes": 1}, {"input_sealed": False}):
            with self.subTest(change=change), self.assertRaises(HTTPException):
                check_retryable(SimpleNamespace(**{**original, **change}), 3)
        check_retryable(SimpleNamespace(**{**original, "kind": "export", "input_sealed": False}), 3)

    def test_download_rejects_unfinished_and_malformed_outputs(self):
        original = dict(kind="export", state="succeeded", result_hash="a" * 64, result_bytes=100,
                        format="csv", file_key=uuid4().hex + ".blob")
        for change in ({"state": "running"}, {"result_hash": None}, {"result_hash": "not a hash"},
                       {"result_bytes": 0}, {"result_bytes": 1048577}, {"kind": "import"}):
            with self.subTest(change=change), patch.object(transfers, "live_identity", side_effect=lambda _db, user: user), \
                 patch.object(transfers, "require_task", return_value=SimpleNamespace(**{**original, **change})), \
                 self.assertRaises(HTTPException):
                transfers.export_download(None, object(), uuid4())


if __name__ == "__main__":
    unittest.main()
