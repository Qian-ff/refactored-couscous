"""Explicit, synthetic development fixtures. Never runs automatically in production."""
import json
import os
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlmodel import Session

from app.core.config import ROOT, settings
from app.core.db import engine
from app.core.security import get_password_hash
from app.models import College, Course, CourseStaff, Enrollment, Role, RoleGrant, School, User


def fixture_id(name: str) -> UUID:
    return uuid5(NAMESPACE_URL, "https://safelab.invalid/fixtures/" + name)


def seed(session: Session, password: str) -> dict:
    def add(model, key: str, **values):
        record = session.get(model, fixture_id(key))
        if record is None:
            record = model(id=fixture_id(key), **values)
            session.add(record)
            session.flush()
        elif model is School:
            record.name = values["name"]
            session.add(record)
        return record

    schools, colleges, users, courses = {}, {}, {}, {}
    for key, name in (("a", "示范大学 A"), ("b", "隔离验证大学")):
        schools[key] = add(School, "school-" + key, code="demo-" + key, name=name)
        for suffix, title in (("chem", "化学学院"), ("eng", "工程学院")):
            college_key = key + "-" + suffix
            colleges[college_key] = add(College, college_key, school_id=schools[key].id, code=suffix, name=title)
    accounts = [
        ("platform", None, None, Role.PLATFORM_ADMIN, "平台运维"),
        ("admin", "a", None, Role.SCHOOL_ADMIN, "学校管理员"),
        ("college", "a", "a-chem", Role.COLLEGE_ADMIN, "化学院管理员"),
        ("teacher", "a", "a-chem", Role.TEACHER, "陈老师"),
        ("teacher_eng", "a", "a-eng", Role.TEACHER, "周老师"),
        ("student", "a", "a-eng", Role.STUDENT, "林同学"),
        ("student_chem", "a", "a-chem", Role.STUDENT, "沈同学"),
        ("admin_b", "b", None, Role.SCHOOL_ADMIN, "隔离学校管理员"),
        ("teacher_b", "b", "b-chem", Role.TEACHER, "隔离学校教师"),
    ]
    password_hash = get_password_hash(password)
    for username, school_key, college_key, role, display in accounts:
        school_id = schools[school_key].id if school_key else None
        college_id = colleges[college_key].id if college_key else None
        users[username] = add(User, "user-" + username, school_id=school_id, college_id=college_id,
                              username=username, display_name=display, hashed_password=password_hash)
        add(RoleGrant, "grant-" + username, user_id=users[username].id, school_id=school_id, role=role,
            college_id=college_id if role == Role.COLLEGE_ADMIN else None)
    for key, title, college_key, teacher in (
        ("general", "实验室通识安全", "a-chem", "teacher"),
        ("electrical", "工程实验室基础安全", "a-eng", "teacher_eng"),
        ("isolated", "隔离学校验证课程", "b-chem", "teacher_b"),
    ):
        college = colleges[college_key]
        courses[key] = add(Course, "course-" + key, school_id=college.school_id, college_id=college.id,
                           code=key.upper(), title=title)
        add(CourseStaff, "staff-" + key, school_id=college.school_id, course_id=courses[key].id,
            user_id=users[teacher].id, is_primary=True)
    for username in ("student", "student_chem"):
        add(Enrollment, "enroll-" + username, school_id=schools["a"].id,
            course_id=courses["general"].id, user_id=users[username].id)
    session.commit()
    return {"accounts": [{"school_code": "demo-" + school if school else "platform", "username": username,
                           "display_name": display, "role": role} for username, school, _, role, display in accounts],
            "ids": {"colleges": {key: str(v.id) for key, v in colleges.items()},
                    "users": {key: str(v.id) for key, v in users.items()},
                    "courses": {key: str(v.id) for key, v in courses.items()}}}


if __name__ == "__main__":
    if settings.APP_ENV == "production":
        raise SystemExit("Synthetic fixture seeding is disabled in production")
    password = os.environ.get("SAFELAB_DEMO_PASSWORD")
    if not password:
        from dotenv import dotenv_values
        password = dotenv_values(ROOT / ".env").get("SAFELAB_DEMO_PASSWORD")
    if not password or len(password) < 12:
        raise SystemExit("Run the local setup script to generate SAFELAB_DEMO_PASSWORD")
    with Session(engine) as db:
        result = seed(db, password)
    target: Path = ROOT / "others/runtime/demo-accounts.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({**result, "password": password}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Synthetic accounts are available in the ignored others/runtime/demo-accounts.json")
