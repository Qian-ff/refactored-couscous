"""A's public mounting, compatibility migration and validation-redaction checks."""
import subprocess
import sys
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from test_a0_migration import old_database, old_rows


def test_b1_additive_upgrade_retains_a0_catalogs_and_server_defaults():
    with old_database() as (engine, env, command):
        ids = old_rows(engine)
        subprocess.run([*command, "e24a0c0a0001"], env=env, check=True, capture_output=True)
        with engine.connect() as db:
            catalogs = db.execute(text("SELECT id,catalog_id FROM course ORDER BY code")).all()
        subprocess.run([*command, "head"], env=env, check=True, capture_output=True)
        with engine.connect() as db:
            assert db.execute(text("SELECT id,catalog_id FROM course ORDER BY code")).all() == catalogs
            assert db.execute(text("SELECT id FROM course_staff")).scalar_one() == ids["staff"]
            assert db.execute(text("SELECT id FROM enrollment")).scalar_one() == ids["enroll"]
            assert db.execute(text("SELECT count(*) FROM app_user WHERE student_no IS NULL AND major_id IS NULL "
                                   "AND NOT must_change_password AND revision=1")).scalar_one() == 2
            assert db.execute(text("SELECT count(*) FROM course WHERE NOT archived AND NOT join_approval "
                                   "AND NOT leave_approval AND revision=1")).scalar_one() == 2
        columns = {col["name"]: col for col in inspect(engine).get_columns("app_user")}
        assert columns["must_change_password"]["default"] == "false"
        assert columns["revision"]["default"] == "1"
        tables = set(inspect(engine).get_table_names())
        assert {"major", "account_invitation", "enrollment_request", "command_receipt", "core_audit_event"} <= tables


def test_b1_conflicting_primary_teachers_stop_before_schema_changes():
    with old_database() as (engine, env, command):
        ids = old_rows(engine)
        subprocess.run([*command, "e24a0c0a0001"], env=env, check=True, capture_output=True)
        with engine.begin() as db:
            db.execute(text("INSERT INTO course_staff(id,school_id,course_id,user_id,is_primary) "
                            "VALUES (:id,:school,:course,:user,true)"),
                       {"id":uuid4(),"school":ids["school"],"course":ids["one"],"user":ids["student"]})
        result = subprocess.run([*command, "head"], env=env, capture_output=True, text=True)
        assert result.returncode != 0
        assert "Multiple legacy primary teachers; data preserved" in result.stderr
        with engine.connect() as db:
            assert db.execute(text("SELECT count(*) FROM course_staff")).scalar_one() == 2
            assert db.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "e24a0c0a0001"
        assert "major" not in inspect(engine).get_table_names()


def test_b1_migration_enforces_major_tenant_and_nullable_parent_constraint():
    with old_database() as (engine, env, command):
        ids = old_rows(engine)
        subprocess.run([*command, "head"], env=env, check=True, capture_output=True)
        major_id, other_college = uuid4(), uuid4()
        with engine.begin() as db:
            db.execute(text("INSERT INTO college(id,school_id,code,name) VALUES (:id,:school,'second','Second')"),
                       {"id":other_college,"school":ids["school"]})
            db.execute(text("INSERT INTO major(id,school_id,college_id,code,name) VALUES (:id,:school,:college,'major','Major')"),
                       {"id":major_id,"school":ids["school"],"college":ids["college"]})
        for college in (None, other_college):
            with pytest.raises(IntegrityError):
                with engine.begin() as db:
                    db.execute(text("UPDATE app_user SET major_id=:major,college_id=:college WHERE id=:id"),
                               {"major":major_id,"college":college,"id":ids["student"]})
        with pytest.raises(IntegrityError):
            with engine.begin() as db:
                db.execute(text("INSERT INTO course_staff(id,school_id,course_id,user_id,is_primary) "
                                "VALUES (:id,:school,:course,:user,true)"),
                           {"id":uuid4(),"school":ids["school"],"course":ids["one"],"user":ids["student"]})


def test_public_routers_export_typed_business_and_keep_learning_unpublished(client):
    schema = client.get("/api/v1/openapi.json").json()
    assert {"/api/v1/admin/accounts", "/api/v1/imports/commit", "/api/v1/catalogs",
            "/api/v1/catalogs/{catalog_id}/teacher-options",
            "/api/v1/courses/{course_id}/transfer", "/api/v1/auth/change-password"} <= set(schema["paths"])
    assert not any("tutoring-status" in path or "training-records" in path for path in schema["paths"])
    assert client.get("/api/v1/learning/training-records").status_code == 404


def test_catalog_teacher_picker_public_query_bounds_tenant_and_minimal_fields(client, auth, db):
    from app.domains.core.models import CourseCatalog
    from app.seed import fixture_id

    owner = auth()
    catalog_id = client.get(f"/api/v1/courses/{fixture_id('course-general')}", headers=owner).json()["catalog_id"]
    path = f"/api/v1/catalogs/{catalog_id}/teacher-options"
    response = client.get(path, headers=owner, params={"q": "teacher_eng", "limit": 1})
    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert set(response.json()["data"][0]) == {"id", "username", "display_name", "college_id"}
    assert client.get(path, headers=owner, params={"q": "teacher%"}).json()["count"] == 0
    assert client.get(path, headers=owner, params={"q": "t"}).status_code == 422
    assert client.get(path, headers=owner, params={"q": "teacher", "limit": 21}).status_code == 422
    assert client.get(path, headers=auth("student"), params={"q": "teacher"}).status_code == 403
    assert client.get(path, headers=auth("teacher_b", "demo-b"), params={"q": "teacher"}).status_code == 404
    catalog = db.get(CourseCatalog, UUID(catalog_id))
    catalog.archived = True
    db.add(catalog)
    db.commit()
    assert client.get(path, headers=owner, params={"q": "teacher"}).status_code == 409


def test_invalid_secret_input_is_not_echoed_by_public_validation_handler(client, auth):
    secret = "s3cr3t"
    response = client.post("/api/v1/auth/change-password", headers=auth(),
                           json={"old_password":"synthetic-current","new_password":secret})
    assert response.status_code == 422
    assert secret not in response.text
    assert all("input" not in error and "ctx" not in error for error in response.json()["detail"])


def test_health_rejects_an_old_schema_instead_of_reusing_an_unready_service():
    with old_database() as (_engine, env, _command):
        code = "from app.main import app; from fastapi.testclient import TestClient; " \
               "response=TestClient(app).get('/api/v1/health'); " \
               "assert response.status_code==503, response.status_code"
        subprocess.run([sys.executable,"-c",code], cwd=Path(__file__).resolve().parents[1],
                       env=env, check=True, capture_output=True)
