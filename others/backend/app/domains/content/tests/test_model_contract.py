"""Metadata/SQL checks only; these are not PostgreSQL authorization integration evidence."""
import unittest
from uuid import uuid4

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from app.domains.core.auth import Identity
from app.domains.core.models import LoginSession, RoleGrant, User, now
from app.domains.content.access import readable_versions
from app.domains.content.models import (
    ContentJob, ContentUpload, Library, Material, MaterialPublication, MaterialReview, MaterialVersion, SourceChunk,
)


class ModelContractTests(unittest.TestCase):
    def test_postgresql_ddl_resolves_foreign_keys(self):
        for model in (Library, Material, ContentUpload, MaterialVersion, SourceChunk,
                      MaterialReview, MaterialPublication, ContentJob):
            with self.subTest(model=model.__name__):
                table = model.__table__
                for foreign_key in table.foreign_keys:
                    self.assertIsNotNone(foreign_key.column)
                self.assertIn("CREATE TABLE", str(CreateTable(table).compile(dialect=postgresql.dialect())))

    def test_explicit_upload_fk_and_immutable_input_shape(self):
        self.assertEqual(next(iter(MaterialVersion.__table__.c.upload_id.foreign_keys)).target_fullname,
                         "content_upload.id")
        ddl = str(CreateTable(MaterialVersion.__table__).compile(dialect=postgresql.dialect()))
        self.assertIn("ck_content_version_input", ddl)
        self.assertNotIn("published", Material.__table__.c)

    def test_publication_review_binds_exact_target_and_version(self):
        constraint = next(c for c in MaterialPublication.__table__.foreign_key_constraints
                          if c.name == "fk_content_publication_review")
        self.assertEqual(set(constraint.column_keys), {"review_id", "version_id", "target_library_id"})

    def test_identity_narrowed_query_uses_exists_not_duplicate_join(self):
        school, user_id = uuid4(), uuid4()
        user = User(id=user_id, school_id=school, username="synthetic", display_name="Synthetic", hashed_password="unused")
        grants = [RoleGrant(user_id=user_id, school_id=school, role=role)
                  for role in ("teacher", "school_admin")]
        identity = Identity(user, grants, LoginSession(user_id=user_id, expires_at=now()), "teacher")
        sql = str(readable_versions(identity).compile(dialect=postgresql.dialect()))
        self.assertIn("EXISTS", sql)
        self.assertIn("content_material_review.state", sql)
        self.assertIn("content_material_publication.active IS true", sql)
        self.assertNotIn("JOIN content_material_publication", sql.split("WHERE", 1)[0])
        self.assertFalse(identity.has("school_admin"))


if __name__ == "__main__":
    unittest.main()
