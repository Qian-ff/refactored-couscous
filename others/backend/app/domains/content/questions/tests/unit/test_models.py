"""DDL compilation only; real PG guards/permissions require A's future migration."""
import unittest

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from app.domains.core import models as core_models  # noqa: F401
from app.domains.content.lessons import models as lesson_models
from app.domains.content.questions import models as question_models


class ModelContractTests(unittest.TestCase):
    def test_all_candidate_foreign_keys_resolve_and_compile_on_postgres(self):
        tables = []
        for module in (question_models, lesson_models):
            tables.extend(value.__table__ for value in vars(module).values()
                          if isinstance(value, type) and value.__module__ == module.__name__ and hasattr(value, "__table__"))
        self.assertTrue(tables)
        for table in tables:
            with self.subTest(table=table.name):
                for key in table.foreign_keys:
                    self.assertIsNotNone(key.column)
                self.assertIn("CREATE TABLE", str(CreateTable(table).compile(dialect=postgresql.dialect())))

    def test_publications_bind_review_version_and_target_together(self):
        for model in (question_models.QuestionPublication, lesson_models.LessonPublication):
            composite = [constraint for constraint in model.__table__.foreign_key_constraints
                         if len(constraint.column_keys) == 3]
            self.assertEqual(len(composite), 1)
            self.assertEqual(set(composite[0].column_keys), {"review_id", "version_id", "target_library_id"})

    def test_transfer_has_no_fake_material_version_and_uses_real_session_owner(self):
        table = question_models.TransferTask.__table__
        self.assertNotIn("material_version_id", table.c)
        self.assertIn("fk_question_transfer_session_owner", {constraint.name for constraint in table.foreign_key_constraints})
        self.assertIn("content_scene_asset.id", {key.target_fullname for key in lesson_models.LessonVersion.__table__.foreign_keys})


if __name__ == "__main__":
    unittest.main()
