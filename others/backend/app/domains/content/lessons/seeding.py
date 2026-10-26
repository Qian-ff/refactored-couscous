"""Explicit internal demo import into two existing authorized course libraries. Never auto-publish."""
from uuid import UUID

from fastapi import HTTPException
from pydantic import model_validator

from app.domains.content.access import require_library
from app.domains.content.lessons.models import SceneAsset
from app.domains.content.lessons.seeds import SPECS, lesson_seed, scene_svg
from app.domains.content.lessons.services import _context, _insert
from app.domains.content.questions.budget import ContentBudget
from app.domains.content.questions.policy import staff
from app.domains.content.questions.schemas import StrictModel, canonical_bytes, fingerprint
from app.domains.content.questions.seeds import TOPICS, provenance, question_seeds, seed_manifest
from app.domains.content.questions.services import _insert_draft
from app.domains.content.services import execute_command, require_key


class DemoDraftImport(StrictModel):
    general_library_id: UUID
    chemistry_library_id: UUID

    @model_validator(mode="after")
    def distinct(self):
        if self.general_library_id == self.chemistry_library_id:
            raise ValueError("两个示范班须使用不同课程库")
        return self


def _targets(db, identity, request):
    libraries = {"general": require_library(db, identity, request.general_library_id, "submit"),
                 "chemistry": require_library(db, identity, request.chemistry_library_id, "submit")}
    if any(row.scope != "course" for row in libraries.values()):
        raise HTTPException(422, "示范内容须导入已有教学班课程库")
    if libraries["general"].school_id != libraries["chemistry"].school_id:
        raise HTTPException(403, "一次示范导入不能跨校")
    if libraries["general"].course_id == libraries["chemistry"].course_id:
        raise HTTPException(422, "须指定两个不同教学班")
    return libraries


def import_demo_drafts(db, identity, request: DemoDraftImport, key, budget=ContentBudget()):
    staff(identity)
    require_key(key)
    original = _targets(db, identity, request)

    def action():
        libraries = _targets(db, identity, request)
        for seed in question_seeds():
            _insert_draft(db, identity, libraries[seed.group], seed.content, ())
        for topic, (group, _title, _refs) in TOPICS.items():
            library = libraries[group]
            svg = scene_svg(topic)
            metadata = provenance(topic).model_dump(mode="json")
            asset = SceneAsset(library_id=library.id, svg=svg.svg, content_hash=svg.sha256,
                provenance=metadata, view_box=list(svg.view_box), creator_id=identity.user.id,
                retained_bytes=len(svg.svg.encode("utf-8")) + len(canonical_bytes(metadata)))
            db.add(asset)
            db.flush()
            content = lesson_seed(topic, asset.id)
            actual_asset, sources, questions = _context(db, identity, content, library)
            _insert(db, identity, library, content, actual_asset, sources, questions)
        budget.admit(db, libraries["general"].school_id)
        return {"state": "draft", "question_count": 60, "lesson_count": 6, "scene_count": 6}

    return execute_command(db, identity, original["general"].school_id, "content.demo.import", key,
        {**request.model_dump(mode="json"), "seed_hash": fingerprint({"questions": seed_manifest()["content_hash"],
            "lesson_specs": SPECS, "scenes": {topic: scene_svg(topic).sha256 for topic in TOPICS}})}, action,
        lambda: _targets(db, identity, request))
