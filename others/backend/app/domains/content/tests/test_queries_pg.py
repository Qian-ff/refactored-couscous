"""Authorization/count/cursor integration cases, pending A's real C-02 migration."""
from uuid import UUID
import hashlib

from sqlmodel import select

from app.seed import fixture_id
from app.domains.content import queries
from app.domains.content.access import descriptor
from app.domains.content.models import Library, MaterialVersion, SourceChunk
from app.domains.content.schemas import LibraryCreate, TextMaterialCreate
from app.domains.content.services import create_library, create_text_version
from app.domains.content.tests.test_services_pg import completed_fixture, identity, school_library
from app.domains.core.policy import resource_access


def test_submit_sql_matches_b_capability_for_all_seed_roles(db):
    platform = identity(db, "platform", "administrator")
    specifications = [("platform_public", None), ("school", fixture_id("school-a")),
                      ("school", fixture_id("school-b")), ("college", fixture_id("a-chem")),
                      ("college", fixture_id("a-eng")), ("catalog", fixture_id("catalog-general")),
                      ("course", fixture_id("course-general")), ("course", fixture_id("course-electrical"))]
    for index, (scope, parent) in enumerate(specifications):
        create_library(db, platform, LibraryCreate(scope=scope, parent_id=parent, title=f"C02-{index}"),
                       f"c02-scope-create-{index}")
    libraries = db.exec(select(Library)).all()
    for username, role in (("platform", "administrator"), ("admin", "administrator"), ("college", "administrator"),
                           ("teacher", "teacher"), ("teacher_eng", "teacher"), ("student", "student"),
                           ("admin_b", "administrator"), ("teacher_b", "teacher")):
        actor = identity(db, username, role)
        expected = {row.id for row in libraries if row.active and resource_access(db, actor, descriptor(row)).submit}
        actual = {row.id for row in queries.targets(db, actor, "", 0, 100)}
        assert actual == expected, username


def test_empty_school_library_visible_as_target_but_not_reading_list_for_s_only(db):
    admin = identity(db, "admin", "administrator")
    teacher = identity(db, "teacher", "teacher")
    library_id = school_library(db, admin)
    assert library_id in {row.id for row in queries.targets(db, teacher, "", 0, 100)}
    assert library_id not in {row.id for row in queries.libraries(db, teacher, "", 0, 100).items}
    assert library_id in {row.id for row in queries.libraries(db, admin, "", 0, 100).items}


def test_chinese_chunks_page_by_response_budget_without_losing_locator(db):
    admin = identity(db, "admin", "administrator")
    teacher = identity(db, "teacher", "teacher")
    library_id = school_library(db, admin)
    created = create_text_version(db, teacher, TextMaterialCreate(library_id=library_id, title="Synthetic", text="原文"),
                                  "c02-chunks-create", 10 * 1024**3)
    # Fixture seeds chunks before freezing the version, as the production snapshot transaction does.
    version = db.get(MaterialVersion, UUID(created["version_id"]))
    version.extraction_state = "running"
    db.add(version)
    db.flush()
    for ordinal in range(1, 101):
        db.add(SourceChunk(material_version_id=version.id, ordinal=ordinal,
                           locator={"kind": "paragraph", "position": 1, "part": ordinal},
                           text="安" * 8192, text_hash=hashlib.sha256(("安" * 8192).encode()).hexdigest()))
    db.flush()
    completed_fixture(db, created)
    first = queries.chunks(db, teacher, version.id, 0, 100)
    assert 0 < len(first.items) < 100
    assert first.next_ordinal == first.items[-1].ordinal
    second = queries.chunks(db, teacher, version.id, first.next_ordinal, 100)
    assert second.items[0].ordinal == first.next_ordinal + 1
    assert second.items[0].locator["position"] == 1
    assert len(first.model_dump_json().encode()) <= 1024 * 1024
