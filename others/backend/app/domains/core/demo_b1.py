"""Explicit synthetic B1 examples. Never invoked on startup and never overwrites a password.

A can run with the shared entry: backend app.domains.core.demo_b1. Requires the existing
synthetic A0 organization and SAFELAB_DEMO_PASSWORD from ignored configuration.
"""
import os

from sqlmodel import Session

from app.core.config import settings
from app.core.db import engine
from app.core.grants import add_role_grant
from app.core.security import get_password_hash
from app.domains.core.models import College, Course, CourseCatalog, CourseStaff, Enrollment, Major, Role, School, User
from app.seed import fixture_id


def seed_b1_examples(db: Session, password: str):
    if settings.APP_ENV == "production":
        raise RuntimeError("Synthetic B1 seeding is disabled in production")
    if not 8 <= len(password) <= 256:
        raise ValueError("A synthetic development password is required")
    school = db.get(School, fixture_id("school-a"))
    chemistry, engineering = (db.get(College, fixture_id(name)) for name in ("a-chem", "a-eng"))
    if school is None or chemistry is None or engineering is None:
        raise ValueError("Seed A0 synthetic organizations first")

    def existing_or_add(model, key, **fields):
        record_id = fixture_id("b1-demo-" + key)
        record = db.get(model, record_id)
        if record is None:
            record = model(id=record_id, **fields)
            db.add(record)
            db.flush()
        return record

    major = existing_or_add(Major, "major-eng", school_id=school.id, college_id=engineering.id,
                            code="B1-ENG", name="示范工程专业")
    student = existing_or_add(User, "student-cross", school_id=school.id, college_id=engineering.id,
        major_id=major.id, username="b1_student_cross", display_name="跨学院示范学生", student_no="B1-20260001",
        hashed_password=get_password_hash(password))
    add_role_grant(db, user_id=student.id, role=Role.STUDENT)
    catalog = existing_or_add(CourseCatalog, "catalog", school_id=school.id, college_id=chemistry.id,
        owner_id=fixture_id("user-teacher"), code="B1-LAB-CATALOG", title="实验室安全协同示范课程")
    classes = []
    for suffix, college, teacher, title in (
        ("chem", chemistry, "teacher", "化学学院教学班"), ("eng", engineering, "teacher_eng", "工程学院教学班"),
    ):
        course = existing_or_add(Course, "class-" + suffix, school_id=school.id, college_id=college.id,
            catalog_id=catalog.id, code="B1-CLASS-" + suffix.upper(), title=title)
        existing_or_add(CourseStaff, "staff-" + suffix, school_id=school.id, course_id=course.id,
                        user_id=fixture_id("user-" + teacher), is_primary=True)
        classes.append(course)
    existing_or_add(Enrollment, "cross-enrollment", school_id=school.id, course_id=classes[0].id, user_id=student.id)
    result = {"catalog_id": str(catalog.id), "course_ids": [str(course.id) for course in classes],
              "student_username": student.username, "student_no": student.student_no,
              "note": "学生仅加入化学学院班；另一班名单私有，共享内容需由C审核发布后验证。既有密码与关系不覆盖。"}
    db.commit()
    return result


if __name__ == "__main__":
    import json
    password = os.environ.get("SAFELAB_DEMO_PASSWORD", "")
    with Session(engine) as db:
        print(json.dumps(seed_b1_examples(db, password), ensure_ascii=False))
