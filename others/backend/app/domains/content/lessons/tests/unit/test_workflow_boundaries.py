import copy
import unittest
from uuid import uuid4
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import aliased

from app.domains.content.lessons.schemas import Choice, Scoring
from app.domains.content.lessons.services import snapshot_hash, validate_question_binding
from app.domains.content.models import Library
from app.domains.content.questions.policy import covers_library, version_query
from app.domains.content.questions import queries
from app.domains.content.questions.schemas import Provenance, QuestionPayload
from app.domains.content.questions.sources import SourceSnapshot, check_publication
from app.domains.content.questions.tests.unit.test_policy import actor
from app.domains.content.questions.tests.unit.test_schema import sample_question


class WorkflowBoundaryTests(unittest.TestCase):
    def test_lesson_lists_use_lesson_tables_before_count_and_paging(self):
        class EmptyResult:
            def one(self):
                return 0

            def all(self):
                return []

        class CaptureSession:
            def __init__(self):
                self.sql = []

            def exec(self, statement):
                self.sql.append(str(statement.compile(dialect=postgresql.dialect())))
                return EmptyResult()

        for query, kwargs, table in (
            (queries.banks, {}, "content_lesson"),
            (queries.reviews, {}, "content_lesson_review"),
            (queries.publications, {"library_id": uuid4()}, "content_lesson_publication"),
        ):
            with self.subTest(query=query.__name__), patch.object(queries, "require_library"):
                db = CaptureSession()
                page = query(db, actor("teacher"), kind="lesson", **kwargs)
                self.assertEqual(page.total, 0)
                self.assertEqual(len(db.sql), 2)
                for sql in db.sql:
                    self.assertIn(table, sql)
                    self.assertNotIn("content_question", sql)
                    self.assertIn("WHERE", sql)

    def test_question_reference_must_match_full_fixed_content_and_scoring(self):
        raw = sample_question()
        payload = QuestionPayload.model_validate(raw)
        activity = Choice(id="activity", kind="choice", selection="single", prompt=payload.stem,
                          options=payload.options, question_version_id=uuid4())
        score = Scoring(activity_id="activity", correct_ids=payload.answer_ids, explanation=payload.explanation)
        validate_question_binding(activity, score, payload)
        for changed in (activity.model_copy(update={"prompt": "不同题干"}),
                        activity.model_copy(update={"selection": "multiple"})):
            with self.assertRaises(HTTPException):
                validate_question_binding(changed, score, payload)
        with self.assertRaises(HTTPException):
            validate_question_binding(activity, score.model_copy(update={"correct_ids": ("b",)}), payload)

    def test_frozen_lesson_hash_includes_asset_and_retained_question_origin(self):
        asset = type("Asset", (), {"content_hash": "a" * 64})()
        content = {"title": "original"}
        baseline = snapshot_hash(content, None, asset, {}, [])
        self.assertNotEqual(baseline, snapshot_hash(content, None, asset, {}, [("activity", uuid4())]))
        altered = copy.copy(asset)
        altered.content_hash = "b" * 64
        self.assertNotEqual(baseline, snapshot_hash(content, None, altered, {}, []))

    def test_college_publication_does_not_implicitly_cover_a_cross_college_catalog(self):
        requested = Library(scope="catalog", school_id=uuid4(), college_id=uuid4(), catalog_id=uuid4(),
                            creator_id=uuid4(), title="catalog")
        sql = str(covers_library(aliased(Library), requested).compile(dialect=postgresql.dialect(),
                                                                    compile_kwargs={"literal_binds": True}))
        self.assertIn("scope = 'college' AND false", sql)
        self.assertIn("scope = 'catalog' AND true", sql)

    def test_target_filter_cannot_be_mistaken_for_private_draft_read_authority(self):
        target = Library(scope="school", school_id=uuid4(), creator_id=uuid4(), title="target")
        with self.assertRaises(ValueError):
            version_query(actor("teacher"), "question", target_library=target)

    def test_public_source_locator_proof_never_publishes_a_changed_private_body(self):
        a = Library(scope="school", school_id=uuid4(), creator_id=uuid4(), title="A")
        b = Library(scope="school", school_id=uuid4(), creator_id=uuid4(), title="B")
        material = SourceSnapshot(uuid4(), None, {}, a.school_id, {"public_reuse_allowed": True,
            "license": "Synthetic public source", "license_url": "https://example.test/license"})
        proof = frozenset({(material.material_version_id, material.chunk_id)})
        with self.assertRaises(HTTPException):
            check_publication({"teaching_reuse_allowed": True, "license": "teaching"}, a, b, "synthetic",
                              [material], public_source_ids=proof)
        check_publication({"teaching_reuse_allowed": True, "license": "teaching"}, b, b, "synthetic",
                          [material], public_source_ids=proof)

    def test_retained_public_sources_still_require_immutable_source_license(self):
        a = Library(scope="school", school_id=uuid4(), creator_id=uuid4(), title="A")
        b = Library(scope="school", school_id=uuid4(), creator_id=uuid4(), title="B")
        private = SourceSnapshot(uuid4(), None, {}, a.school_id, {"public_reuse_allowed": False})
        with self.assertRaises(HTTPException):
            check_publication({}, b, b, "synthetic", [private],
                              public_source_ids=frozenset({(private.material_version_id, None)}))

    def test_origin_proofs_are_not_client_provenance_fields(self):
        for name in ("public_origin", "public_source_ids", "approved", "publication_id"):
            with self.subTest(name=name), self.assertRaises(ValidationError):
                Provenance.model_validate({name: True})


if __name__ == "__main__":
    unittest.main()
