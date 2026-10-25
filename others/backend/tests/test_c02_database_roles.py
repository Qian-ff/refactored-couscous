"""Real runtime-role protection; never run these assertions with migration credentials."""
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError


def test_api_role_cannot_own_or_assume_table_owners(db):
    flags = db.execute(text("SELECT rolsuper,rolcreaterole,rolcreatedb,rolbypassrls FROM pg_roles WHERE rolname=current_user")).one()
    assert not any(flags)
    owners = db.execute(text("SELECT DISTINCT tableowner FROM pg_tables WHERE schemaname='public'")).scalars().all()
    assert owners
    for owner in owners:
        assert not db.execute(text("SELECT pg_has_role(current_user,:owner,'MEMBER')"), {"owner": owner}).scalar()


@pytest.mark.parametrize("statement", [
    "ALTER TABLE content_material_version DISABLE TRIGGER ALL",
    "TRUNCATE content_source_chunk",
    "CREATE TABLE c02_forbidden_owner_bypass(id integer)",
])
def test_runtime_cannot_disable_or_bypass_history_guards(db, statement):
    with pytest.raises(DBAPIError):
        with db.begin_nested():
            db.execute(text(statement))
