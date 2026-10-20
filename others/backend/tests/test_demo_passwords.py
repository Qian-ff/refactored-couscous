from conftest import TEST_PASSWORD
from sqlmodel import select

from app.core.security import get_password_hash, verify_password
from app.models import Course, RoleGrant, User
from app.seed import fixture_id, reset_demo_passwords, seed


def test_demo_reset_changes_login_without_reseeding_business_data(db, client, auth):
    old_login = auth("teacher")
    teacher = db.get(User, fixture_id("user-teacher"))
    ordinary = User(school_id=teacher.school_id, username="ordinary-user", display_name="Ordinary",
                    hashed_password=get_password_hash(TEST_PASSWORD))
    db.add(ordinary)
    db.flush()
    db.add(RoleGrant(user_id=ordinary.id, school_id=ordinary.school_id, role="teacher"))
    course = db.get(Course, fixture_id("course-general"))
    course.title = "Keep this edited course"
    db.add(course)
    removed_grant = db.get(RoleGrant, fixture_id("grant-teacher_eng"))
    db.delete(removed_grant)
    db.commit()
    ordinary_login = auth("ordinary-user")
    course_ids = {item.id for item in db.exec(select(Course)).all()}

    reset_demo_passwords(db, "88888888")
    db.commit()

    assert client.get("/api/v1/auth/me", headers=old_login).status_code == 401
    for username, role in (("student", "student"), ("teacher", "teacher"), ("admin", "school_admin")):
        response = client.post("/api/v1/auth/login", json={
            "school_code": "demo-a", "username": username, "password": "88888888"})
        assert response.status_code == 200
        headers = {"Authorization": "Bearer " + response.json()["access_token"]}
        identity = client.get("/api/v1/auth/me", headers=headers)
        assert identity.status_code == 200
        assert role in {grant["role"] for grant in identity.json()["grants"]}
        assert client.post("/api/v1/auth/login", json={
            "school_code": "demo-a", "username": username, "password": TEST_PASSWORD}).status_code == 401

    assert verify_password(TEST_PASSWORD, ordinary.hashed_password)[0]
    assert not verify_password("88888888", ordinary.hashed_password)[0]
    assert client.get("/api/v1/auth/me", headers=ordinary_login).status_code == 200
    assert client.post("/api/v1/auth/login", json={
        "school_code": "demo-a", "username": ordinary.username, "password": "88888888"}).status_code == 401
    assert db.get(Course, course.id).title == "Keep this edited course"
    assert {item.id for item in db.exec(select(Course)).all()} == course_ids
    assert db.get(RoleGrant, fixture_id("grant-teacher_eng")) is None


def test_regular_seed_preserves_explicitly_reset_passwords(db, client):
    reset_demo_passwords(db, "88888888")
    db.commit()
    seed(db, TEST_PASSWORD)
    response = client.post("/api/v1/auth/login", json={
        "school_code": "demo-a", "username": "teacher", "password": "88888888"})
    assert response.status_code == 200
