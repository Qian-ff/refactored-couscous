"""Actual 8002 HTTP/PG/Docker checks; no TestClient, mocked runner or fixture parser."""
import hashlib
import json
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text

from app.seed import fixture_id

ROOT = Path(__file__).resolve().parents[3]
BASE = "http://127.0.0.1:8002/api/v1"


class Wire:
    count = 0

    def __init__(self):
        self.runtime = json.loads((ROOT / "others/runtime/c02-public/api-runtime.json").read_text())

    def request(self, method, path, token=None, body=None, *, status=200, raw=False, key=None):
        headers = {"Idempotency-Key": key or str(uuid4())}
        if token:
            headers["Authorization"] = "Bearer " + token
        if body is not None:
            headers["Content-Type"] = "application/octet-stream" if isinstance(body, bytes) else "application/json"
            body = body if isinstance(body, bytes) else json.dumps(body).encode()
        request = Request(BASE + path, data=body, headers=headers, method=method)
        try:
            response = urlopen(request, timeout=12)
        except HTTPError as error:
            response = error
        with response:
            self.count += 1
            value = response.read(20 * 1024 * 1024 + 1)
            assert len(value) <= 20 * 1024 * 1024
            assert response.status == status, f"{method} {path}: HTTP {response.status}, expected {status}"
            return (value if raw else json.loads(value)), dict(response.headers)

    def json(self, *args, **kwargs):
        return self.request(*args, **kwargs)[0]

    def login(self, username, school="demo-a"):
        return self.json("POST", "/auth/login", body={"school_code": school, "username": username,
            "password": self.runtime["synthetic_password"]})["access_token"]

    def job(self, token, job_id):
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            result = self.json("GET", "/content/jobs/" + job_id, token)
            if result["state"] in {"succeeded", "failed", "canceled"}:
                assert result["state"] == "succeeded", result.get("error_code")
                return
            assert self.json("GET", "/health")["status"] == "ok"
            time.sleep(.3)
        raise AssertionError("Actual HTTP parse job timed out")


@pytest.fixture
def wire():
    instance = Wire()
    identity = instance.json("GET", "/dev/identity")
    assert identity["worktree_id"] == hashlib.sha256(str(ROOT).casefold().encode()).hexdigest()[:20]
    assert instance.json("GET", "/health")["migration"] == "c02d0c00001"
    return instance


def library(wire, admin, name, *, scope="school", parent=None):
    if parent is None:
        parent = wire.json("GET", "/auth/me", admin)["school"]["id"]
    return wire.json("POST", "/content/libraries", admin, {"title": name, "scope": scope,
        "parent_id": parent, "audience": "all"}, status=201)["library_id"]


def review(wire, teacher, version_id, target):
    return wire.json("POST", "/content/material-reviews", teacher, {"version_id": version_id,
        "target_library_id": target, "authorization_statement": "Synthetic original authorized for teaching"},
        status=201)["review_id"]


def publish(wire, admin, review_id, warning_hash):
    wire.json("POST", "/content/material-reviews/" + review_id + "/decision", admin,
        {"revision": 1, "decision": "approved", "warning_hash": warning_hash,
         "warnings_acknowledged": True, "original_authorized": True})
    return wire.json("POST", "/content/material-publications", admin,
        {"review_id": review_id, "revision": 2}, status=201)["publication_id"]


