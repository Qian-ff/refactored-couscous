"""Upgrade actual A1 PostgreSQL schemas, without touching the demonstration database."""
from contextlib import contextmanager
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

from conftest import base_url
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[3]


@contextmanager
def old_database():
    name = "safelab_migration_" + uuid4().hex[:12]
    assert name.startswith("safelab_migration_") and len(name) == 30
    admin = create_engine(base_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    url = base_url.set(database=name, drivername="postgresql+psycopg")
    engine = create_engine(url)
    env = dict(os.environ, DATABASE_URL=url.render_as_string(hide_password=False), APP_ENV="test")
    command = [sys.executable, "-m", "alembic", "-c", str(ROOT / "others/backend/alembic.ini"), "upgrade"]
    try:
        subprocess.run([*command, "c7d7105add2f"], env=env, check=True, capture_output=True)
        yield engine, env, command
    finally:
        engine.dispose()
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE "{name}"'))
        admin.dispose()


def old_rows(engine, *, mixed=False):
    ids = {name: uuid4() for name in ("school", "college", "teacher", "student", "one", "two", "staff", "enroll")}
    with engine.begin() as db:
        db.execute(text("INSERT INTO school VALUES (:id,'migration-fixture','Fixture')"), {"id": ids["school"]})
        db.execute(text("INSERT INTO college VALUES (:id,:school,'fixture','Fixture')"),
                   {"id": ids["college"], "school": ids["school"]})
        for who in ("teacher", "student"):
            db.execute(text("""INSERT INTO app_user (id,school_id,college_id,username,display_name,hashed_password,is_active)
                VALUES (:id,:school,:college,:who,:who,'fixture-not-a-login',true)"""),
                {"id": ids[who], "school": ids["school"], "college": ids["college"], "who": who})
        for code in ("one", "two"):
            db.execute(text("""INSERT INTO course VALUES (:id,:school,:college,:code,'Identical title',now())"""),
                {"id": ids[code], "school": ids["school"], "college": ids["college"], "code": code})
        db.execute(text("INSERT INTO course_staff VALUES (:id,:school,:course,:user,true)"),
                   {"id": ids["staff"], "school": ids["school"], "course": ids["one"], "user": ids["teacher"]})
        db.execute(text("INSERT INTO enrollment VALUES (:id,:school,:course,:user,'active')"),
                   {"id": ids["enroll"], "school": ids["school"], "course": ids["one"], "user": ids["student"]})
        if mixed:
            for role in ("student", "teacher"):
                db.execute(text("INSERT INTO role_grant VALUES (:id,:user,:school,:role,NULL)"),
                    {"id": uuid4(), "user": ids["student"], "school": ids["school"], "role": role})
    return ids


def test_a1_upgrade_preserves_relationships_and_distinguishes_identical_titles():
    with old_database() as (engine, env, command):
        ids = old_rows(engine)
        subprocess.run([*command, "head"], env=env, check=True, capture_output=True)
        with engine.connect() as db:
            rows = db.execute(text("SELECT id,catalog_id,title FROM course ORDER BY code")).all()
            assert {row.id for row in rows} == {ids["one"], ids["two"]}
            assert len({row.catalog_id for row in rows}) == 2
            assert all(row.id != row.catalog_id for row in rows)
            assert db.execute(text("SELECT id FROM course_staff")).scalar_one() == ids["staff"]
            assert db.execute(text("SELECT id FROM enrollment")).scalar_one() == ids["enroll"]
            assert db.execute(text("SELECT owner_id FROM course_catalog WHERE code='one'")).scalar_one() == ids["teacher"]


def test_conflicting_legacy_account_stops_upgrade_without_deleting_data():
    with old_database() as (engine, env, command):
        ids = old_rows(engine, mixed=True)
        result = subprocess.run([*command, "head"], env=env, capture_output=True, text=True)
        assert result.returncode != 0
        assert "Student role conflicts; data preserved" in result.stderr
        with engine.connect() as db:
            assert db.execute(text("SELECT count(*) FROM role_grant WHERE user_id=:id"), {"id": ids["student"]}).scalar() == 2
            assert db.execute(text("SELECT version_num FROM alembic_version")).scalar() == "c7d7105add2f"
