import unittest
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.dialects import postgresql

from app.domains.core.auth import Identity
from app.domains.core.models import LoginSession, RoleGrant, User, now
from app.domains.content.models import Library
from app.domains.content.questions.budget import ContentBudget
from app.domains.content.questions.policy import draft_query, staff, version_query
from app.domains.content.questions.queries import bounds, keyword
from app.domains.content.questions.sources import SourceSnapshot, check_publication


def actor(role):
    user = User(id=uuid4(), school_id=uuid4(), username="synthetic", display_name="Synthetic", hashed_password="unused")
    grant = RoleGrant(user_id=user.id, school_id=user.school_id, role=role)
    return Identity(user, [grant], LoginSession(user_id=user.id, expires_at=now() + timedelta(hours=1)), role)


class ContentPolicyTests(unittest.TestCase):
    def test_student_is_filtered_before_any_question_or_lesson_count(self):
        identity = actor("student")
        with self.assertRaises(HTTPException) as denied:
            staff(identity)
        self.assertEqual(denied.exception.status_code, 403)
        for kind in ("question", "lesson"):
            self.assertIn("WHERE false", str(version_query(identity, kind).compile(dialect=postgresql.dialect())))
            self.assertIn("false", str(draft_query(identity, kind).compile(dialect=postgresql.dialect())))

    def test_fixed_versions_use_exists_before_paging_not_duplicate_publication_joins(self):
        identity = actor("teacher")
        for kind in ("question", "lesson"):
            sql = str(version_query(identity, kind, uuid4()).compile(dialect=postgresql.dialect()))
            self.assertIn("EXISTS", sql)
            self.assertIn(".state =", sql)
            self.assertNotIn(f"JOIN content_{kind}_publication", sql.split("WHERE", 1)[0])

    def test_authoring_resolution_requires_published_course_bindings_and_all_audience_for_lessons(self):
        course = SimpleNamespace(id=uuid4(), school_id=uuid4(), college_id=uuid4(), catalog_id=uuid4())
        identity = actor("teacher")
        sql = str(version_query(identity, "lesson", published_only=True, course=course).compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
        self.assertIn("audience = 'all'", sql)
        self.assertIn(str(course.id), sql)
        self.assertIn(str(course.catalog_id), sql)
        self.assertIn("state = 'approved'", sql)
        self.assertNotIn("'submitted'", sql)

    def test_missing_public_accounting_fails_before_touching_a_session(self):
        with self.assertRaises(HTTPException) as unavailable:
            ContentBudget().admit(None, None)
        self.assertEqual(unavailable.exception.status_code, 503)

    def test_search_literals_and_bounds(self):
        self.assertEqual(keyword("安_%\\"), "%安\\_\\%\\\\%")
        for q, point, offset, limit in (("a" * 101, "", 0, 1), ("", "a" * 101, 0, 1), ("", "", -1, 1), ("", "", 0, 101)):
            with self.subTest(limit=limit), self.assertRaises(HTTPException):
                bounds(q, point, offset, limit)

    def test_school_private_data_cannot_be_relabelled_for_another_school(self):
        source = Library(scope="school", school_id=uuid4(), creator_id=uuid4(), title="source")
        target = Library(scope="school", school_id=uuid4(), creator_id=uuid4(), title="target")
        with self.assertRaises(HTTPException) as denied:
            check_publication({"public_reuse_allowed": True, "license": "test"}, source, target, "synthetic")
        self.assertEqual(denied.exception.status_code, 403)

    def test_reuse_requires_an_explicit_grant_and_public_requires_each_source_license(self):
        source = Library(scope="school", school_id=uuid4(), creator_id=uuid4(), title="source")
        public = Library(scope="platform_public", creator_id=uuid4(), title="public")
        for provenance in ({"license": "not a grant"}, {"teaching_reuse_allowed": True}):
            with self.subTest(provenance=provenance), self.assertRaises(HTTPException):
                check_publication(provenance, source, source, "synthetic", reusing=True)
        allowed = {"license": "synthetic public license", "license_url": "https://example.test/license", "public_reuse_allowed": True}
        private_ref = SourceSnapshot(uuid4(), None, {}, source.school_id, {"public_reuse_allowed": False})
        with self.assertRaises(HTTPException):
            check_publication(allowed, source, public, "synthetic", [private_ref])
        check_publication(allowed, source, public, "synthetic")


if __name__ == "__main__":
    unittest.main()
