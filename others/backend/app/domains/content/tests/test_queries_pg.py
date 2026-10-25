"""Authorization/count/cursor integration cases, pending A's real C-02 migration."""
from uuid import UUID
import hashlib

import pytest
from fastapi import HTTPException
from sqlmodel import select

from app.seed import fixture_id
from app.domains.content import queries
from app.domains.content.access import descriptor
from app.domains.content.models import Library, MaterialVersion, SourceChunk
from app.domains.content.schemas import LibraryCreate, TextMaterialCreate
from app.domains.content.services import create_library, create_text_version
from app.domains.content.tests.test_services_pg import completed_fixture, identity, school_library
from app.domains.core.policy import resource_access


def test_target_bindings_and_material_revision_do_not_blend(db):
    from app.domains.content.schemas import MaterialChange, ReviewDecision, ReviewSubmit, RevisionInput
    from app.domains.content.services import change_material, decide_review, publish_review, submit_review, warnings_hash
    admin = identity(db, "admin", "administrator")
    teacher = identity(db, "teacher", "teacher")
    student = identity(db, "student", "student")
    first = school_library(db, admin)
    second = UUID(create_library(db, admin, LibraryCreate(scope="school", parent_id=admin.user.school_id,
        title="Second target", audience="all"), "c02-target-second")["library_id"])
    created = create_text_version(db, teacher, TextMaterialCreate(library_id=first, title="Fixed version", text="Original"),
                                  "c02-binding-text", 10 * 1024**3)
    version = completed_fixture(db, created)
    reviews = [submit_review(db, teacher, ReviewSubmit(version_id=version.id, target_library_id=target,
        authorization_statement="Synthetic original authorized for target"), "c02-binding-review-" + str(index))
        for index, target in enumerate((first, second))]
    decide_review(db, admin, UUID(reviews[0]["review_id"]), ReviewDecision(revision=1, decision="approved",
        warning_hash=warnings_hash(version), warnings_acknowledged=True, original_authorized=True), "c02-binding-approve")
    publication = publish_review(db, admin, UUID(reviews[0]["review_id"]), RevisionInput(revision=2), "c02-binding-publish")
    change_material(db, teacher, UUID(created["material_id"]), MaterialChange(revision=1, title="Updated title"),
                    "c02-binding-rename")
    current_a = queries.version_view(db, admin, version.id, first)
    current_b = queries.version_view(db, admin, version.id, second)
    assert current_a.material_revision == 2 and current_a.version_no == 1
    assert current_a.binding.review.state == "approved"
    assert str(current_a.binding.active_publication.id) == publication["publication_id"]
    assert current_b.binding.target_library_id == second
    assert current_b.binding.active_publication is None
    assert current_b.binding.review.state == "submitted" and current_b.binding.review.can_decide
    assert current_b.binding.review.warning_hash == warnings_hash(version)
    safe = queries.version_view(db, student, version.id, first)
    assert safe.material_revision is None and safe.source_metadata is None and safe.binding.review is None
    assert safe.actions.preview and safe.actions.download
    assert not safe.actions.edit_material and not safe.actions.retire_material and not safe.actions.submit_review
    with pytest.raises(HTTPException):
        queries.version_view(db, student, version.id, second)


def test_submit_right_does_not_grant_library_management(db):
    admin = identity(db, "admin", "administrator")
    teacher = identity(db, "teacher", "teacher")
    library_id = school_library(db, admin)
    assert library_id in {row.id for row in queries.targets(db, teacher, "Synthetic C02", 0, 100)}
    create_text_version(db, teacher, TextMaterialCreate(library_id=library_id, title="Owned draft", text="Original"),
                        "c02-submit-only-projection", 10 * 1024**3)
    # A teacher may legitimately manage another course library already created by an HTTP test.
    row = next(row for row in queries.libraries(db, teacher, "Synthetic C02", 0, 100).items if row.id == library_id)
    assert row.can_submit and not row.can_manage and not row.can_review


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
