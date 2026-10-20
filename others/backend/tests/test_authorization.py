from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.models import Course, RoleGrant, User
from app.seed import fixture_id


@pytest.mark.parametrize(("username", "school", "count"), [
    ("platform", "platform", 3), ("admin", "demo-a", 2), ("college", "demo-a", 1),
    ("teacher", "demo-a", 1), ("teacher_eng", "demo-a", 1),
    ("student", "demo-a", 1), ("student_chem", "demo-a", 1),
    ("admin_b", "demo-b", 1), ("teacher_b", "demo-b", 1),
])
def test_role_scopes(client, auth, username, school, count):
    response = client.get("/api/v1/courses", headers=auth(username, school))
    assert response.status_code == 200
    assert response.json()["count"] == count


def test_invalid_credentials_and_school(client):
    for school, username, password in (("demo-a", "teacher", "incorrect"), ("missing", "platform", "A1-synthetic-only-test-password"),
                                        ("demo-b", "teacher", "A1-synthetic-only-test-password")):
        response = client.post("/api/v1/auth/login", json={"school_code": school, "username": username, "password": password})
        assert response.status_code == 401


def test_logout_revokes_token(client, auth):
    headers = auth()
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    assert client.get("/api/v1/courses").status_code == 401
    assert client.get("/api/v1/courses", headers={"Authorization": "Bearer invalid"}).status_code == 401


def test_cross_tenant_read_and_write_denied(client, auth):
    headers = auth("admin")
    assert client.get(f"/api/v1/courses/{fixture_id('course-isolated')}", headers=headers).status_code == 404
    assert client.post("/api/v1/courses", headers=headers, json={
        "college_id": str(fixture_id("b-chem")), "teacher_id": str(fixture_id("user-teacher_b")),
        "code": "EVIL", "title": "Forbidden"}).status_code == 403


def test_college_admin_scope_and_context(client, auth):
    headers = auth("college")
    assert client.get(f"/api/v1/courses/{fixture_id('course-electrical')}", headers=headers).status_code == 404
    data = client.get("/api/v1/courses/context", headers=headers).json()
    assert {c["id"] for c in data["colleges"]} == {str(fixture_id("a-chem"))}
    assert client.post("/api/v1/courses", headers=headers, json={
        "college_id": str(fixture_id("a-eng")), "teacher_id": str(fixture_id("user-teacher_eng")),
        "code": "EVIL", "title": "Forbidden"}).status_code == 403


def test_cross_college_enrollment_minimum_data(client, auth):
    headers = auth("student")  # Engineering student enrolled in a chemistry course.
    me = client.get("/api/v1/auth/me", headers=headers).json()
    assert me["college"]["id"] == str(fixture_id("a-eng"))
    assert "courses:create" not in me["permissions"]
    assert not any("monitor" in permission for permission in me["permissions"])
    data = client.get(f"/api/v1/courses/{fixture_id('course-general')}", headers=headers)
    assert data.status_code == 200
    assert set(data.json()) == {"id", "school_id", "college_id", "catalog_id", "college_name", "code", "title", "teacher_name"}
    assert client.get(f"/api/v1/courses/{fixture_id('course-electrical')}", headers=headers).status_code == 404
    assert client.get("/api/v1/courses/context", headers=headers).json() == {"can_create": False, "colleges": [], "teachers": []}
    assert client.post("/api/v1/courses", headers=headers, json={
        "college_id": str(fixture_id("a-chem")), "teacher_id": str(fixture_id("user-teacher")),
        "code": "EVIL", "title": "Forbidden"}).status_code == 403


def test_course_write_read_conflict_and_ignored_forged_school(client, auth):
    body = {"college_id": str(fixture_id("a-chem")), "teacher_id": str(fixture_id("user-teacher")),
            "code": "A1-NEW", "title": "New course", "school_id": str(fixture_id("school-b"))}
    response = client.post("/api/v1/courses", headers=auth(), json=body)
    assert response.status_code == 201, response.text
    record = response.json()
    assert record["school_id"] == str(fixture_id("school-a"))
    assert client.get(f"/api/v1/courses/{record['id']}", headers=auth("admin")).status_code == 200
    assert client.get(f"/api/v1/courses/{record['id']}", headers=auth("admin_b", "demo-b")).status_code == 404
    assert client.post("/api/v1/courses", headers=auth(), json=body).status_code == 409


def test_role_revocation_and_disabled_user_take_effect_immediately(client, auth, db):
    headers = auth()
    grant = db.exec(select(RoleGrant).where(RoleGrant.user_id == fixture_id("user-teacher"))).first()
    db.delete(grant)
    db.commit()
    assert client.get("/api/v1/courses", headers=headers).status_code == 403
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 403
    user = db.get(User, fixture_id("user-teacher"))
    user.is_active = False
    db.add(user)
    db.commit()
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_postgresql_rejects_cross_tenant_foreign_key(db):
    db.add(Course(id=uuid4(), school_id=fixture_id("school-b"), college_id=fixture_id("a-chem"), code="BAD-FK", title="Invalid"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_school_admin_instances_share_database_state(client, auth):
    first, second = auth("admin"), auth("admin")
    response = client.post("/api/v1/courses", headers=first, json={
        "college_id": str(fixture_id("a-eng")), "teacher_id": str(fixture_id("user-teacher_eng")),
        "code": "SHARED", "title": "Shared state"})
    assert response.status_code == 201
    assert client.get(f"/api/v1/courses/{response.json()['id']}", headers=second).status_code == 200
