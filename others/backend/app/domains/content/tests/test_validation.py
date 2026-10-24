"""Pure boundary checks; PG command/locking checks require A's migration."""
import unittest
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql

from app.domains.content.models import Library, MaterialVersion
from app.domains.content.quota import DISK_FLOOR, GLOBAL_BYTES, SCHOOL_BYTES, accounting_queries, validate_budget
from app.domains.content.schemas import LibraryChange, LibraryCreate, ReviewSubmit, SourceMetadata, TextMaterialCreate
from app.domains.content.services import require_key, validate_publication_source, warnings_hash


class ValidationTests(unittest.TestCase):
    def test_client_cannot_inject_authority_or_storage(self):
        for extra in ({"creator_id": str(uuid4())}, {"published": True}, {"file_key": "../private"}):
            with self.subTest(extra=extra), self.assertRaises(ValidationError):
                TextMaterialCreate(library_id=uuid4(), title="Safety", text="safe", **extra)

    def test_utf8_byte_budget_and_blank_input(self):
        for value in (" ", "x\0y", "安" * 350000):
            with self.subTest(length=len(value)), self.assertRaises(ValidationError):
                TextMaterialCreate(library_id=uuid4(), title="Safety", text=value)
        raw = " line 1\r\nline 2 "
        self.assertEqual(TextMaterialCreate(library_id=uuid4(), title="Safety", text=raw).text, raw)

    def test_scope_immutable_in_patch(self):
        with self.assertRaises(ValidationError):
            LibraryChange(revision=1, scope="school")
        with self.assertRaises(ValidationError):
            LibraryCreate(scope="school", title="  ")
        with self.assertRaises(ValidationError):
            ReviewSubmit(version_id=uuid4(), target_library_id=uuid4(), authorization_statement=" ")

    def test_source_links_never_accept_credential_urls(self):
        for url in ("https://user:secret@example.test/file", "file:///etc/passwd", "http://example.test"):
            with self.subTest(url=url), self.assertRaises(ValidationError):
                SourceMetadata(license_url=url)

    def test_quota_boundaries_and_missing_capacity_probe(self):
        validate_budget(GLOBAL_BYTES, SCHOOL_BYTES, 123, DISK_FLOOR + 123)
        for total, scoped, reserved, free, status in (
                (GLOBAL_BYTES + 1, 0, 0, 10**12, 413),
                (0, SCHOOL_BYTES + 1, 0, 10**12, 413),
                (0, 0, 10, DISK_FLOOR + 9, 507),
                (0, 0, 0, None, 503)):
            with self.subTest(status=status), self.assertRaises(HTTPException) as context:
                validate_budget(total, scoped, reserved, free)
            self.assertEqual(context.exception.status_code, status)

    def test_accounting_is_state_independent_and_scoped(self):
        groups = accounting_queries(None)
        global_sql = [str(query.compile(dialect=postgresql.dialect())) for query in groups[0]]
        scoped_sql = [str(query.compile(dialect=postgresql.dialect())) for query in groups[1]]
        self.assertTrue(all("state" not in sql for sql in global_sql))
        self.assertTrue(all("IS NULL" in sql for sql in scoped_sql))
        self.assertIn("reserved_bytes", global_sql[0])
        self.assertIn("retained_bytes", global_sql[1])

    def test_unparsed_or_cross_school_source_cannot_be_published(self):
        actor = uuid4()
        source = Library(scope="school", school_id=uuid4(), title="Source", creator_id=actor)
        target = Library(scope="school", school_id=uuid4(), title="Target", creator_id=actor)
        version = MaterialVersion(material_id=uuid4(), version_no=1, input_kind="text", input_text="x",
                                  content_hash="a" * 64, created_by=actor)
        with self.assertRaises(HTTPException):
            validate_publication_source(version, source, source, "authorized")
        version.extraction_state = "succeeded"
        with self.assertRaises(HTTPException) as context:
            validate_publication_source(version, source, target, "authorized")
        self.assertEqual(context.exception.status_code, 403)

    def test_public_license_and_warning_snapshot(self):
        actor = uuid4()
        source = Library(scope="school", school_id=uuid4(), title="Source", creator_id=actor)
        target = Library(scope="platform_public", title="Public", creator_id=actor)
        version = MaterialVersion(material_id=uuid4(), version_no=1, input_kind="text", input_text="x",
                                  content_hash="a" * 64, created_by=actor, extraction_state="succeeded")
        before = warnings_hash(version)
        version.warnings = ["NOTES"]
        self.assertNotEqual(before, warnings_hash(version))
        with self.assertRaises(HTTPException):
            validate_publication_source(version, source, target, "authorized")
        version.source_metadata = {"public_reuse_allowed": True, "license": "synthetic-license",
                                   "license_url": "https://example.test/license"}
        validate_publication_source(version, source, target, "authorized")

    def test_writes_require_bounded_idempotency_key(self):
        for key in (None, "short", "a" * 129):
            with self.subTest(key=key), self.assertRaises(HTTPException):
                require_key(key)


if __name__ == "__main__":
    unittest.main()
