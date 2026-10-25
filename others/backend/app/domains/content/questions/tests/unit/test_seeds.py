import unittest
from collections import Counter
from uuid import uuid4

from app.domains.content.lessons.projection import student_projection
from app.domains.content.lessons.seeds import SPECS, lesson_seed, scene_svg
from app.domains.content.questions.seeds import TOPICS, question_seeds, seed_manifest
from app.domains.content.questions.transfer_codec import export_template, parse_template


class DraftSeedTests(unittest.TestCase):
    def test_sixty_unique_original_drafts_split_into_two_groups_and_six_topics(self):
        seeds = question_seeds()
        self.assertEqual(len(seeds), 60)
        self.assertEqual(Counter(seed.group for seed in seeds), {"general": 30, "chemistry": 30})
        self.assertEqual(Counter(seed.topic for seed in seeds), {topic: 10 for topic in TOPICS})
        self.assertEqual(Counter(seed.content.payload.kind for seed in seeds), {"single": 36, "true_false": 12, "multiple": 6, "scenario": 6})
        self.assertEqual(len({seed.content.payload.duplicate_hash() for seed in seeds}), 60)
        self.assertEqual(len({seed.key for seed in seeds}), 60)
        for seed in seeds:
            self.assertEqual(seed.status, "draft")
            self.assertFalse(seed.content.provenance.public_reuse_allowed)
            self.assertFalse(seed.content.provenance.teaching_reuse_allowed)
            self.assertEqual(seed.content.sources, ())
            if seed.content.payload.kind != "true_false":
                for option in seed.content.payload.options:
                    self.assertRegex(option.id, r"^v[0-9a-f]{12}$")

    def test_all_draft_questions_roundtrip_through_the_real_csv_codec(self):
        contents = [seed.content for seed in question_seeds()]
        preview = parse_template(export_template(contents, "csv"), "csv")
        self.assertEqual([row.content for row in preview.rows], contents)
        self.assertTrue(all(row.error is None and row.duplicate_of is None for row in preview.rows))

    def test_six_scenes_and_lessons_are_distinct_bounded_and_student_safe(self):
        hashes = set()
        for topic in SPECS:
            with self.subTest(topic=topic):
                scene = scene_svg(topic)
                hashes.add(scene.sha256)
                self.assertEqual(scene.view_box, (0, 0, 960, 600))
                content = lesson_seed(topic, uuid4())
                self.assertEqual({activity.kind for activity in content.activities}, {"choice", "hotspot", "order"})
                self.assertTrue(all(not getattr(activity, "question_version_id", None) for activity in content.activities))
                projected = student_projection(content, uuid4(), uuid4()).model_dump(mode="json")
                self.assertNotIn("scoring", projected)
                self.assertNotIn("provenance", projected)
                for activity in projected["activities"]:
                    for option in activity.get("items", activity.get("options", activity.get("regions", []))):
                        self.assertRegex(option["id"], r"^v[0-9a-f]{12}$")
                self.assertFalse(content.provenance.public_reuse_allowed)
        self.assertEqual(len(hashes), 6)

    def test_manifest_is_deterministic_and_does_not_invent_external_version_hashes(self):
        first = seed_manifest()
        self.assertEqual(first, seed_manifest())
        self.assertEqual(first["status"], "draft")
        for reference in first["references"]:
            self.assertIsNone(reference["publisher_content_hash"])
            self.assertIsNone(reference["publisher_version"])
            self.assertTrue(reference["url"].startswith("https://"))


if __name__ == "__main__":
    unittest.main()
