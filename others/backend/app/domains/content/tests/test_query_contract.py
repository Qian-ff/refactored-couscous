import unittest
from uuid import uuid4

from fastapi import FastAPI
from sqlalchemy.dialects import postgresql

from app.domains.core.auth import Identity
from app.domains.core.models import LoginSession, RoleGrant, User, now
from app.domains.content.access import readable_versions, submit_libraries
from app.domains.content.downloads import safe_name
from app.domains.content.queries import keyword, library_query
from app.domains.content.routes import router
from app.domains.content.views import CommandResult, VersionView


class QueryContractTests(unittest.TestCase):
    def identity(self):
        user = User(id=uuid4(), school_id=uuid4(), college_id=uuid4(), username="synthetic",
                    display_name="Synthetic", hashed_password="unused")
        grant = RoleGrant(user_id=user.id, school_id=user.school_id, role="teacher")
        return Identity(user, [grant], LoginSession(user_id=user.id, expires_at=now()), "teacher")

    def test_queries_compile_with_context_library_and_scoped_targets(self):
        identity = self.identity()
        for query in (readable_versions(identity, uuid4()), submit_libraries(identity), library_query(identity)[0]):
            sql = str(query.compile(dialect=postgresql.dialect()))
            self.assertIn("EXISTS", sql)
            self.assertIn("school", sql)

    def test_literal_search_and_safe_download_filename(self):
        self.assertEqual(keyword("a%b_c"), "%a\\%b\\_c%")
        self.assertNotIn("/", safe_name("../private/安全.txt"))
        self.assertNotIn("\n", safe_name("安全\r\n.txt"))

    def test_public_models_exclude_storage_and_actor_credentials(self):
        forbidden = {"file_key", "upload_id", "owner_id", "login_session_id", "lease_owner", "input_text", "grants"}
        self.assertFalse(forbidden.intersection(VersionView.model_fields))
        self.assertNotIn("file_key", CommandResult.model_fields)

    def test_candidate_openapi_is_typed_and_binary_but_not_published(self):
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        spec = app.openapi()
        paths = spec["paths"]
        get = paths["/api/v1/content/versions/{version_id}/download"]["get"]
        self.assertEqual(set(get["responses"]["200"]["content"]), {"application/octet-stream"})
        put = paths["/api/v1/content/uploads/{upload_id}/bytes"]["put"]
        self.assertEqual(put["requestBody"]["content"]["application/octet-stream"]["schema"]["format"], "binary")
        post = paths["/api/v1/content/libraries"]["post"]
        self.assertTrue(any(p["name"] == "Idempotency-Key" and p["required"] for p in post["parameters"]))
        self.assertIn("$ref", paths["/api/v1/content/materials"]["get"]["responses"]["200"]["content"]["application/json"]["schema"])


if __name__ == "__main__":
    unittest.main()
