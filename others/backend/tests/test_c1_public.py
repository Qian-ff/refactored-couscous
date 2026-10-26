"""Opt-in, real C1 candidate HTTP/runner flow on the fixed non-owner test profile."""
import hashlib
import json
import os
from pathlib import Path
import time
from uuid import UUID, uuid4

import httpx
import jwt
import pytest
from sqlalchemy import create_engine
from sqlmodel import Session

from app.domains.content.background_identity import load_identity
from app.domains.content.questions.models import TransferTask
from app.domains.content.questions.schemas import DraftContent, Provenance, QuestionPayload
from app.domains.content.questions.transfer_codec import export_template, parse_template
from app.domains.content.questions.tests.unit.test_schema import sample_question
from app.domains.content.lessons.tests.unit.test_content import sample_lesson
from app.domains.content.lessons.tests.unit.test_scenes import SAFE
from app.domains.content.questions.assessment import resolve_assessment_questions
from app.domains.content.lessons.assessment import resolve_lesson_publication, student_lesson_from_snapshot

pytestmark = pytest.mark.skipif(os.environ.get("LABCONNECT_C1_LIVE") != "1", reason="Requires the explicit C1 live candidate")
ROOT = Path(__file__).resolve().parents[3]


def test_real_csv_xlsx_runner_staff_http_and_private_snapshot_contract():
    config = json.loads((ROOT / "others/runtime/c1-public/api-runtime.json").read_text())
    engine = create_engine(config["database_url"])
    report = {"api_origin": "http://127.0.0.1:8002", "formats": [], "physical_clients_tested": False}
    tokens = {}
    with httpx.Client(base_url="http://127.0.0.1:8002/api/v1", timeout=20) as api:
        def call(actor, method, route, body=None, expected=200, raw=None):
            headers = {"Idempotency-Key": "t2-live-" + str(uuid4())}
            if actor:
                headers["Authorization"] = "Bearer " + tokens[actor]
            if raw is not None:
                headers["Content-Type"] = "application/octet-stream"
            response = api.request(method, route, json=body if raw is None else None, content=raw, headers=headers)
            assert response.status_code == expected, (method, route, response.status_code, response.text[:500])
            return response

        def wait_task(task_id, wanted="succeeded", seconds=50):
            deadline = time.monotonic() + seconds
            while time.monotonic() < deadline:
                row = call("teacher", "GET", "/content/questions/tasks/" + task_id).json()
                if row["state"] == wanted:
                    return row
                assert row["state"] not in {"failed", "expired"}, row
                time.sleep(.1)
            raise AssertionError("Candidate transfer did not reach " + wanted)

        def clean(task_id):
            deadline = time.monotonic() + 25
            while time.monotonic() < deadline:
                with Session(engine) as db:
                    row = db.get(TransferTask, UUID(task_id))
                    if row.stop_confirmed and row.reserved_bytes == 0:
                        return {"execution_id": str(row.execution_id), "generation": row.generation,
                            "stop_confirmed": True, "reserved_bytes": 0, "retained_bytes": row.retained_bytes}
                time.sleep(.1)
            raise AssertionError("Actual stop/cleanup not confirmed")

        for username, school in [("admin", "demo-a"), ("teacher", "demo-a"), ("student", "demo-a"), ("teacher_b", "demo-b")]:
            tokens[username] = call(None, "POST", "/auth/login", {"school_code": school, "username": username,
                "password": config["synthetic_password"]}).json()["access_token"]
        report["source"] = call(None, "GET", "/dev/identity").json()
        assert report["source"]["contract"] == "0.5.0"
        me = call("admin", "GET", "/auth/me").json()
        library = call("admin", "POST", "/content/libraries", {"scope": "school", "parent_id": me["school"]["id"],
            "audience": "all", "title": "T2合成往返" + str(uuid4())}, 201).json()["library_id"]
        versions = []
        for format in ("csv", "xlsx"):
            content = DraftContent(payload=QuestionPayload.model_validate({**sample_question(), "stem": "T2合成" + format + str(uuid4())}),
                provenance=Provenance(license="Synthetic functional test", teaching_reuse_allowed=True))
            data = export_template([content], format)
            created = call("teacher", "POST", "/content/questions/imports", {"library_id": library,
                "format": format, "expected_bytes": len(data), "input_hash": hashlib.sha256(data).hexdigest()}, 201).json()
            task_id, batch_id = created["task_id"], created["batch_id"]
            call("teacher", "PUT", f"/content/questions/tasks/{task_id}/input", raw=data)
            call("teacher", "PUT", f"/content/questions/tasks/{task_id}/input", raw=data, expected=409)
            wait_task(task_id)
            import_cleanup = clean(task_id)
            batch = call("teacher", "GET", "/content/questions/imports/" + batch_id).json()
            assert batch["state"] == "ready", batch
            call("teacher", "POST", f"/content/questions/imports/{batch_id}/confirm", {"revision": batch["revision"],
                "library_id": library, "input_hash": batch["input_hash"], "preview_hash": batch["preview_hash"]})
            question = call("teacher", "GET", f"/content/questions/imports/{batch_id}/created").json()["items"][0]["question_id"]
            submitted = call("teacher", "POST", f"/content/questions/drafts/{question}/submit", {"revision": 1,
                "target_library_id": library, "authorization_statement": "Synthetic test authorization"}).json()
            review, version = submitted["review_id"], submitted["version_id"]
            call("admin", "POST", f"/content/questions/reviews/{review}/decision", {"revision": 1, "decision": "approved"})
            call("admin", "POST", f"/content/questions/reviews/{review}/publish", {"revision": 2})
            versions.append(version)
            exported = call("teacher", "POST", "/content/questions/exports", {"library_id": library, "format": format,
                "version_ids": [version], "authorization_statement": "Synthetic export authorization"}, 201).json()
            wait_task(exported["task_id"])
            export_cleanup = clean(exported["task_id"])
            result = call("teacher", "GET", f"/content/questions/exports/{exported['task_id']}/download").content
            parsed = parse_template(result, format)
            assert parsed.rows[0].content.payload == content.payload
            call("student", "GET", "/content/questions/versions/" + version, expected=403)
            call("teacher_b", "GET", "/content/questions/versions/" + version, expected=403)
            report["formats"].append({"format": format, "input_bytes": len(data), "output_bytes": len(result),
                "output_sha256": hashlib.sha256(result).hexdigest(), "payload_roundtrip": True,
                "version": version, "import": import_cleanup, "export": export_cleanup})

        # Ordinary cancellation catches the actual running execution, then retries only after cleanup.
        canceled = call("teacher", "POST", "/content/questions/exports", {"library_id": library, "format": "csv",
            "version_ids": versions, "authorization_statement": "Synthetic cancel and retry"}, 201).json()
        wait_task(canceled["task_id"], wanted="running")
        call("teacher", "POST", f"/content/questions/tasks/{canceled['task_id']}/cancel", {"generation": 1})
        report["cancellation"] = clean(canceled["task_id"])
        retry = call("teacher", "POST", f"/content/questions/tasks/{canceled['task_id']}/retry", {"generation": report["cancellation"]["generation"]}).json()
        wait_task(canceled["task_id"])
        report["retry"] = clean(canceled["task_id"])
        assert report["retry"]["execution_id"] != report["cancellation"]["execution_id"]
        assert retry["generation"] == report["retry"]["generation"]

        # One legacy text parse shares the same scheduler/controller and remains usable.
        legacy = call("teacher", "POST", "/content/materials/text", {"library_id": library,
            "title": "T2合成旧资料兼容", "text": "Synthetic legacy compatibility"}, 201).json()
        deadline = time.monotonic() + 50
        while time.monotonic() < deadline:
            old = call("teacher", "GET", "/content/versions/" + legacy["version_id"]).json()
            if old["extraction_state"] == "succeeded":
                break
            time.sleep(.2)
        assert old["extraction_state"] == "succeeded"
        report["legacy_material"] = {"version": legacy["version_id"], "parsed": True}
        ROOT.joinpath("others/reports/c1-public/t2/live-http.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    engine.dispose()


def test_private_b2_snapshots_and_student_projection_remain_separate():
    config = json.loads((ROOT / "others/runtime/c1-public/api-runtime.json").read_text())
    engine = create_engine(config["database_url"])
    tokens = {}
    with httpx.Client(base_url="http://127.0.0.1:8002/api/v1", timeout=20) as api:
        def call(actor, method, route, body=None, expected=200):
            headers = {"Idempotency-Key": "t2-snapshot-" + str(uuid4())}
            if actor:
                headers["Authorization"] = "Bearer " + tokens[actor]
            response = api.request(method, route, json=body, headers=headers)
            assert response.status_code == expected, (method, route, response.status_code, response.text[:500])
            return response

        for actor in ("teacher", "admin", "student", "teacher_eng"):
            tokens[actor] = call(None, "POST", "/auth/login", {"school_code": "demo-a", "username": actor,
                "password": config["synthetic_password"]}).json()["access_token"]
        previous = json.loads((ROOT / "others/reports/c1-public/t2/live-http.json").read_text())
        version_id = previous["formats"][0]["version"]
        version = call("teacher", "GET", "/content/questions/versions/" + version_id).json()
        library = version["library_id"]
        teacher = call("teacher", "GET", "/auth/me").json()
        college = call("teacher", "GET", "/courses/context").json()["colleges"][0]["id"]
        course = call("teacher", "POST", "/courses", {"college_id": college, "teacher_id": teacher["id"],
            "code": "T2_" + uuid4().hex[:10], "title": "T2合成受控快照"}, 201).json()["id"]
        engineering = call("teacher_eng", "GET", "/courses/context").json()["colleges"][0]["id"]
        engineering_course = call("teacher_eng", "GET", "/courses").json()["data"][0]["id"]
        for scope, parent in (("college", engineering), ("course", engineering_course)):
            restricted = call("admin", "POST", "/content/libraries", {"scope": scope, "parent_id": parent,
                "audience": "all", "title": "T2合成范围校验" + uuid4().hex[:8]}, 201).json()["library_id"]
            call("teacher", "POST", "/content/questions/drafts", {"library_id": restricted, "payload": sample_question()}, expected=403)
        provenance = Provenance(license="Synthetic functional test", teaching_reuse_allowed=True).model_dump(mode="json")
        asset = call("teacher", "POST", "/content/lessons/scenes", {"library_id": library, "svg": SAFE,
            "provenance": provenance}, 201).json()["asset_id"]
        raw = sample_lesson()
        raw["title"] = "T2合成关卡" + uuid4().hex[:8]
        raw["scene"]["svg_asset_id"] = asset
        raw["provenance"] = provenance
        lesson = call("teacher", "POST", "/content/lessons/drafts", {"library_id": library, "content": raw}, 201).json()["lesson_id"]
        submitted = call("teacher", "POST", f"/content/lessons/drafts/{lesson}/submit", {"revision": 1,
            "target_library_id": library, "authorization_statement": "Synthetic functional authorization"}).json()
        review, lesson_version = submitted["review_id"], submitted["version_id"]
        call("admin", "POST", f"/content/lessons/reviews/{review}/decision", {"revision": 1, "decision": "approved"})
        call("admin", "POST", f"/content/lessons/reviews/{review}/publish", {"revision": 2})
        scene = call("teacher", "GET", f"/content/lessons/versions/{lesson_version}/preview/scene")
        assert "no-store" in scene.headers["cache-control"]
        assert "sandbox" in scene.headers["content-security-policy"]
        call("student", "GET", f"/content/lessons/versions/{lesson_version}/preview", expected=403)
        call("student", "GET", f"/content/lessons/versions/{lesson_version}/preview/scene", expected=403)

        def current(db, actor):
            claims = jwt.decode(tokens[actor], options={"verify_signature": False})
            return load_identity(db, UUID(claims["sub"]), UUID(claims["jti"]), "teacher" if actor == "teacher" else "student")

        with Session(engine) as db:
            teacher_identity = current(db, "teacher")
            questions = resolve_assessment_questions(db, teacher_identity, UUID(course), [UUID(version_id)])
            snapshots = resolve_lesson_publication(db, teacher_identity, UUID(course), [UUID(lesson_version)])
            frozen_question = questions[0].model_dump(mode="json")
            frozen_lesson = snapshots[0].model_dump(mode="json")
            # This helper filters fields; B2 must still authorize its task, relation and unlock.
            student = student_lesson_from_snapshot(db, current(db, "student"), snapshots[0]).model_dump(mode="json")
            assert "review" not in student and "scoring" not in student and "payload_hash" not in student
            assert "correct_ids" not in json.dumps(student) and "answer_ids" not in json.dumps(student)
            assert frozen_lesson["preview"]["review"]
            assert frozen_question["payload"]["answer_ids"]
        draft = call("teacher", "GET", "/content/questions/drafts/" + version["question_id"]).json()
        updated = {"payload": draft["payload"], "provenance": draft["provenance"], "revision": draft["revision"],
            "sources": [{"material_version_id": row["material_version_id"], "chunk_id": row["chunk_id"]} for row in draft["sources"]]}
        updated["payload"] = {**updated["payload"], "stem": "T2合成新草稿" + uuid4().hex[:8]}
        call("teacher", "PATCH", "/content/questions/drafts/" + version["question_id"], updated)
        with Session(engine) as db:
            after = resolve_assessment_questions(db, current(db, "teacher"), UUID(course), [UUID(version_id)])
            assert after[0].model_dump(mode="json") == frozen_question
        result = {"source": call(None, "GET", "/dev/identity").json(), "private_question_snapshot": True,
            "private_lesson_snapshot": True, "student_safe_projection": True, "draft_edit_preserves_fixed_scoring": True,
            "teacher_svg_private_no_store_csp": True, "student_direct_preview_and_svg_denied": True,
            "other_college_and_unassigned_course_write_denied": True,
            "b2_task_assignment_unlock_implemented": False}
        ROOT.joinpath("others/reports/c1-public/t2/private-snapshots.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    engine.dispose()
