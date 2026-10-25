"""Pure whitelist projection, not an authorization entrypoint.

Callers must authorize the exact retained version and B2 task before using this helper.
Source references are supplied only after separate current material authorization.
"""
import hashlib

from app.domains.content.lessons.schemas import (
    Choice, Hotspot, LessonContent, StudentChoice, StudentHotspot, StudentLesson, StudentOrder,
)


def student_projection(content: LessonContent, lesson_id, version_id, readable_sources=None):
    readable_sources = readable_sources or {}
    result = []
    for activity in content.activities:
        def presentation_key(item):
            return hashlib.sha256(f"{version_id}:{activity.id}:{item.id}".encode()).digest()
        base = dict(id=activity.id, prompt=activity.prompt, source_refs=readable_sources.get(activity.id, ()))
        if isinstance(activity, Choice):
            result.append(StudentChoice(**base, kind="choice", selection=activity.selection,
                                        options=tuple(sorted(activity.options, key=presentation_key))))
        elif isinstance(activity, Hotspot):
            result.append(StudentHotspot(**base, kind="hotspot", scene_id=activity.scene_id,
                                         regions=tuple(sorted(activity.regions, key=presentation_key))))
        else:
            items = tuple(sorted(activity.items, key=presentation_key))
            result.append(StudentOrder(**base, kind="order", items=items))
    return StudentLesson(lesson_id=lesson_id, version_id=version_id, title=content.title,
                         short_lesson=content.short_lesson, required=content.required,
                         scene=content.scene, activities=tuple(result))
