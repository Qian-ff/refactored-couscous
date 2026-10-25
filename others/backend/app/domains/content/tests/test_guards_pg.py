"""Real PG guards. A must install c-02-guards.sql through its migration before these run."""
import hashlib
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.domains.content.models import MaterialVersion, SourceChunk
from app.domains.content.schemas import TextMaterialCreate
from app.domains.content.services import create_text_version
from app.domains.content.tests.test_services_pg import completed_fixture, identity, school_library


def rejected(db, sql, **values):
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.execute(text(sql), values)


def fixture(db):
    admin = identity(db, "admin", "administrator")
    teacher = identity(db, "teacher", "teacher")
    library = school_library(db, admin)
    created = create_text_version(db, teacher, TextMaterialCreate(
        library_id=library, title="Guard fixture", text="Trusted original"), "c02-guard-create", 10 * 1024**3)
    return library, created


def test_library_scope_and_version_input_are_immutable(db):
    library, created = fixture(db)
    rejected(db, "UPDATE content_library SET audience='staff' WHERE id=:id", id=library)
    rejected(db, "UPDATE content_material_version SET input_text='replaced' WHERE id=:id",
             id=UUID(created["version_id"]))
    rejected(db, "DELETE FROM content_material_version WHERE id=:id", id=UUID(created["version_id"]))


def test_success_snapshot_and_chunks_cannot_be_changed_or_extended(db):
    _library, created = fixture(db)
    version = db.get(MaterialVersion, UUID(created["version_id"]))
    version.extraction_state = "running"
    db.add(version)
    db.flush()
    chunk = SourceChunk(material_version_id=version.id, ordinal=1,
                        locator={"kind": "paragraph", "position": 1, "part": 1}, text="Original",
                        text_hash=hashlib.sha256(b"Original").hexdigest())
    db.add(chunk)
    db.flush()
    completed_fixture(db, created)
    rejected(db, "UPDATE content_material_version SET extraction_state='running' WHERE id=:id", id=version.id)
    rejected(db, "UPDATE content_source_chunk SET text='replacement' WHERE id=:id", id=chunk.id)
    rejected(db, "DELETE FROM content_source_chunk WHERE id=:id", id=chunk.id)
    rejected(db, "INSERT INTO content_source_chunk(id,material_version_id,ordinal,locator,text,text_hash) "
             "SELECT gen_random_uuid(),material_version_id,2,locator,text,text_hash FROM content_source_chunk WHERE id=:id",
             id=chunk.id)


def test_job_session_owner_and_library_binding_cannot_be_reassigned(db):
    _library, created = fixture(db)
    other = identity(db, "student", "student")
    rejected(db, "UPDATE content_job SET login_session_id=:login WHERE id=:id",
             login=other.login.id, id=UUID(created["job_id"]))
    rejected(db, "UPDATE content_job SET owner_id=:owner WHERE id=:id",
             owner=other.user.id, id=UUID(created["job_id"]))
