"""C1 public schema only, on the explicitly allocated local non-owner test database."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.domains.core.models import User
from app.domains.content.models import Library, Material, MaterialVersion
from app.domains.content.questions.models import (Question, QuestionDraft, QuestionVersion, QuestionSource, QuestionPublication, QuestionReview)
from app.domains.content.lessons.models import (SceneAsset, Lesson, LessonDraft, LessonVersion,
    LessonSource, LessonQuestion, LessonQuestionOrigin, LessonDraftQuestionOrigin)
from app.domains.content.questions.tests.unit.test_schema import sample_question
from app.seed import seed

ROOT = Path(__file__).resolve().parents[3]
HEAD = "c1d0c000001"
OLD = "c02d0c00001"


def snapshots(engine):
    result = {}
    with engine.connect() as connection:
        for name in sorted(inspect(engine).get_table_names()):
            if name == "alembic_version":
                continue
            rows = connection.execute(text(f'SELECT to_jsonb(t)::text FROM "{name}" t ORDER BY to_jsonb(t)::text')).scalars().all()
            result[name] = {"count": len(rows), "sha256": hashlib.sha256(json.dumps(rows).encode()).hexdigest()}
    return result


def test_c1_dedicated_schema_migration_and_committed_integrity(migrated_database):
    configuration = Path(os.environ["LABCONNECT_C02_TEST_ADMIN_CONFIG"])
    assert configuration.resolve() == (ROOT / "others/runtime/c1-public/database-admin.json").resolve()
    management = json.loads(configuration.read_text())
    owner, runtime = create_engine(management["owner_url"]), create_engine(management["runtime_url"])
    assert owner.url.database == runtime.url.database == "safelab_c1_test"
    assert owner.url.host in {"127.0.0.1", "localhost"}
    spec = importlib.util.spec_from_file_location("c1_management", ROOT / "others/deploy/content/database.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report = {"database": "safelab_c1_test", "migration": HEAD, "main_database_touched": False}

    def move(revision, *, down=False):
        cfg = Config(str(ROOT / "others/backend/alembic.ini"))
        with owner.begin() as connection:
            cfg.attributes["connection"] = connection
            (command.downgrade if down else command.upgrade)(cfg, revision)
        module.grant_runtime(management["owner_url"], management["runtime_role"])

    def denied(sql, params):
        # Each rejection is a new real transaction, outside any fixture savepoint.
        with pytest.raises(IntegrityError):
            with runtime.begin() as connection:
                connection.execute(text(sql), params)

    def empty_dedicated_schema():
        # B1 deliberately has no history-erasing downgrade. Reset only this allocated test schema.
        with owner.begin() as connection:
            assert connection.execute(text("SELECT current_database()")).scalar_one() == "safelab_c1_test"
            connection.exec_driver_sql("DROP SCHEMA public CASCADE")
            connection.exec_driver_sql("CREATE SCHEMA public")

    try:
        empty_dedicated_schema()
        move(HEAD)
        assert len([n for n in inspect(owner).get_table_names() if n.startswith("content_")]) == 31
        report["empty_to_head"] = True
        move(OLD, down=True)
        with Session(runtime) as db:
            seed(db, management["synthetic_password"])
            admin = db.exec(select(User).where(User.username == "admin")).one()
            user_id, school_id = admin.id, admin.school_id
            library = Library(scope="school", school_id=school_id, audience="all", title="T1 legacy synthetic", creator_id=user_id)
            db.add(library)
            db.flush()
            material = Material(library_id=library.id, creator_id=user_id, title="T1 legacy material")
            db.add(material)
            db.flush()
            version = MaterialVersion(material_id=material.id, version_no=1, input_kind="text",
                input_text="T1 legacy text", content_hash="0" * 64, created_by=user_id)
            db.add(version)
            db.commit()
            library_id, material_version_id = library.id, version.id
        before = snapshots(owner)
        move(HEAD)
        move(HEAD)
        after = snapshots(owner)
        assert all(after[name] == value for name, value in before.items())
        assert len(after) - len(before) == 23
        move(OLD, down=True)
        assert snapshots(owner) == before
        move(HEAD)
        assert all(snapshots(owner)[name] == value for name, value in before.items())
        report.update(old_to_head_repeat_downgrade_upgrade=True, preserved_old_tables=before)
        with runtime.connect() as connection:
            flags = connection.execute(text("""SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls
                FROM pg_roles WHERE rolname=current_user""")).one()
            assert not any(flags)
            assert not connection.execute(text("SELECT pg_has_role(current_user,:owner,'MEMBER')"),
                                         {"owner": owner.url.username}).scalar_one()
            assert not connection.execute(text("SELECT has_schema_privilege(current_user,'public','CREATE')")).scalar_one()
            assert not connection.execute(text("""SELECT EXISTS(SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE n.nspname='public' AND pg_get_userbyid(c.relowner)=current_user)""")).scalar_one()
        report["runtime_nonowner_no_admin_or_schema_create"] = True

        # Commit actual parent/child creation, including a savepoint, then test a fresh connection.
        with Session(runtime) as db:
            question = Question(library_id=library_id, creator_id=user_id)
            asset = SceneAsset(library_id=library_id, creator_id=user_id, svg="<svg/>", content_hash="0" * 64,
                               provenance={}, view_box=[0, 0, 100, 100])
            lesson = Lesson(library_id=library_id, creator_id=user_id)
            db.add_all([question, asset, lesson])
            db.flush()
            db.add(QuestionDraft(question_id=question.id, payload=sample_question(), provenance={}, duplicate_hash="1" * 64, updated_by=user_id))
            with db.begin_nested():
                qv = QuestionVersion(question_id=question.id, version_no=1, draft_revision=1,
                    payload=sample_question(), provenance={}, payload_hash="2" * 64, created_by=user_id)
                lv = LessonVersion(lesson_id=lesson.id, version_no=1, draft_revision=1, content={},
                    scene_asset_id=asset.id, payload_hash="3" * 64, created_by=user_id)
                db.add_all([qv, lv])
                db.flush()
                db.add(QuestionSource(question_version_id=qv.id, material_version_id=material_version_id, locator={}))
                db.add_all([LessonSource(lesson_version_id=lv.id, activity_id="a", material_version_id=material_version_id, locator={}),
                    LessonQuestion(lesson_version_id=lv.id, activity_id="a", question_version_id=qv.id),
                    LessonQuestionOrigin(lesson_version_id=lv.id, activity_id="a", question_version_id=qv.id)])
                db.flush()
            db.add(LessonDraft(lesson_id=lesson.id, content={}, scene_asset_id=asset.id, updated_by=user_id))
            db.flush()
            db.add(LessonDraftQuestionOrigin(lesson_id=lesson.id, activity_id="a", question_version_id=qv.id))
            db.commit()
            qid, lid, qvid, lvid, asset_id = question.id, lesson.id, qv.id, lv.id, asset.id
        for table, column, value in [("content_question_version", "id", qvid), ("content_lesson_version", "id", lvid),
                                      ("content_scene_asset", "id", asset_id)]:
            denied(f'UPDATE {table} SET retained_bytes=retained_bytes+1 WHERE {column}=:id', {"id": value})
            denied(f'DELETE FROM {table} WHERE {column}=:id', {"id": value})
        for parent, child, key, version_id in [
            ("content_question_version", "content_question_source", "question_version_id", qvid),
            ("content_lesson_version", "content_lesson_source", "lesson_version_id", lvid),
        ]:
            with runtime.begin() as connection:
                before_xmin = connection.execute(text(f'SELECT xmin::text FROM {parent} WHERE id=:id'), {"id": version_id}).scalar_one()
                with pytest.raises(IntegrityError) as no_op:
                    with connection.begin_nested():
                        connection.execute(text(f'UPDATE {parent} SET payload_hash=payload_hash WHERE id=:id'), {"id": version_id})
                assert no_op.value.orig.diag.message_primary == "C1_FIXED_VERSION_UPDATE_FORBIDDEN"
                assert connection.execute(text(f'SELECT xmin::text FROM {parent} WHERE id=:id'), {"id": version_id}).scalar_one() == before_xmin
                with pytest.raises(IntegrityError) as late_child:
                    with connection.begin_nested():
                        columns = f"id,{key},material_version_id,locator" + (",activity_id" if parent == "content_lesson_version" else "")
                        values = ":new,:id,:material,'{}'::jsonb" + (",'late-noop'" if parent == "content_lesson_version" else "")
                        connection.execute(text(f'INSERT INTO {child}({columns}) VALUES ({values})'),
                                           {"new": uuid4(), "id": version_id, "material": material_version_id})
                # Check the guard, not a duplicate source's unique constraint.
                assert late_child.value.orig.diag.message_primary == "C1_SNAPSHOT_CLOSED"
        report["no_op_update_cannot_reopen_committed_question_or_lesson"] = True
        for table, key, value in [("content_question_source", "question_version_id", qvid),
                                  ("content_lesson_source", "lesson_version_id", lvid),
                                  ("content_lesson_question", "lesson_version_id", lvid),
                                  ("content_lesson_question_origin", "lesson_version_id", lvid)]:
            denied(f'DELETE FROM {table} WHERE {key}=:id', {"id": value})
            # An alternate row bypasses unique keys, so this tests closure rather than a duplicate failure.
            if table.endswith("source"):
                columns = "id," + key + ",material_version_id,chunk_id,locator"
                values = ":new,:parent,:material,NULL,'{}'::jsonb"
                if table == "content_lesson_source":
                    columns += ",activity_id"
                    values += ",'b'"
                # use a different legacy source for a genuinely new candidate row
                with runtime.begin() as connection:
                    connection.execute(text("""INSERT INTO content_material_version
                        (id,material_id,version_no,input_kind,input_text,content_hash,extraction_state,
                         source_metadata,warnings,allow_cloud,retained_bytes,created_by,created_at)
                        SELECT :new,material_id,(SELECT max(v.version_no)+1 FROM content_material_version v
                            WHERE v.material_id=content_material_version.material_id),'text','T1 other','0000','queued','{}','[]',false,0,created_by,now()
                        FROM content_material_version WHERE id=:old"""), {"new": (other := uuid4()), "old": material_version_id})
                denied(f'INSERT INTO {table} ({columns}) VALUES ({values})',
                       {"new": uuid4(), "parent": value, "material": other})
            else:
                denied(f"INSERT INTO {table}(id,lesson_version_id,activity_id,question_version_id) VALUES (:new,:parent,'b',:q)",
                       {"new": uuid4(), "parent": value, "q": qvid})
        denied("UPDATE content_question SET library_id=:library WHERE id=:id", {"library": uuid4(), "id": qid})
        denied("UPDATE content_material_version SET content_hash='changed' WHERE id=:id", {"id": material_version_id})
        report["committed_fixed_versions_and_children_closed_with_c02_protection"] = True

        with runtime.begin() as connection:
            for table, key, parent in [("content_question_draft_source", "question_id", qid),
                                       ("content_lesson_draft_source", "lesson_id", lid)]:
                columns = f"id,{key},material_version_id" + (",activity_id" if key == "lesson_id" else "")
                values = ":id,:parent,:material" + (",'a'" if key == "lesson_id" else "")
                for _ in range(2):
                    connection.execute(text(f'DELETE FROM {table} WHERE {key}=:parent'), {"parent": parent})
                    connection.execute(text(f'INSERT INTO {table}({columns}) VALUES ({values})'),
                                       {"id": uuid4(), "parent": parent, "material": material_version_id})
            connection.execute(text("INSERT INTO content_lesson_draft_question(id,lesson_id,activity_id,question_version_id) VALUES (:id,:l,'a',:q)"),
                               {"id": uuid4(), "l": lid, "q": qvid})
            connection.execute(text("DELETE FROM content_lesson_draft_question WHERE lesson_id=:id"), {"id": lid})
        denied("DELETE FROM content_lesson_draft_question_origin WHERE lesson_id=:id", {"id": lid})
        with runtime.begin() as connection:
            connection.execute(text("DELETE FROM content_lesson_draft_source WHERE lesson_id=:id"), {"id": lid})
            connection.execute(text("DELETE FROM content_lesson_draft_question_origin WHERE lesson_id=:id"), {"id": lid})
            connection.execute(text("DELETE FROM content_lesson_draft WHERE lesson_id=:id"), {"id": lid})
        report["draft_replace_unlink_origin_retention_and_whole_discard"] = True

        # Exercise the public DB contract directly. Domain command PG remains C's next stage.
        from app.domains.content.models import now
        from app.domains.content.lessons.models import LessonReview, LessonPublication
        with Session(runtime) as db:
            for review_type, publication_type, version_id in [
                (QuestionReview, QuestionPublication, qvid), (LessonReview, LessonPublication, lvid)
            ]:
                review = review_type(version_id=version_id, target_library_id=library_id,
                    submitter_id=user_id, authorization_statement="T1 synthetic permission")
                db.add(review)
                db.commit()
                rid = review.id
                with pytest.raises(IntegrityError):
                    db.add(publication_type(review_id=rid, version_id=version_id,
                        target_library_id=library_id, published_by=user_id))
                    db.commit()
                db.rollback()
                review = db.get(review_type, rid)
                review.state, review.reviewer_id, review.decided_at, review.revision = "approved", user_id, now(), 2
                db.add(review)
                db.commit()
                publication = publication_type(review_id=rid, version_id=version_id,
                    target_library_id=library_id, published_by=user_id)
                db.add(publication)
                db.commit()
                denied(f"UPDATE {review_type.__tablename__} SET authorization_statement='changed' WHERE id=:id", {"id": rid})
                denied(f"UPDATE {review_type.__tablename__} SET state='rejected',revision=revision+1 WHERE id=:id", {"id": rid})
                publication.active, publication.retired_at, publication.revision = False, now(), 2
                db.add(publication)
                db.commit()
            platform = db.exec(select(User).where(User.username == "platform")).one()
            school_b = db.exec(select(User).where(User.username == "admin_b")).one()
            public = Library(scope="platform_public", title="T1 public", audience="all", creator_id=platform.id)
            target = Library(scope="school", school_id=school_b.school_id, title="T1 target", audience="all", creator_id=school_b.id)
            db.add_all([public, target])
            db.flush()
            original, copied = Question(library_id=public.id, creator_id=platform.id), Question(library_id=target.id, creator_id=school_b.id)
            db.add_all([original, copied])
            db.flush()
            public_version = QuestionVersion(question_id=original.id, version_no=1, draft_revision=1,
                payload=sample_question(), provenance={"license": "T1 public synthetic grant", "public_reuse_allowed": True},
                payload_hash="4"*64, created_by=platform.id)
            db.add(public_version)
            db.flush()
            db.add(QuestionSource(question_version_id=public_version.id, material_version_id=material_version_id, locator={}))
            db.commit()
            copied_version = QuestionVersion(question_id=copied.id, version_no=1, draft_revision=1,
                payload=sample_question(), provenance=public_version.provenance, copied_from_version_id=public_version.id,
                payload_hash="5"*64, created_by=school_b.id)
            db.add(copied_version)
            db.flush()
            db.add(QuestionSource(question_version_id=copied_version.id, material_version_id=material_version_id, locator={}))
            db.commit()
            assert copied_version.copied_from_version_id == public_version.id
        report["schema_review_publish_retire_and_cross_school_lineage_fks"] = True
        report["domain_authorization_and_15_pg_checks"] = "not run by executor; C primary-key repair received as 6719c313"
    finally:
        # Leave a pristine HEAD schema for C, not permanent idempotency receipts from this check.
        empty_dedicated_schema()
        move(HEAD)
        report["final_schema_pristine_for_domain_pg"] = True
        target_report = ROOT / "others/reports/c1-public/t1/revision-1/schema.json"
        target_report.parent.mkdir(parents=True, exist_ok=True)
        target_report.write_text(json.dumps(report, indent=2), encoding="utf-8")
        owner.dispose()
        runtime.dispose()
