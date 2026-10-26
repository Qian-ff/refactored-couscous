from datetime import datetime
from uuid import UUID

from app.domains.content.lessons.schemas import LessonContent
from app.domains.content.questions.schemas import StrictModel


class DraftView(StrictModel):
    lesson_id: UUID
    library_id: UUID
    revision: int
    parent_revision: int
    retired: bool
    can_edit: bool
    content: LessonContent
    updated_at: datetime


class VersionView(StrictModel):
    lesson_id: UUID
    version_id: UUID
    library_id: UUID
    version_no: int
    title: str
    required: bool
    created_at: datetime
