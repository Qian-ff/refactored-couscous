import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.domains.content.questions.schemas import Provenance, QuestionCreate, QuestionPayload, Revision, fingerprint


def sample_question():
    return dict(kind="single", stem="入室前应先做什么？", options=[{"id": "a", "label": "核对本次要求"},
                {"id": "b", "label": "忽略要求"}], answer_ids=["a"], explanation="根据本次实验要求准备。",
                knowledge_points=["入室准备"], difficulty="easy")


class QuestionValidationTests(unittest.TestCase):
    def test_chinese_hash_is_stable_and_normalized_duplicates_ignore_answer_changes(self):
        first = sample_question()
        second = {**first, "answer_ids": ["b"], "options": list(reversed(first["options"]))}
        a, b = QuestionPayload.model_validate(first), QuestionPayload.model_validate(second)
        self.assertEqual(a.duplicate_hash(), b.duplicate_hash())
        self.assertNotEqual(fingerprint(a), fingerprint(b))
        self.assertEqual(fingerprint(a), fingerprint(a.model_dump(mode="json")))

    def test_answers_must_exist_and_be_unique(self):
        for answer in (["missing"], ["a", "a"], []):
            with self.subTest(answer=answer), self.assertRaises(ValidationError):
                QuestionPayload.model_validate({**sample_question(), "answer_ids": answer})

    def test_type_specific_answer_cardinality(self):
        with self.assertRaises(ValidationError):
            QuestionPayload.model_validate({**sample_question(), "kind": "multiple"})
        with self.assertRaises(ValidationError):
            QuestionPayload.model_validate({**sample_question(), "kind": "true_false"})
        value = {**sample_question(), "kind": "true_false", "answer_ids": ["true"],
                 "options": [{"id": "true", "label": "正确"}, {"id": "false", "label": "错误"}]}
        self.assertEqual(QuestionPayload.model_validate(value).answer_ids, ("true",))

    def test_duplicate_ids_and_unicode_equivalent_labels_are_invalid(self):
        for options in ([{"id": "a", "label": "甲"}, {"id": "a", "label": "乙"}],
                        [{"id": "a", "label": "Ａ"}, {"id": "b", "label": "a"}]):
            with self.subTest(options=options), self.assertRaises(ValidationError):
                QuestionPayload.model_validate({**sample_question(), "options": options})

    def test_no_mass_assignment_or_implicit_approval(self):
        for key in ("creator_id", "school_id", "published", "approved", "answer_visible"):
            with self.subTest(key=key), self.assertRaises(ValidationError):
                QuestionCreate.model_validate({"library_id": str(uuid4()), "payload": sample_question(), key: True})

    def test_control_characters_blank_and_invalid_unicode_are_rejected(self):
        for value in ("  ", "text\x00", "\ud800"):
            with self.subTest(value=repr(value)), self.assertRaises(ValidationError):
                QuestionPayload.model_validate({**sample_question(), "stem": value})

    def test_knowledge_and_byte_limits(self):
        for change in ({"knowledge_points": ["同名", "同名"]}, {"knowledge_points": ["点" * 101]},
                       {"explanation": "安" * 8000, "stem": "全" * 4000}):
            with self.subTest(change=list(change)), self.assertRaises(ValidationError):
                QuestionPayload.model_validate({**sample_question(), **change})

    def test_provenance_date_and_link_validation(self):
        for change in ({"acquired_date": "2026-02-30"}, {"original_url": "https://user:secret@example.test/file"},
                       {"license_url": "file:///private"}, {"source_hash": "bad"}):
            with self.subTest(change=list(change)), self.assertRaises(ValidationError):
                Provenance.model_validate(change)
        self.assertFalse(Provenance(acquired_date="2026-10-25").public_reuse_allowed)

    def test_revision_is_positive_integer_not_boolean_or_coerced_string(self):
        for revision in (0, True, "1"):
            with self.subTest(revision=revision), self.assertRaises(ValidationError):
                Revision(revision=revision)


if __name__ == "__main__":
    unittest.main()
