"""Real PostgreSQL/API checks for the narrow self metadata contract."""
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlmodel import select

from app.domains.core.models import (
    Course, CourseCatalog, CourseStaff, Enrollment, EnrollmentRequest, LoginSession, Role, RoleGrant, User,
)
from app.seed import fixture_id


def command(client, path, headers, body=None):
    return client.post("/api/v1" + path, headers={**headers, "Idempotency-Key": uuid4().hex},
                       **({"json": body} if body is not None else {}))


def make_course(db, code, *, archived=False, join_approval=False):
    catalog = CourseCatalog(school_id=fixture_id("school-a"), college_id=fixture_id("a-chem"),
                            code=code, title="关系查询 " + code)
    db.add(catalog)
    db.flush()
    course = Course(school_id=catalog.school_id, college_id=catalog.college_id, catalog_id=catalog.id,
                    code=code, title=catalog.title, archived=archived, join_approval=join_approval)
    db.add(course)
    db.flush()
    db.add(CourseStaff(school_id=course.school_id, course_id=course.id,
                       user_id=fixture_id("user-teacher"), is_primary=True))
    return course


def enroll(db, course, status="active", username="student"):
    row = Enrollment(school_id=course.school_id, course_id=course.id,
                     user_id=fixture_id("user-" + username), status=status)
    db.add(row)
    return row


