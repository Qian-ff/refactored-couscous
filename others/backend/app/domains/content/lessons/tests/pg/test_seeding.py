"""Draft-only seeding on A副2's real migrated PG; synthetic scopes, no professional approval."""
from uuid import UUID

from sqlalchemy import func
from sqlmodel import select

from app.domains.content.lessons.models import Lesson, LessonDraft, LessonPublication, LessonReview
from app.domains.content.lessons.seeding import DemoDraftImport, import_demo_drafts
from app.domains.content.questions.models import Question, QuestionDraft, QuestionPublication, QuestionReview
from app.domains.content.questions.tests.pg.test_workflows import SEMANTIC_BUDGET, identity
from app.domains.content.schemas import LibraryCreate
from app.domains.content.services import create_library
from app.domains.core.models import Course


def test_two_existing_course_scopes_receive_only_sixty_drafts_and_six_lessons(db):
    admin = identity(db, "admin", "administrator")
    source = db.exec(select(Course).where(Course.school_id == admin.user.school_id)).first()
    assert source is not None, "A副2 fixture must include a real school/college/catalog/course"
    courses = [Course(school_id=source.school_id, college_id=source.college_id, catalog_id=source.catalog_id,
        code="C1-DEMO-" + key, title="Synthetic C1 demo " + key) for key in ("GENERAL", "CHEMISTRY")]
    db.add_all(courses)
    db.commit()
    libraries = []
    for ordinal, course in enumerate(courses):
        created = create_library(db, admin, LibraryCreate(scope="course", parent_id=course.id,
            title="Synthetic C1 demo course", audience="all"), f"c1-demo-bank-{ordinal}")
        libraries.append(UUID(created["library_id"]))
    review_models = (QuestionReview, QuestionPublication, LessonReview, LessonPublication)
    before = [db.exec(select(func.count()).select_from(model)).one() for model in review_models]
    request = DemoDraftImport(general_library_id=libraries[0], chemistry_library_id=libraries[1])
    result = import_demo_drafts(db, admin, request, "c1-demo-draft-import", SEMANTIC_BUDGET)
    assert import_demo_drafts(db, admin, request, "c1-demo-draft-import", SEMANTIC_BUDGET) == result
    assert result == {"state": "draft", "question_count": 60, "lesson_count": 6, "scene_count": 6}
    for library_id in libraries:
        assert db.exec(select(func.count()).select_from(QuestionDraft).join(Question).where(Question.library_id == library_id)).one() == 30
        assert db.exec(select(func.count()).select_from(LessonDraft).join(Lesson).where(Lesson.library_id == library_id)).one() == 3
    assert [db.exec(select(func.count()).select_from(model)).one() for model in review_models] == before
