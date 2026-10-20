"""Real local PostgreSQL tests; each case rolls its own rows back."""
import os
import subprocess
import sys
from pathlib import Path

import pytest
from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[3]
config = dotenv_values(ROOT / ".env")
base_url = make_url(os.environ.get("DATABASE_URL") or config["DATABASE_URL"])
if base_url.host not in ("127.0.0.1", "localhost"):
    raise RuntimeError("A1 tests require a local PostgreSQL host")
test_url = base_url.set(database="safelab_a1_test", drivername="postgresql+psycopg")
os.environ["DATABASE_URL"] = test_url.render_as_string(hide_password=False)
os.environ["APP_ENV"] = "test"

from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session  # noqa: E402

from app.core.db import engine, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import seed  # noqa: E402

TEST_PASSWORD = "A1-synthetic-only-test-password"


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    admin = create_engine(base_url.set(database="postgres", drivername="postgresql+psycopg"), isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        if not connection.execute(text("SELECT 1 FROM pg_database WHERE datname = 'safelab_a1_test'")).scalar():
            connection.execute(text('CREATE DATABASE "safelab_a1_test"'))
    admin.dispose()
    subprocess.run([sys.executable, "-m", "alembic", "-c", str(ROOT / "others/backend/alembic.ini"), "upgrade", "head"], check=True)
    yield
    engine.dispose()


@pytest.fixture
def db(migrated_database):
    with engine.connect() as connection:
        outer = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            seed(session, TEST_PASSWORD)
            yield session
        outer.rollback()


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def auth(client):
    def login(username="teacher", school="demo-a"):
        response = client.post("/api/v1/auth/login", json={"school_code": school, "username": username, "password": TEST_PASSWORD})
        assert response.status_code == 200, response.text
        return {"Authorization": "Bearer " + response.json()["access_token"]}
    return login
