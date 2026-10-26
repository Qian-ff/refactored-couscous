"""Explicit C02 local management entry; never imported by the API runtime."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import secrets
import sys

from alembic import command
from alembic.config import Config
from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "others/backend"))


def migrate(owner_url: str, revision: str = "head"):
    engine = create_engine(owner_url)
    config = Config(str(ROOT / "others/backend/alembic.ini"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, revision)
    engine.dispose()


def grant_runtime(owner_url: str, role: str):
    if not any(role.startswith(prefix) and role[len(prefix):].isalnum() for prefix in ("c02_run_", "c1_run_")):
        raise ValueError("Unexpected C02 runtime role")
    engine = create_engine(owner_url)
    with engine.begin() as connection:
        connection.exec_driver_sql("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
        connection.exec_driver_sql(f'GRANT USAGE ON SCHEMA public TO "{role}"')
        connection.exec_driver_sql(f'GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO "{role}"')
        connection.exec_driver_sql(f'GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO "{role}"')
        connection.exec_driver_sql(f'GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO "{role}"')
    engine.dispose()


def prepare_test(primary: Path, destination: Path):
    if destination.parent.resolve() != (ROOT / "others/runtime/c02-public").resolve():
        raise RuntimeError("Management configuration must stay in this candidate's ignored directory")
    owner = make_url(dotenv_values(primary / ".env")["DATABASE_URL"])
    if owner.host not in {"127.0.0.1", "localhost"}:
        raise RuntimeError("C02 validation only manages local PostgreSQL")
    owner = owner.set(drivername="postgresql+psycopg", database="safelab_c02_test")
    if destination.exists():
        existing = json.loads(destination.read_text())
        if make_url(existing["owner_url"]) != owner:
            raise RuntimeError("Existing management configuration belongs to another database")
        return existing
    role, password = "c02_run_" + secrets.token_hex(6), secrets.token_urlsafe(32)
    engine = create_engine(owner.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with engine.connect() as connection:
        if not connection.execute(text("SELECT 1 FROM pg_database WHERE datname='safelab_c02_test'")).scalar():
            connection.exec_driver_sql('CREATE DATABASE "safelab_c02_test"')
        # Random internal identifiers/passwords contain no SQL metacharacters.
        connection.exec_driver_sql(f'CREATE ROLE "{role}" LOGIN PASSWORD \'{password}\' '
                                   'NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS')
        connection.exec_driver_sql(f'GRANT CONNECT ON DATABASE safelab_c02_test TO "{role}"')
    engine.dispose()
    configuration = {"owner_url": owner.render_as_string(hide_password=False), "runtime_role": role,
                     "runtime_url": owner.set(username=role, password=password).render_as_string(hide_password=False)}
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8") as handle:
        json.dump(configuration, handle)
    os.chmod(destination, 0o600)
    return configuration


def prepare_c1_test(primary: Path, destination: Path):
    """One fixed test profile, using the existing separate local management credentials."""
    if destination.resolve() != (ROOT / "others/runtime/c1-public/database-admin.json").resolve():
        raise RuntimeError("C1 management configuration must stay in its fixed ignored directory")
    management = json.loads((primary / "others/runtime/content-parser/database-admin.json").read_text())
    owner = make_url(management["owner_url"])
    business = make_url(dotenv_values(primary / ".env")["DATABASE_URL"])
    if (owner.host not in {"127.0.0.1", "localhost"} or owner.database != "safelab"
            or (owner.host, owner.port, owner.database) != (business.host, business.port, business.database)):
        raise RuntimeError("C1 profile requires the existing project's local PostgreSQL management entry")
    owner = owner.set(drivername="postgresql+psycopg", database="safelab_c1_test")
    if destination.exists():
        existing = json.loads(destination.read_text())
        runtime = make_url(existing["runtime_url"])
        if (make_url(existing["owner_url"]) != owner or runtime.database != "safelab_c1_test"
                or runtime.username != existing["runtime_role"] or not runtime.username.startswith("c1_run_")):
            raise RuntimeError("Existing C1 management configuration belongs to another profile")
        return existing
    role, password = "c1_run_" + secrets.token_hex(6), secrets.token_urlsafe(32)
    engine = create_engine(owner.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with engine.connect() as connection:
        if not connection.execute(text("SELECT 1 FROM pg_database WHERE datname='safelab_c1_test'")).scalar():
            connection.exec_driver_sql('CREATE DATABASE "safelab_c1_test"')
        connection.exec_driver_sql(f'CREATE ROLE "{role}" LOGIN PASSWORD \'{password}\' '
                                   'NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS')
        connection.exec_driver_sql(f'GRANT CONNECT ON DATABASE safelab_c1_test TO "{role}"')
    engine.dispose()
    data = {"owner_url": owner.render_as_string(hide_password=False), "runtime_role": role,
            "runtime_url": owner.set(username=role, password=password).render_as_string(hide_password=False),
            "synthetic_password": secrets.token_urlsafe(24), "profile": "c1-test"}
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8") as handle:
        json.dump(data, handle)
    destination.chmod(0o600)
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare-test", "prepare-c1-test", "upgrade"))
    parser.add_argument("--admin-config", required=True, type=Path)
    parser.add_argument("--primary", type=Path)
    args = parser.parse_args()
    if args.action in {"prepare-test", "prepare-c1-test"}:
        if args.primary is None:
            parser.error("prepare-test requires --primary")
        data = (prepare_c1_test if args.action == "prepare-c1-test" else prepare_test)(args.primary, args.admin_config)
    else:
        data = json.loads(args.admin_config.read_text())
    os.environ["DATABASE_URL"] = data["runtime_url"]
    os.environ.setdefault("SECRET_KEY", secrets.token_urlsafe(32))
    os.environ["APP_ENV"] = "test"
    migrate(data["owner_url"])
    grant_runtime(data["owner_url"], data["runtime_role"])
    if args.action == "prepare-c1-test":
        runtime = args.admin_config.parent
        storage = (runtime / "materials").resolve()
        storage.mkdir(mode=0o700, exist_ok=True)
        content_file = runtime / "content-runtime.json"
        content_file.write_text(json.dumps({"storage_root": str(storage),
            "parser_client": str((runtime / "parser-client.json").resolve())}), encoding="utf-8")
        api_file = runtime / "api-runtime.json"
        if not api_file.exists():
            api_file.write_text(json.dumps({"database_url": data["runtime_url"], "secret_key": secrets.token_urlsafe(48),
                "content_runtime": str(content_file.resolve()), "synthetic_password": data["synthetic_password"]}), encoding="utf-8")
        for path in (content_file, api_file):
            path.chmod(0o600)
    if args.action == "prepare-test":
        if "synthetic_password" not in data:
            data["synthetic_password"] = secrets.token_urlsafe(24)
            args.admin_config.write_text(json.dumps(data), encoding="utf-8")
        runtime = args.admin_config.parent
        storage = (runtime / "materials").resolve()
        storage.mkdir(mode=0o700, exist_ok=True)
        content_file = runtime / "content-runtime.json"
        content_file.write_text(json.dumps({"storage_root": str(storage),
            "parser_client": str((runtime / "parser-client.json").resolve())}), encoding="utf-8")
        api_file = runtime / "api-runtime.json"
        if not api_file.exists():
            api_file.write_text(json.dumps({"database_url": data["runtime_url"], "secret_key": secrets.token_urlsafe(48),
                "content_runtime": str(content_file.resolve()), "synthetic_password": data["synthetic_password"]}), encoding="utf-8")
        for path in (args.admin_config, content_file, api_file):
            path.chmod(0o600)
    print(json.dumps({"database": make_url(data["runtime_url"]).database, "runtime_role": data["runtime_role"],
                      "migration": "c1d0c000001" if data.get("profile") == "c1-test" else "c02d0c00001",
                      "owner_configuration_separate": True}))


if __name__ == "__main__":
    main()
