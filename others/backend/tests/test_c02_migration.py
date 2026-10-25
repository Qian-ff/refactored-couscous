"""Real disposable PostgreSQL clones: preserve B rows, repeat upgrade, and reverse only the clone."""
import hashlib
import json
import subprocess

from sqlalchemy import inspect, text

from test_a0_migration import old_database, old_rows


def snapshot(engine):
    result = {}
    names = sorted(name for name in inspect(engine).get_table_names()
                   if name != "alembic_version" and not name.startswith("content_"))
    with engine.connect() as connection:
        for name in names:
            quoted = connection.dialect.identifier_preparer.quote(name)
            rows = connection.execute(text(f"SELECT to_jsonb(t)::text FROM {quoted} t ORDER BY id")).scalars().all()
            result[name] = {"count": len(rows), "hash": hashlib.sha256(json.dumps(rows).encode()).hexdigest()}
    return result


def upgrade(command, env, revision):
    subprocess.run([*command, revision], env=env, check=True, capture_output=True)


def test_old_b1_rows_survive_c02_upgrade_repeat_and_clone_downgrade():
    with old_database() as (engine, env, command):
        old_rows(engine)
        upgrade(command, env, "b1c0e0a00001")
        before = snapshot(engine)
        upgrade(command, env, "head")
        upgrade(command, env, "head")
        assert snapshot(engine) == before
        assert len([name for name in inspect(engine).get_table_names() if name.startswith("content_")]) == 8
        # This URL is a fresh safelab_migration_* clone allocated by old_database(), never the demo DB.
        assert engine.url.database.startswith("safelab_migration_")
        subprocess.run([*command[:-1], "downgrade", "b1c0e0a00001"], env=env, check=True, capture_output=True)
        assert snapshot(engine) == before
        assert not any(name.startswith("content_") for name in inspect(engine).get_table_names())
        upgrade(command, env, "head")
        assert snapshot(engine) == before


def test_empty_clone_can_reach_c02_head():
    with old_database() as (engine, env, command):
        upgrade(command, env, "head")
        with engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "c02d0c00001"
            assert connection.execute(text("SELECT count(*) FROM content_material_version")).scalar_one() == 0
