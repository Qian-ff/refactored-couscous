"""Development-only deterministic artifacts, confined to C1 seed-data directories."""
import json
from pathlib import Path

from app.domains.content.lessons import seeds as lessons
from app.domains.content.questions.schemas import fingerprint
from app.domains.content.questions.seeds import TOPICS, provenance, question_seeds, seed_manifest
from app.domains.content.questions.transfer_codec import export_template


def main():
    question_root = Path(__file__).parent / "seed-data"
    lesson_root = Path(lessons.__file__).parent / "seed-data"
    question_root.mkdir(exist_ok=True)
    lesson_root.mkdir(exist_ok=True)
    question_root.joinpath("questions.json").write_text(json.dumps(seed_manifest(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    seeds = question_seeds()
    for group in ("general", "chemistry"):
        question_root.joinpath(group + ".csv").write_bytes(export_template([seed.content for seed in seeds if seed.group == group], "csv"))
    drafts = []
    for topic, (group, title, refs) in TOPICS.items():
        scene = lessons.scene_svg(topic)
        lesson_root.joinpath(topic + ".svg").write_text(scene.svg, encoding="utf-8")
        drafts.append({"key": topic, "group": group, "title": title, "status": "draft", "scene_file": topic + ".svg",
            "scene_hash": scene.sha256, "requires_actual_scene_binding": True,
            "provenance": provenance(topic).model_dump(mode="json"), "reference_keys": list(refs),
            "draft_definition": lessons.SPECS[topic]})
    manifest = {"schema_version": "labconnect.c1-lesson-seeds/1", "status": "draft",
        "content_hash": fingerprint(drafts), "lessons": drafts}
    lesson_root.joinpath("lessons.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"questions": len(seeds), "lessons": len(drafts), "status": "draft"}))


if __name__ == "__main__":
    main()
