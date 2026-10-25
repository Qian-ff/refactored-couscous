import unittest
from unittest.mock import Mock
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.dialects import postgresql

from app.domains.content.lessons.models import LessonDraft
from app.domains.content.questions.models import QuestionDraft
from app.domains.content.questions.policy import locked_draft


class DraftLockTests(unittest.TestCase):
    def test_actual_draft_primary_keys_are_locked_and_existing_rows_refreshed(self):
        for kind, model, primary_key in (("question", QuestionDraft, "question_id"), ("lesson", LessonDraft, "lesson_id")):
            with self.subTest(kind=kind):
                parent_id = uuid4()
                row, db = object(), Mock()
                db.exec.return_value.first.return_value = row
                self.assertIs(locked_draft(db, kind, parent_id), row)
                statement = db.exec.call_args.args[0]
                compiled = statement.compile(dialect=postgresql.dialect())
                self.assertIn(f"WHERE {model.__tablename__}.{primary_key} =", str(compiled))
                self.assertTrue(str(compiled).endswith("FOR UPDATE"))
                self.assertEqual(list(compiled.params.values()), [parent_id])
                self.assertIs(statement.get_execution_options()["populate_existing"], True)

    def test_missing_draft_keeps_the_existing_denial_behavior(self):
        for kind in ("question", "lesson"):
            with self.subTest(kind=kind):
                db = Mock()
                db.exec.return_value.first.return_value = None
                with self.assertRaises(HTTPException) as missing:
                    locked_draft(db, kind, uuid4())
                self.assertEqual(missing.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