def test_real_binary_upload_publication_bindings_revisions_and_revocation(wire):
    admin, teacher, student = wire.login("admin"), wire.login("teacher"), wire.login("student")
    outsider = wire.login("teacher_b", "demo-b")
    tag = "C02 HTTP " + uuid4().hex[:8]
    first, second = library(wire, admin, tag + " A"), library(wire, admin, tag + " B")
    targets = wire.json("GET", "/content/submit-targets?" + urlencode({"q": tag}), teacher)
    assert {first, second} <= {item["id"] for item in targets}
    wire.json("PATCH", "/content/libraries/" + first, teacher, {"revision": 1, "title": "Not allowed"}, status=403)
    data = "实验安全\n个人防护".encode()
    upload = wire.json("POST", "/content/uploads", teacher, {"library_id": first, "title": tag,
        "original_name": "安全说明.txt", "format": "txt", "expected_bytes": len(data),
        "expected_hash": hashlib.sha256(data).hexdigest()}, status=201)["upload_id"]
    created = wire.json("PUT", "/content/uploads/" + upload + "/bytes", teacher, data)
    assert wire.json("PUT", "/content/uploads/" + upload + "/bytes", teacher, data) == created
    version, material = created["version_id"], created["material_id"]
    matching_jobs = wire.json("GET", "/content/jobs?" + urlencode({"version_id": version, "limit": 1}), teacher)
    assert matching_jobs["total"] == 1 and matching_jobs["items"][0]["version_id"] == version
    wire.job(teacher, matching_jobs["items"][0]["job_id"])
    detail = wire.json("GET", "/content/versions/" + version, teacher)
    assert detail["material_revision"] == 1 and detail["actions"]["edit_material"]
    assert not detail["actions"]["retire_material"]
    chunks = wire.json("GET", "/content/versions/" + version + "/chunks", teacher)
    assert [chunk["text"] for chunk in chunks["items"]] == ["实验安全", "个人防护"]
    for actor in (student, outsider):
        wire.json("GET", "/content/versions/" + version, actor, status=403)
        wire.json("GET", "/content/versions/" + version + "/download", actor, status=403)
    review_a, review_b = review(wire, teacher, version, first), review(wire, teacher, version, second)
    wire.json("POST", "/content/material-reviews/" + review_a + "/decision", admin,
        {"revision": 1, "decision": "approved", "warning_hash": "0" * 64,
         "warnings_acknowledged": True, "original_authorized": True}, status=409)
    publication = publish(wire, admin, review_a, detail["warning_hash"])
    wire.json("POST", "/content/material-reviews/" + review_a + "/decision", admin,
        {"revision": 1, "decision": "approved", "warning_hash": detail["warning_hash"],
         "warnings_acknowledged": True, "original_authorized": True}, status=409)
    first_view = wire.json("GET", "/content/versions/" + version + "?library_id=" + first, admin)
    second_view = wire.json("GET", "/content/versions/" + version + "?library_id=" + second, admin)
    assert first_view["binding"]["active_publication"]["id"] == publication
    assert second_view["binding"]["active_publication"] is None
    assert second_view["binding"]["review"]["id"] == review_b and second_view["binding"]["review"]["can_decide"]
    safe = wire.json("GET", "/content/versions/" + version + "?library_id=" + first, student)
    assert safe["material_revision"] is None and safe["source_metadata"] is None and safe["binding"]["review"] is None
    assert safe["actions"]["preview"] and safe["actions"]["download"] and not safe["actions"]["edit_material"]
    wire.json("GET", "/content/versions/" + version + "?library_id=" + second, student, status=403)
    original, headers = wire.request("GET", "/content/versions/" + version + "/download", student, raw=True)
    assert original == data and int(headers["content-length"]) == len(data)
    assert "filename*=UTF-8''" in headers["content-disposition"]
    wire.json("PATCH", "/content/materials/" + material, teacher, {"revision": 1, "title": tag + " renamed"})
    renamed = wire.json("GET", "/content/versions/" + version, teacher)
    assert renamed["material_revision"] == 2 and renamed["version_no"] == 1
    wire.json("PATCH", "/content/materials/" + material, teacher, {"revision": 1, "title": "Stale"}, status=409)
    wire.json("PATCH", "/content/materials/" + material, student, {"revision": 2, "title": "Forbidden"}, status=403)
    bounded = wire.json("GET", "/content/material-reviews?" + urlencode({"library_id": second, "version_id": version}), admin)
    assert bounded["total"] == 1 and bounded["items"][0]["id"] == review_b
    wire.json("POST", "/content/material-publications/" + publication + "/retire", admin, {"revision": 1})
    wire.json("GET", "/content/versions/" + version, student, status=403)
    wire.json("GET", "/content/versions/" + version + "/download", student, status=403)
    wire.json("POST", "/auth/logout", teacher)
    wire.json("PATCH", "/content/materials/" + material, teacher, {"revision": 2, "title": "Old capability"}, status=401)


def test_real_http_rechecks_course_scope_after_capability_was_read(wire):
    admin, teacher = wire.login("admin"), wire.login("teacher")
    target = library(wire, admin, "C02 scope " + uuid4().hex[:8], scope="course", parent=str(fixture_id("course-general")))
    created = wire.json("POST", "/content/materials/text", teacher,
        {"library_id": target, "title": "Scoped original", "text": "Scope check"}, status=201)
    wire.job(teacher, created["job_id"])
    before = wire.json("GET", "/content/versions/" + created["version_id"], teacher)
    assert before["actions"]["edit_material"]
    engine = create_engine(wire.runtime["database_url"])
    try:
        with engine.begin() as connection:
            connection.execute(text("UPDATE course_staff SET is_active=false WHERE id=:id"), {"id": fixture_id("staff-general")})
        wire.json("GET", "/content/versions/" + created["version_id"], teacher, status=403)
        wire.json("PATCH", "/content/materials/" + created["material_id"], teacher,
            {"revision": before["material_revision"], "title": "Old scope"}, status=403)
        wire.json("GET", "/content/versions/" + created["version_id"] + "/download", teacher, status=403)
    finally:
        with engine.begin() as connection:
            connection.execute(text("UPDATE course_staff SET is_active=true WHERE id=:id"), {"id": fixture_id("staff-general")})
        engine.dispose()
