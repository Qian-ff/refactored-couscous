"""Private authoring data and explicit labconnect.lesson/1 student projection."""
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.domains.content.questions.schemas import (
    ID_PATTERN, Option, Provenance, SourcePointer, StrictModel, canonical_bytes, clean_text,
)


class ActivityBase(StrictModel):
    id: str = Field(pattern=ID_PATTERN)
    prompt: str = Field(min_length=1, max_length=4000)
    sources: tuple[SourcePointer, ...] = Field(default=(), max_length=20)

    _prompt = field_validator("prompt")(clean_text)

    @model_validator(mode="after")
    def unique_sources(self):
        refs = [(item.material_version_id, item.chunk_id) for item in self.sources]
        if len(set(refs)) != len(refs):
            raise ValueError("活动来源不能重复")
        return self


class Choice(ActivityBase):
    kind: Literal["choice"]
    selection: Literal["single", "multiple"]
    options: tuple[Option, ...] = Field(min_length=2, max_length=8)
    question_version_id: UUID | None = None


class Region(StrictModel):
    id: str = Field(pattern=ID_PATTERN)
    label: str = Field(min_length=1, max_length=1000)
    x: float = Field(ge=0, le=1, allow_inf_nan=False, strict=True)
    y: float = Field(ge=0, le=1, allow_inf_nan=False, strict=True)
    width: float = Field(gt=0, le=1, allow_inf_nan=False, strict=True)
    height: float = Field(gt=0, le=1, allow_inf_nan=False, strict=True)

    _label = field_validator("label")(clean_text)

    @model_validator(mode="after")
    def in_scene(self):
        if self.x + self.width > 1 or self.y + self.height > 1:
            raise ValueError("热点矩形须在场景内")
        return self


class Hotspot(ActivityBase):
    kind: Literal["hotspot"]
    scene_id: str = Field(pattern=ID_PATTERN)
    regions: tuple[Region, ...] = Field(min_length=2, max_length=50)


class Order(ActivityBase):
    kind: Literal["order"]
    items: tuple[Option, ...] = Field(min_length=2, max_length=12)


Activity = Annotated[Choice | Hotspot | Order, Field(discriminator="kind")]


class Scoring(StrictModel):
    activity_id: str = Field(pattern=ID_PATTERN)
    correct_ids: tuple[str, ...] = Field(min_length=1, max_length=50)
    explanation: str = Field(min_length=1, max_length=8000)

    _explanation = field_validator("explanation")(clean_text)


class Scene(StrictModel):
    id: str = Field(pattern=ID_PATTERN)
    svg_asset_id: UUID
    accessible_description: str = Field(min_length=1, max_length=4000)

    _description = field_validator("accessible_description")(clean_text)


class LessonContent(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    short_lesson: str = Field(min_length=1, max_length=32000)
    required: bool = Field(default=True, strict=True)
    scene: Scene
    activities: tuple[Activity, ...] = Field(min_length=1, max_length=50)
    scoring: tuple[Scoring, ...] = Field(min_length=1, max_length=50)
    provenance: Provenance = Field(default_factory=Provenance)

    _text = field_validator("title", "short_lesson")(clean_text)

    @model_validator(mode="after")
    def validate_scoring(self):
        activities = {activity.id: activity for activity in self.activities}
        scores = {item.activity_id: item for item in self.scoring}
        if len(activities) != len(self.activities) or len(scores) != len(self.scoring) or activities.keys() != scores.keys():
            raise ValueError("活动ID须唯一，且每个活动恰有一份评分数据")
        for activity in self.activities:
            score = scores[activity.id]
            options = activity.options if isinstance(activity, Choice) else (
                activity.regions if isinstance(activity, Hotspot) else activity.items)
            ids = [option.id for option in options]
            correct = score.correct_ids
            if len(set(ids)) != len(ids) or len(set(correct)) != len(correct) or not set(correct) <= set(ids):
                raise ValueError("活动选项/答案ID重复或不匹配")
            if isinstance(activity, Choice) and activity.selection == "single" and len(correct) != 1:
                raise ValueError("单选活动须恰有一个答案")
            if isinstance(activity, Choice) and activity.selection == "multiple" and len(correct) < 2:
                raise ValueError("多选活动须至少两个正确选项")
            if isinstance(activity, Order) and set(correct) != set(ids):
                raise ValueError("排序答案须为全部选项的排列")
            if isinstance(activity, Hotspot) and activity.scene_id != self.scene.id:
                raise ValueError("热点场景引用不匹配")
        if len(canonical_bytes(self)) > 1048576:
            raise ValueError("关卡载荷不能超过1MiB")
        return self


class LessonCreate(StrictModel):
    library_id: UUID
    content: LessonContent


class LessonChange(StrictModel):
    revision: int = Field(ge=1, strict=True)
    content: LessonContent


class SceneCreate(StrictModel):
    library_id: UUID
    svg: str = Field(min_length=1, max_length=262144)
    provenance: Provenance = Field(default_factory=Provenance)


class StudentReference(StrictModel):
    material_id: UUID
    version_id: UUID
    page: int | None = Field(default=None, ge=1)
    paragraph: str | None = Field(default=None, max_length=100)


class StudentActivityBase(StrictModel):
    id: str
    prompt: str
    source_refs: tuple[StudentReference, ...]


class StudentChoice(StudentActivityBase):
    kind: Literal["choice"]
    selection: Literal["single", "multiple"]
    options: tuple[Option, ...]


class StudentHotspot(StudentActivityBase):
    kind: Literal["hotspot"]
    scene_id: str
    regions: tuple[Region, ...]


class StudentOrder(StudentActivityBase):
    kind: Literal["order"]
    items: tuple[Option, ...]


StudentActivity = Annotated[StudentChoice | StudentHotspot | StudentOrder, Field(discriminator="kind")]


class StudentLesson(StrictModel):
    schema_version: Literal["labconnect.lesson/1"] = "labconnect.lesson/1"
    lesson_id: UUID
    version_id: UUID
    title: str
    short_lesson: str
    required: bool
    scene: Scene
    activities: tuple[StudentActivity, ...]


class TeacherLessonPreview(StrictModel):
    mode: Literal["teacher-preview"] = "teacher-preview"
    lesson: StudentLesson
    review: tuple[Scoring, ...]
