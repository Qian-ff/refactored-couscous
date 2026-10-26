import copy
import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.domains.content.lessons.projection import student_projection
from app.domains.content.lessons.schemas import LessonContent, Region, StudentLesson, StudentReference, TeacherLessonPreview


def sample_lesson():
    return {"title": "入室准备", "short_lesson": "检查本次实验要求，并在教师确认后开始。", "required": True,
            "scene": {"id": "room", "svg_asset_id": str(uuid4()), "accessible_description": "实验室入口与储物区域"},
            "activities": [{"id": "choice", "kind": "choice", "prompt": "哪项符合要求？", "selection": "single",
                            "options": [{"id": "a", "label": "确认要求"}, {"id": "b", "label": "直接开始"}]},
                           {"id": "order", "kind": "order", "prompt": "排列步骤", "items": [
                               {"id": "first", "label": "确认要求"}, {"id": "second", "label": "按要求准备"}]}],
            "scoring": [{"activity_id": "choice", "correct_ids": ["a"], "explanation": "先确认要求。"},
                        {"activity_id": "order", "correct_ids": ["first", "second"], "explanation": "确认后再准备。"}]}


class LessonContentTests(unittest.TestCase):
    def test_projection_omits_private_fields_and_requires_authorized_sources(self):
        raw = sample_lesson()
        raw["activities"][0]["question_version_id"] = str(uuid4())
        raw["activities"][0]["sources"] = [{"material_version_id": str(uuid4()), "chunk_id": str(uuid4())}]
        content = LessonContent.model_validate(raw)
        lesson_id, version_id = uuid4(), uuid4()
        public = student_projection(content, lesson_id, version_id)
        output = public.model_dump_json()
        for private in ("correct_ids", "scoring", "explanation", "provenance", "question_version_id", "chunk_id"):
            self.assertNotIn('"' + private + '"', output)
        self.assertEqual(public.activities[0].source_refs, ())
        ref = StudentReference(material_id=uuid4(), version_id=uuid4(), page=1)
        with_source = student_projection(content, lesson_id, version_id, {"choice": (ref,)})
        self.assertEqual(with_source.activities[0].source_refs, (ref,))
        self.assertEqual(public.model_dump(), student_projection(content, lesson_id, version_id).model_dump())

    def test_presented_order_is_stable_and_independent_of_the_private_solution(self):
        first = sample_lesson()
        second = copy.deepcopy(first)
        second["scoring"][1]["correct_ids"] = ["second", "first"]
        lesson_id, version_id = uuid4(), uuid4()
        a = student_projection(LessonContent.model_validate(first), lesson_id, version_id)
        b = student_projection(LessonContent.model_validate(second), lesson_id, version_id)
        self.assertEqual(a.model_dump(), b.model_dump())

    def test_teacher_preview_is_separate_and_student_rejects_answer_fields(self):
        content = LessonContent.model_validate(sample_lesson())
        public = student_projection(content, uuid4(), uuid4())
        preview = TeacherLessonPreview(lesson=public, review=content.scoring)
        self.assertEqual(preview.review[0].correct_ids, ("a",))
        with self.assertRaises(ValidationError):
            StudentLesson.model_validate({**public.model_dump(), "review": preview.review})

    def test_activity_ids_and_scoring_must_match_exactly(self):
        for change in ("duplicate_activity", "missing_score", "unknown_answer", "partial_order"):
            raw = sample_lesson()
            if change == "duplicate_activity":
                raw["activities"].append(copy.deepcopy(raw["activities"][0]))
            elif change == "missing_score":
                raw["scoring"].pop()
            elif change == "unknown_answer":
                raw["scoring"][0]["correct_ids"] = ["not-an-option"]
            else:
                raw["scoring"][1]["correct_ids"] = ["first"]
            with self.subTest(change=change), self.assertRaises(ValidationError):
                LessonContent.model_validate(raw)

    def test_rectangles_reject_overflow_nan_and_boolean(self):
        rectangle = dict(id="region", label="区域", x=0.2, y=0.2, width=0.3, height=0.3)
        for update in ({"x": 0.9}, {"width": 0}, {"x": float("nan")}, {"y": True}):
            with self.subTest(update=update), self.assertRaises(ValidationError):
                Region(**{**rectangle, **update})

    def test_unknown_payload_scoring_flags_are_rejected(self):
        raw = sample_lesson()
        raw["activities"][0]["options"][0]["correct"] = True
        with self.assertRaises(ValidationError):
            LessonContent.model_validate(raw)


if __name__ == "__main__":
    unittest.main()