def get_mine(client, headers, **params):
    response = client.get("/api/v1/enrollments/mine", headers=headers, params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_self_relations_report_real_states_and_only_minimal_self_metadata(client, auth, db):
    headers = auth("student")
    rows = []
    for suffix, state, archived in (("A", "active", True), ("B", "withdrawn", False), ("C", "removed", False)):
        course = make_course(db, "HISTORY_" + suffix, archived=archived)
        rows.append((course, enroll(db, course, state)))
    private = make_course(db, "HISTORY_PRIVATE")
    enroll(db, private, username="student_chem")
    db.commit()
    result = get_mine(client, headers, q="HISTORY_")
    assert result["count"] == 3
    assert {row["course_id"] for row in result["data"]} == {str(course.id) for course, _ in rows}
    assert {row["status"] for row in result["data"]} == {"active", "withdrawn", "removed"}
    for row in result["data"]:
        assert set(row) == {"enrollment_id", "course_id", "course_code", "course_title", "course_archived", "status"}
    assert result["data"][0]["course_archived"] is True
    # This student is in the engineering college; a valid cross-college relationship remains visible.
    assert db.get(User, fixture_id("user-student")).college_id != rows[0][0].college_id
    assert get_mine(client, headers, q="PRIVATE")["count"] == 0
    forged = get_mine(client, headers, q="HISTORY_", user_id=str(fixture_id("user-student_chem")),
                      school_id=str(fixture_id("school-b")))
    assert forged == result
    assert get_mine(client, headers, q="ISOLATED")["count"] == 0


def test_another_school_student_reads_only_their_own_school_relationships_and_requests(client, auth, db):
    foreign = User(school_id=fixture_id("school-b"), college_id=fixture_id("b-eng"),
        username="student_foreign", display_name="隔离学校合成学生",
        hashed_password=db.get(User, fixture_id("user-student")).hashed_password)
    db.add(foreign)
    db.flush()
    db.add(RoleGrant(user_id=foreign.id, school_id=foreign.school_id, role=Role.STUDENT))
    course = db.get(Course, fixture_id("course-isolated"))
    db.add(Enrollment(school_id=foreign.school_id, user_id=foreign.id, course_id=course.id))
    db.add(EnrollmentRequest(school_id=foreign.school_id, user_id=foreign.id,
                            course_id=course.id, kind="leave"))
    db.commit()
    headers = auth("student_foreign", "demo-b")
    mine = get_mine(client, headers, user_id=str(fixture_id("user-student")), school_id=str(fixture_id("school-a")))
    assert mine["count"] == 1 and mine["data"][0]["course_code"] == "ISOLATED"
    assert get_mine(client, headers, q="GENERAL")["count"] == 0
    requests = client.get("/api/v1/enrollments/requests", headers=headers).json()
    assert requests["count"] == 1 and requests["data"][0]["course_code"] == "ISOLATED"
    own_a = client.get("/api/v1/enrollments/requests", headers=auth("student")).json()
    assert own_a["count"] == 0


def test_withdraw_remove_and_rejoin_keep_identity_but_never_restore_live_access_from_history(client, auth, db):
    student, teacher = auth("student"), auth("teacher")
    course_id = fixture_id("course-general")
    before = get_mine(client, student, q="GENERAL")["data"][0]["enrollment_id"]
    assert command(client, f"/courses/{course_id}/leave", student).json()["status"] == "withdrawn"
    assert get_mine(client, student, q="GENERAL")["data"][0]["status"] == "withdrawn"
    assert client.get(f"/api/v1/courses/{course_id}", headers=student).status_code == 404
    for private_path in ("members", "management"):
        assert client.get(f"/api/v1/courses/{course_id}/{private_path}", headers=student).status_code != 200
    assert command(client, f"/courses/{course_id}/members", teacher, {"username": "student"}).status_code == 200
    restored = get_mine(client, student, q="GENERAL")["data"][0]
    assert restored["enrollment_id"] == before and restored["status"] == "active"
    assert command(client, f"/courses/{course_id}/remove-member", teacher, {"username": "student"}).status_code == 200
    removed = get_mine(client, student, q="GENERAL")["data"][0]
    assert removed["enrollment_id"] == before and removed["status"] == "removed"
    assert client.get(f"/api/v1/courses/{course_id}", headers=student).status_code == 404
    assert get_mine(client, auth("student_chem"), q="GENERAL")["data"][0]["status"] == "active"


def test_archived_active_relationship_is_separate_from_current_courses(client, auth, db):
    course = make_course(db, "SELF_ARCHIVE")
    enroll(db, course)
    db.commit()
    student, teacher = auth("student"), auth("teacher")
    assert command(client, f"/courses/{course.id}/archive", teacher, {"revision": 1}).status_code == 200
    row = get_mine(client, student, archived=True, status="active")["data"][0]
    assert row["course_id"] == str(course.id) and row["course_archived"] is True and row["status"] == "active"
    assert client.get("/api/v1/courses", headers=student, params={"archived": True}).json()["count"] == 0
    assert client.get(f"/api/v1/courses/{course.id}", headers=student).status_code == 404
    assert get_mine(client, student, q="SELF_ARCHIVE", archived=False)["count"] == 0


def test_pending_requests_have_safe_labels_without_enrollment_and_approval_is_not_current_membership(client, auth, db):
    course = make_course(db, "SELF_PENDING", join_approval=True)
    db.commit()
    student, teacher = auth("student"), auth("teacher")
    issued = command(client, f"/courses/{course.id}/invite", teacher,
                     {"revision": 1, "expires_at": (datetime.now(UTC) + timedelta(days=1)).isoformat()})
    assert issued.status_code == 200
    joining = command(client, "/enrollments/join", student, {"invitation_code": issued.json()["code"]})
    assert joining.status_code == 200 and joining.json()["status"] == "pending_join"
    assert get_mine(client, student, q="SELF_PENDING")["count"] == 0
    request_id = joining.json()["request_id"]
    own = client.get("/api/v1/enrollments/requests", headers=student).json()["data"]
    row = next(value for value in own if value["id"] == request_id)
    assert row["course_code"] == course.code and row["course_title"] == course.title
    assert row["course_archived"] is False and row["created_at"]
    assert {"id", "course_id", "user_id", "display_name", "kind", "status", "created_at", "decided_at"} <= row.keys()
    assert command(client, f"/courses/{course.id}/requests/{request_id}/decide", teacher, {"approve": True}).status_code == 200
    assert command(client, f"/courses/{course.id}/remove-member", teacher, {"username": "student"}).status_code == 200
    row = next(value for value in client.get("/api/v1/enrollments/requests", headers=student).json()["data"] if value["id"] == request_id)
    assert row["status"] == "approved" and row["decided_at"]
    assert get_mine(client, student, q="SELF_PENDING")["data"][0]["status"] == "removed"


def test_filters_counts_pagination_and_literal_keyword_stay_within_self_scope(client, auth, db):
    for code, state in (("PAGE_A", "active"), ("PAGE_B", "withdrawn"), ("PAGE_C", "removed")):
        enroll(db, make_course(db, code), state)
    enroll(db, make_course(db, "PAGE_PRIVATE"), username="student_chem")
    percent = make_course(db, "PERCENT")
    percent.title = "仅本人可见的100%标签"
    enroll(db, percent)
    private_percent = make_course(db, "PRIVATE_PERCENT")
    private_percent.title = "另一个学生的100%标签"
    enroll(db, private_percent, username="student_chem")
    db.commit()
    headers = auth("student")
    pages = [get_mine(client, headers, q="PAGE_", offset=index, limit=1) for index in range(3)]
    assert [value["count"] for value in pages] == [3, 3, 3]
    assert [value["data"][0]["course_code"] for value in pages] == ["PAGE_A", "PAGE_B", "PAGE_C"]
    assert get_mine(client, headers, q="PAGE_", offset=3, limit=1) == {"data": [], "count": 3}
    assert get_mine(client, headers, q="PAGE_", status="withdrawn")["count"] == 1
    literal_percent = get_mine(client, headers, q="%")
    assert literal_percent["count"] == 1 and literal_percent["data"][0]["course_id"] == str(percent.id)
    assert get_mine(client, headers, q="%' OR 1=1 --")["count"] == 0


def test_own_request_pagination_and_labels_do_not_reveal_other_students(client, auth, db):
    instant = datetime(2026, 10, 1, tzinfo=UTC)
    own_ids = []
    for index in range(3):
        course = make_course(db, f"REQUEST_{index}")
        request = EnrollmentRequest(school_id=course.school_id, course_id=course.id,
            user_id=fixture_id("user-student"), kind="join", created_at=instant)
        own_ids.append(request.id)
        db.add(request)
        db.add(EnrollmentRequest(school_id=course.school_id, course_id=course.id,
            user_id=fixture_id("user-student_chem"), kind="join", created_at=instant))
    db.commit()
    headers = auth("student")
    pages = [client.get("/api/v1/enrollments/requests", headers=headers, params={"offset": index, "limit": 1}).json() for index in range(3)]
    assert all(page["count"] == 3 for page in pages)
    assert [page["data"][0]["id"] for page in pages] == [str(value) for value in sorted(own_ids)]
    assert all(page["data"][0]["user_id"] == str(fixture_id("user-student")) for page in pages)
    assert all(page["data"][0]["course_code"].startswith("REQUEST_") for page in pages)


@pytest.mark.parametrize("username,school", [("teacher", "demo-a"), ("admin", "demo-a"), ("platform", "platform"), ("teacher_b", "demo-b")])
def test_self_queries_reject_nonstudent_roles(client, auth, username, school):
    headers = auth(username, school)
    for endpoint in ("/enrollments/mine", "/enrollments/requests"):
        assert client.get("/api/v1" + endpoint, headers=headers).status_code == 403
        assert client.get("/api/v1" + endpoint, headers={**headers, "X-Work-Role": "student"}).status_code == 403


def test_self_queries_require_authentication(client):
    for endpoint in ("/enrollments/mine", "/enrollments/requests"):
        assert client.get("/api/v1" + endpoint).status_code == 401


@pytest.mark.parametrize("change,expected", [("password", 403), ("revoked", 401), ("disabled", 401), ("role", 403)])
def test_self_queries_recheck_account_and_role_on_every_request(client, auth, db, change, expected):
    headers = auth("student")
    user = db.get(User, fixture_id("user-student"))
    if change == "password":
        user.must_change_password = True
        db.add(user)
    elif change == "disabled":
        user.is_active = False
        db.add(user)
    elif change == "revoked":
        for login in db.exec(select(LoginSession).where(LoginSession.user_id == user.id)).all():
            login.revoked = True
            db.add(login)
    else:
        for grant in db.exec(select(RoleGrant).where(RoleGrant.user_id == user.id)).all():
            db.delete(grant)
    db.commit()
    for endpoint in ("/enrollments/mine", "/enrollments/requests"):
        assert client.get("/api/v1" + endpoint, headers=headers).status_code == expected


@pytest.mark.parametrize("params", [{"offset": -1}, {"limit": 0}, {"limit": 101}, {"q": "x" * 101}, {"status": "other"}, {"archived": "other"}])
def test_self_relation_query_bounds_are_validated(client, auth, params):
    assert client.get("/api/v1/enrollments/mine", headers=auth("student"), params=params).status_code == 422
