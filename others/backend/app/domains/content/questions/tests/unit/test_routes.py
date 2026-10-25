import re
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.db import get_db
from app.domains.content.lessons.routes import router as lesson_router
from app.domains.content.questions.routes import router as question_router
from app.domains.content.questions.tests.unit.test_policy import actor
from app.domains.content.questions.tests.unit.test_schema import sample_question
from app.domains.core.auth import get_business_identity


def candidate_app(role="teacher"):
    app = FastAPI()
    app.include_router(question_router, prefix="/api/v1")
    app.include_router(lesson_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: None
    app.dependency_overrides[get_business_identity] = lambda: actor(role)
    return app


class CandidateRouteTests(unittest.TestCase):
    def test_candidate_schema_has_no_public_scoring_or_naked_asset_endpoint(self):
        schema = candidate_app().openapi()
        self.assertGreaterEqual(len(schema["paths"]), 30)
        operation_ids = []
        for path, methods in schema["paths"].items():
            self.assertNotIn("/students", path)
            self.assertNotIn("/assets/", path)
            self.assertNotIn("/answers", path)
            for method, operation in methods.items():
                operation_ids.append(operation["operationId"])
                self.assertNotIn("purpose", [value["name"] for value in operation.get("parameters", [])])
                if method in {"post", "patch", "delete", "put"}:
                    key = next(value for value in operation["parameters"] if value["name"] == "Idempotency-Key")
                    self.assertTrue(key["required"])
                    self.assertEqual(key["schema"]["minLength"], 8)
        self.assertEqual(len(operation_ids), len(set(operation_ids)))
        for model in ("TransferView", "TransferResult"):
            properties = schema["components"]["schemas"][model]["properties"]
            for private in ("file_key", "execution_id", "lease_owner", "payload", "answer_ids"):
                self.assertNotIn(private, properties)

    def test_student_cannot_call_any_candidate_management_route(self):
        app = candidate_app("student")
        paths = app.openapi()["paths"]
        with TestClient(app) as client:
            for path, methods in paths.items():
                concrete = re.sub(r"\{[^}]+\}", str(uuid4()), path)
                for method in methods:
                    with self.subTest(path=path, method=method):
                        response = client.request(method, concrete, params={"library_id": str(uuid4())},
                            headers={"Idempotency-Key": "c1-student-denied"}, **({"json": {}} if method != "get" else {}))
                        self.assertEqual(response.status_code, 403)

    def test_unconfigured_environment_returns_503_before_business_execution(self):
        with TestClient(candidate_app()) as client:
            response = client.post("/api/v1/content/questions/drafts", json={"library_id": str(uuid4()), "payload": sample_question()},
                headers={"Idempotency-Key": "c1-test-unconfigured"})
        self.assertEqual(response.status_code, 503)
        self.assertIn("CONTENT_C1_UNAVAILABLE", response.json()["detail"])

    def test_teacher_svg_response_is_private_passive_and_not_cacheable(self):
        with patch("app.domains.content.lessons.queries.preview_asset", return_value=(b'<svg xmlns="http://www.w3.org/2000/svg"/>', "a" * 64)), \
             TestClient(candidate_app()) as client:
            response = client.get(f"/api/v1/content/lessons/versions/{uuid4()}/preview/scene")
        self.assertEqual(response.status_code, 200)
        self.assertIn("image/svg+xml", response.headers["content-type"])
        self.assertEqual(response.headers["cache-control"], "private, no-store")
        self.assertIn("sandbox", response.headers["content-security-policy"])
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")


if __name__ == "__main__":
    unittest.main()
