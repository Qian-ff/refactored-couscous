import copy
import io
import unittest
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError

from app.domains.content.models import now
from app.domains.content.questions.imports import ImportConfirm, _confirmed_contents, preview_hash
from app.domains.content.questions.tests.unit.test_transfer_codec import content
from app.domains.content.questions.transfer_codec import Preview, export_template, parse_template
from app.domains.content.questions.transfer_cli import process
from app.domains.content.questions.schemas import canonical_bytes


def fixture():
    preview = parse_template(export_template([content()], "csv"), "csv")
    batch = SimpleNamespace(id=uuid4(), library_id=uuid4(), input_hash=preview.input_hash, revision=2,
        state="ready", row_count=1, normalized_rows=[row.model_dump(mode="json") for row in preview.rows], errors=[])
    task = SimpleNamespace(id=uuid4(), state="succeeded", generation=1, result_hash=preview.digest(), expires_at=now() + timedelta(hours=1))
    batch.preview_hash = preview_hash(batch, task)
    request = ImportConfirm(revision=2, library_id=batch.library_id, input_hash=batch.input_hash, preview_hash=batch.preview_hash)
    return batch, task, request


class ImportConfirmationTests(unittest.TestCase):
    def test_fixed_worker_export_then_import_produces_the_same_draft(self):
        manifest = canonical_bytes({"protocol": "labconnect.question-transfer/1", "questions": [content().model_dump(mode="json")]})
        csv_file = process(io.BytesIO(manifest), "export", "csv")
        result = Preview.model_validate_json(process(io.BytesIO(csv_file), "import", "csv"))
        self.assertEqual(result.rows[0].content, content())

    def test_only_exact_reviewed_batch_produces_content(self):
        batch, task, request = fixture()
        self.assertEqual(_confirmed_contents(batch, task, request), [content()])
        for change in ({"revision": 1}, {"library_id": uuid4()}, {"input_hash": "a" * 64}, {"preview_hash": "b" * 64}):
            with self.subTest(change=change), self.assertRaises(HTTPException):
                _confirmed_contents(batch, task, request.model_copy(update=change))

    def test_late_result_changed_payload_generation_or_error_invalidates_confirmation(self):
        for mutation in ("payload", "generation", "worker_hash", "errors", "count", "state", "expired"):
            with self.subTest(mutation=mutation):
                batch, task, request = fixture()
                if mutation == "payload":
                    batch.normalized_rows[0]["content"]["payload"]["stem"] = "changed"
                elif mutation == "generation":
                    task.generation += 1
                elif mutation == "worker_hash":
                    task.result_hash = "c" * 64
                elif mutation == "errors":
                    batch.errors = [{"row": 3, "code": "existing_duplicate"}]
                elif mutation == "count":
                    batch.row_count = 2
                elif mutation == "state":
                    task.state = "canceled"
                else:
                    task.expires_at = now() - timedelta(seconds=1)
                with self.assertRaises(HTTPException):
                    _confirmed_contents(batch, task, request)

    def test_untrusted_previews_cannot_claim_unknown_errors_duplicates_or_material_grants(self):
        batch, _task, _request = fixture()
        original = {"input_hash": batch.input_hash, "rows": copy.deepcopy(batch.normalized_rows)}
        for mutation in ("protocol", "hash", "row", "duplicate", "both", "neither", "source", "error"):
            value = copy.deepcopy(original)
            row = value["rows"][0]
            if mutation == "protocol":
                value["protocol"] = "labconnect.parse/1"
            elif mutation == "hash":
                value["input_hash"] = "not a digest"
            elif mutation == "row":
                row["row"] = 99
            elif mutation == "duplicate":
                row["duplicate_of"] = 3
            elif mutation == "both":
                row["error"] = "invalid_question"
            elif mutation == "neither":
                row["content"] = None
            elif mutation == "source":
                row["content"]["sources"] = [{"material_version_id": str(uuid4())}]
            else:
                row["content"], row["error"] = None, "<private text>"
            with self.subTest(mutation=mutation), self.assertRaises(ValidationError):
                Preview.model_validate(value)


if __name__ == "__main__":
    unittest.main()
