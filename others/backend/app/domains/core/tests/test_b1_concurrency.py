"""Independent committed synthetic rows for real concurrent HTTP transactions."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import delete
from sqlmodel import Session, select

from app.core.db import engine
from app.core.grants import add_role_grant
from app.core.security import get_password_hash
from app.domains.core.models import (
    AccountInvitation, College, CommandReceipt, CoreAuditEvent, Course, CourseCatalog,
    CourseStaff, Enrollment, EnrollmentRequest, LoginSession, Major, Role, RoleGrant, School, User,
)
from app.main import app

PASSWORD = "Synthetic-Concurrent-B1-Only"


@pytest.fixture
def race_rows(migrated_database):
    school = School(code="b1-race-" + uuid4().hex[:12], name="合成并发学校")
    college = College(school_id=school.id, code="chem", name="合成学院")
    major = Major(school_id=school.id, college_id=college.id, code="major", name="合成专业")
    hashed = get_password_hash(PASSWORD)
    users = {name: User(school_id=school.id, college_id=college.id, username=name, display_name=name,
                        hashed_password=hashed) for name in ("admin", "one", "two", "three", "candidate")}
    users["candidate"].major_id, users["candidate"].student_no = major.id, "independent-student-number"
    catalog = CourseCatalog(school_id=school.id, college_id=college.id, owner_id=users["one"].id, code="catalog", title="并发课程")
    course = Course(school_id=school.id, college_id=college.id, catalog_id=catalog.id, code="class", title="并发教学班")
    school_id = school.id
    user_ids = [user.id for user in users.values()]
    race_data = {"school_code": school.code, "school_id": school.id,
                 "users": {key: value.id for key, value in users.items()}, "course_id": course.id}
    with Session(engine) as db:
        for row in (school, college, major):
            db.add(row)
            db.flush()
        for user in users.values():
            db.add(user)
        db.flush()
        for name in ("admin", "one", "two", "three"):
            add_role_grant(db, user_id=users[name].id, role=Role.SCHOOL_ADMIN if name == "admin" else Role.TEACHER)
        db.add(catalog)
        db.flush()
        db.add(course)
        db.flush()
        db.add(CourseStaff(school_id=school.id, course_id=course.id, user_id=users["one"].id, is_primary=True))
        db.commit()
    try:
        yield race_data
    finally:
        # Only this fixture's explicit UUIDs in the dedicated test database are removed.
        with Session(engine) as db:
            db.exec(delete(CommandReceipt).where(CommandReceipt.subject.in_([str(value) for value in user_ids])))
            for model in (CoreAuditEvent, EnrollmentRequest, AccountInvitation, Enrollment, CourseStaff,
                          Course, CourseCatalog, RoleGrant):
                db.exec(delete(model).where(model.school_id == school_id))
            db.exec(delete(LoginSession).where(LoginSession.user_id.in_(user_ids)))
            db.exec(delete(User).where(User.id.in_(user_ids)))
            for model in (Major, College):
                db.exec(delete(model).where(model.school_id == school_id))
            db.exec(delete(School).where(School.id == school_id))
            db.commit()


def race_requests(rows, requests):
    barrier = Barrier(2)
    with TestClient(app) as browser:
        response = browser.post("/api/v1/auth/login", json={"school_code": rows["school_code"],
                                                           "username": "admin", "password": PASSWORD})
        assert response.status_code == 200
        token = response.json()["access_token"]
        def submit(item):
            path, body = item
            barrier.wait(timeout=10)
            return browser.post("/api/v1" + path, headers={"Authorization": "Bearer " + token,
                "Idempotency-Key": uuid4().hex}, json=body).status_code
        with ThreadPoolExecutor(max_workers=2) as workers:
            futures = [workers.submit(submit, request) for request in requests]
            return sorted(future.result(timeout=30) for future in futures)


def test_role_family_cannot_be_bypassed_by_simultaneous_b1_grant_requests(race_rows):
    user_id = race_rows["users"]["candidate"]
    path = f"/admin/accounts/{user_id}/grants"
    assert race_requests(race_rows, [(path, {"role": "student"}), (path, {"role": "teacher"})]) == [200, 422]
    with Session(engine) as db:
        grants = db.exec(select(RoleGrant).where(RoleGrant.user_id == user_id)).all()
        assert len(grants) == 1


def test_simultaneous_primary_handover_has_one_winner(race_rows):
    path = f"/courses/{race_rows['course_id']}/transfer"
    changes = [(path, {"revision": 1, "teacher_id": str(race_rows["users"][name])}) for name in ("two", "three")]
    assert race_requests(race_rows, changes) == [200, 409]
    with Session(engine) as db:
        primary = db.exec(select(CourseStaff).where(CourseStaff.course_id == race_rows["course_id"],
                          CourseStaff.is_primary.is_(True), CourseStaff.is_active.is_(True))).all()
        assert len(primary) == 1 and primary[0].user_id in {race_rows["users"]["two"], race_rows["users"]["three"]}
