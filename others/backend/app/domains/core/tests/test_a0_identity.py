"""Located in the domain to verify that real database fixtures are inherited here."""
import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.core.grants import add_role_grant
from app.core.release import VERSION
from app.models import Course, CourseCatalog, Enrollment, Role, RoleGrant
from app.seed import fixture_id


def test_work_identity_narrows_and_revocation_does_not_escalate(client, auth, db):
    add_role_grant(db, user_id=fixture_id("user-teacher"), role=Role.SCHOOL_ADMIN)
    db.commit()
    headers = auth()
    me = client.get("/api/v1/auth/me", headers=headers).json()
    assert me["available_work_roles"] == ["teacher", "administrator"]
    assert me["active_work_role"] == "teacher"
    assert {g["role"] for g in me["effective_grants"]} == {"teacher"}
    assert client.get("/api/v1/courses", headers=headers).json()["count"] == 1
    admin = {**headers, "X-Work-Role": "administrator"}
    assert client.get("/api/v1/courses", headers=admin).json()["count"] == 2
    assert client.get("/api/v1/courses", headers={**headers, "X-Work-Role": "student"}).status_code == 403
    grant = db.get(RoleGrant, fixture_id("grant-teacher"))
    db.delete(grant)
    db.commit()
    assert client.get("/api/v1/courses", headers=headers).status_code == 403
    assert client.get("/api/v1/courses", headers={**headers, "X-Work-Role": "teacher"}).status_code == 403
    assert client.get("/api/v1/courses", headers=admin).status_code == 200
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200


def test_multiple_college_ranges_only_apply_to_administrator(client, auth, db):
    add_role_grant(db, user_id=fixture_id("user-college"), role=Role.COLLEGE_ADMIN,
                   college_id=fixture_id("a-eng"))
    db.commit()
    me = client.get("/api/v1/auth/me", headers=auth("college")).json()
    assert len(me["effective_grants"]) == 2
    assert client.get("/api/v1/courses", headers=auth("college")).json()["count"] == 2


def test_student_staff_conflict_rejected_by_shared_writer_and_database(db):
    with pytest.raises(ValueError, match="学生账号"):
        add_role_grant(db, user_id=fixture_id("user-student"), role=Role.TEACHER)
    db.add(RoleGrant(user_id=fixture_id("user-student"), school_id=fixture_id("school-a"), role=Role.TEACHER))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_legacy_creation_produces_catalog_and_rejects_cross_school_catalog(client, auth, db):
    response = client.post("/api/v1/courses", headers=auth(), json={
        "college_id": str(fixture_id("a-chem")), "teacher_id": str(fixture_id("user-teacher")),
        "code": "A0-LEGACY", "title": "Same title"})
    assert response.status_code == 201
    record = response.json()
    assert record["id"] != record["catalog_id"]
    catalog = db.get(CourseCatalog, record["catalog_id"])
    assert catalog.school_id == fixture_id("school-a")
    other = db.get(Course, fixture_id("course-isolated"))
    other.catalog_id = catalog.id
    db.add(other)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_catalog_ownership_does_not_authorize_a_private_class(client, auth, db):
    course = db.get(Course, fixture_id("course-electrical"))
    catalog = db.get(CourseCatalog, course.catalog_id)
    catalog.owner_id = fixture_id("user-teacher")
    db.add(catalog)
    db.commit()
    assert client.get(f"/api/v1/courses/{course.id}", headers=auth()).status_code == 404
    assert db.exec(select(Enrollment)).first() is not None


def test_cors_work_identity_write_headers_and_version(client):
    response = client.options("/api/v1/courses", headers={
        "Origin": "http://127.0.0.1:5176", "Access-Control-Request-Method": "PATCH",
        "Access-Control-Request-Headers": "authorization,x-work-role,idempotency-key,if-match"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5176"
    assert client.get("/api/v1/health").json()["contract"] == VERSION
