"""B1 real PostgreSQL/API invariants; public mounting/migration must be integrated by A."""
import csv
import io
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import Uuid, literal, select as sql_select, union_all
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
import pytest

from app.domains.core.auth import Identity
from app.domains.core.csv_tools import ACCOUNT_COLUMNS
from app.domains.core.models import (
    AccountInvitation, Course, CourseStaff, Enrollment, LoginSession, Major, RoleGrant, User,
)
from app.domains.core.policy import ResourceDescriptor, may_read_own_training_history, resource_access
from app.domains.core.resource_query import ResourceColumns, read_resource_predicate
from app.seed import fixture_id

PASSWORD = "Synthetic-B1-Account-Only-2026"


def command(client, method, path, headers, body=None, *, key=None):
    return getattr(client, method)("/api/v1" + path, headers={**headers, "Idempotency-Key": key or uuid4().hex},
                                   **({"json": body} if body is not None else {}))


def major(client, headers):
    response = command(client, "post", "/admin/majors", headers, {
        "school_id": str(fixture_id("school-a")), "college_id": str(fixture_id("a-chem")),
        "code": "M-" + uuid4().hex[:8], "name": "化学专业"})
    assert response.status_code == 201, response.text
    return response.json()


def account_body(major_id, *, username=None, student_no=None):
    return {"school_id": str(fixture_id("school-a")), "college_id": str(fixture_id("a-chem")),
            "major_id": major_id, "username": username or "b1-" + uuid4().hex[:8],
            "student_no": student_no or "S-" + uuid4().hex[:8], "display_name": "合成学生",
            "temporary_password": PASSWORD, "grants": [{"role": "student"}]}


def login(client, username, password=PASSWORD):
    result = client.post("/api/v1/auth/login", json={"school_code": "demo-a", "username": username, "password": password})
    assert result.status_code == 200
    return {"Authorization": "Bearer " + result.json()["access_token"]}


def class_management(client, headers, course_id=None):
    response = client.get(f"/api/v1/courses/{course_id or fixture_id('course-general')}/management", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def csv_text(rows):
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=ACCOUNT_COLUMNS)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def csv_row(major_code, username, number):
    return {"username": username, "student_no": number, "display_name": "导入合成学生", "college_code": "chem",
            "major_code": major_code, "role": "student", "temporary_password": PASSWORD, "gender": "", "contact": ""}


def identity(db, username, work_role):
    user = db.get(User, fixture_id("user-" + username))
    grants = list(db.exec(select(RoleGrant).where(RoleGrant.user_id == user.id)).all())
    session = LoginSession(user_id=user.id, expires_at=datetime.now(UTC) + timedelta(hours=1))
    return Identity(user, grants, session, work_role)


def test_account_independent_student_number_first_change_and_session_revocation(client, auth, db):
    admin = auth("admin")
    body = account_body(major(client, admin)["id"], username="different-login", student_no="2026100001")
    created = command(client, "post", "/admin/accounts", admin, body)
    assert created.status_code == 201, created.text
    value = created.json()
    assert value["username"] != value["student_no"] and value["must_change_password"]
    assert "hashed_password" not in value and PASSWORD not in created.text
    student = login(client, body["username"])
    assert client.get("/api/v1/auth/me", headers=student).json()["must_change_password"]
    assert client.get("/api/v1/profile", headers=student).status_code == 200
    assert client.get("/api/v1/courses", headers=student).status_code == 403
    assert command(client, "post", "/auth/change-password", student, {
        "old_password": PASSWORD, "new_password": PASSWORD + "-changed"}).status_code == 200
    assert client.get("/api/v1/auth/me", headers=student).status_code == 401
    changed = login(client, body["username"], PASSWORD + "-changed")
    assert client.get("/api/v1/courses", headers=changed).status_code == 200
    assert not db.get(User, UUID_value(value["id"])).must_change_password
    reset = command(client, "post", f"/admin/accounts/{value['id']}/reset-password", admin,
                    {"temporary_password": PASSWORD + "-reset"})
    assert reset.status_code == 200
    assert client.get("/api/v1/profile", headers=changed).status_code == 401
    assert client.get("/api/v1/auth/me", headers=login(client, body["username"], PASSWORD + "-reset")).json()["must_change_password"]


def UUID_value(value):
    from uuid import UUID
    return UUID(value)


def test_account_role_family_scope_and_self_escalation_are_rejected(client, auth):
    admin = auth("admin")
    mixed = account_body(major(client, admin)["id"])
    mixed["grants"].append({"role": "teacher"})
    assert command(client, "post", "/admin/accounts", admin, mixed).status_code == 422
    assert command(client, "post", f"/admin/accounts/{fixture_id('user-admin')}/grants", admin,
                   {"role": "teacher"}).status_code == 403
    assert command(client, "post", f"/admin/accounts/{fixture_id('user-student')}/grants", admin,
                   {"role": "teacher"}).status_code == 422
    assert client.get("/api/v1/admin/accounts?q=teacher_b", headers=admin).json()["count"] == 0
    assert client.get(f"/api/v1/admin/accounts/{fixture_id('user-teacher_b')}", headers=admin).status_code == 404
    assert client.get("/api/v1/admin/accounts", headers=auth()).status_code == 403
    assert client.get("/api/v1/admin/accounts?q=student&limit=1", headers=auth("college")).json()["count"] == 1


def test_org_creation_scope_reserved_platform_and_stop_preserves_rows(client, auth, db):
    platform = auth("platform", "platform")
    assert command(client, "post", "/admin/schools", platform, {"code": "platform", "name": "保留"}).status_code == 422
    assert command(client, "post", "/admin/colleges", auth("college"), {
        "school_id": str(fixture_id("school-a")), "code": "other", "name": "越权"}).status_code == 403
    organization = major(client, auth("admin"))
    updated = command(client, "patch", f"/admin/majors/{organization['id']}", auth("college"),
                      {"revision": organization["revision"], "is_active": False})
    assert updated.status_code == 200
    assert db.get(Major, UUID_value(organization["id"])) is not None
    assert command(client, "post", "/admin/accounts", auth("admin"), account_body(organization["id"])).status_code == 422


def test_csv_invalid_preview_commit_rollback_and_no_secret_echo(client, auth, db):
    admin = auth("admin")
    org = major(client, admin)
    text = csv_text([csv_row(org["code"], "csv-good", "CSV-1"), csv_row(org["code"], "teacher", "CSV-2")])
    body = {"kind": "accounts", "school_id": str(fixture_id("school-a")), "csv": text}
    checked = client.post("/api/v1/imports/preview", headers=admin, json=body)
    assert checked.status_code == 200 and not checked.json()["valid"]
    assert PASSWORD not in checked.text
    result = command(client, "post", "/imports/commit", admin, {**body, "preview_digest": checked.json()["digest"]})
    assert result.status_code == 409 and PASSWORD not in result.text
    assert db.exec(select(User).where(User.username == "csv-good")).first() is None


def test_csv_atomic_success_retry_and_changed_payload_conflict(client, auth, db):
    admin = auth("admin")
    org = major(client, admin)
    original = db.get(User, fixture_id("user-teacher")).hashed_password
    body = {"kind": "accounts", "school_id": str(fixture_id("school-a")),
            "csv": csv_text([csv_row(org["code"], "csv-one", "CSV-ONE"), csv_row(org["code"], "csv-two", "CSV-TWO")])}
    preview = client.post("/api/v1/imports/preview", headers=admin, json=body).json()
    assert preview["valid"]
    payload = {**body, "preview_digest": preview["digest"]}
    key = uuid4().hex
    first = command(client, "post", "/imports/commit", admin, payload, key=key)
    second = command(client, "post", "/imports/commit", admin, payload, key=key)
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json() and first.json()["count"] == 2
    assert PASSWORD not in first.text
    assert command(client, "post", "/imports/commit", admin, {**payload, "csv": payload["csv"] + "\n"}, key=key).status_code == 409
    assert db.get(User, fixture_id("user-teacher")).hashed_password == original


def test_csv_rechecks_conflicts_after_preview(client, auth, db):
    admin = auth("admin")
    org = major(client, admin)
    body = {"kind": "accounts", "school_id": str(fixture_id("school-a")),
            "csv": csv_text([csv_row(org["code"], "not-created", "N-1"), csv_row(org["code"], "raced", "N-2")])}
    checked = client.post("/api/v1/imports/preview", headers=admin, json=body).json()
    assert checked["valid"]
    assert command(client, "post", "/admin/accounts", admin, account_body(org["id"], username="raced", student_no="N-3")).status_code == 201
    result = command(client, "post", "/imports/commit", admin, {**body, "preview_digest": checked["digest"]})
    assert result.status_code == 409
    assert db.exec(select(User).where(User.username == "not-created")).first() is None


def test_roster_rejoin_preserves_enrollment_id_and_minimal_cross_college_data(client, auth, db):
    teacher = auth()
    course_id = fixture_id("course-general")
    original = db.exec(select(Enrollment).where(Enrollment.course_id == course_id,
                                              Enrollment.user_id == fixture_id("user-student"))).one().id
    assert command(client, "post", f"/courses/{course_id}/remove-member", teacher, {"username": "student"}).status_code == 200
    assert client.get(f"/api/v1/courses/{course_id}", headers=auth("student")).status_code == 404
    body = {"kind": "roster", "school_id": str(fixture_id("school-a")), "course_id": str(course_id), "csv": "username\nstudent\n"}
    checked = client.post("/api/v1/imports/preview", headers=teacher, json=body).json()
    assert checked["valid"]
    assert command(client, "post", "/imports/commit", teacher, {**body, "preview_digest": checked["digest"]}).status_code == 200
    assert db.exec(select(Enrollment).where(Enrollment.id == original)).one().status == "active"
    result = client.get(f"/api/v1/courses/{course_id}/members?q=student&limit=1", headers=teacher).json()
    assert result["count"] == 2 and len(result["data"]) == 1
    assert set(result["data"][0]) == {"id", "username", "display_name", "student_no", "college_id", "status"}


def test_collaborator_can_change_roster_but_cannot_transfer_or_archive(client, auth):
    teacher, collaborator = auth(), auth("teacher_eng")
    course_id = fixture_id("course-general")
    state = class_management(client, teacher)
    added = command(client, "post", f"/courses/{course_id}/staff", teacher,
                    {"revision": state["revision"], "teacher_id": str(fixture_id("user-teacher_eng"))})
    assert added.status_code == 200
    assert client.get(f"/api/v1/courses/{course_id}/teacher-options?q=teacher", headers=collaborator).status_code == 403
    options = client.get(f"/api/v1/courses/{course_id}/teacher-options?q=teacher_eng", headers=teacher).json()
    assert options["count"] == 1
    assert set(options["data"][0]) == {"id", "username", "display_name", "college_id"}
    assert command(client, "post", f"/courses/{course_id}/members", collaborator, {"username": "student"}).status_code == 200
    assert command(client, "post", f"/courses/{course_id}/archive", collaborator, {"revision": added.json()["revision"]}).status_code == 403
    assert command(client, "post", f"/courses/{course_id}/transfer", collaborator,
                   {"revision": added.json()["revision"], "teacher_id": str(fixture_id("user-teacher_eng"))}).status_code == 403
    assert command(client, "post", f"/courses/{course_id}/remove-staff", teacher,
                   {"revision": added.json()["revision"], "teacher_id": str(fixture_id("user-teacher_eng"))}).status_code == 200
    assert client.get(f"/api/v1/courses/{course_id}", headers=collaborator).status_code == 404


def test_primary_transfer_removes_old_class_access_and_protects_deactivation(client, auth, db):
    teacher, admin = auth(), auth("admin")
    course_id = fixture_id("course-general")
    user = db.get(User, fixture_id("user-teacher"))
    assert command(client, "patch", f"/admin/accounts/{user.id}", admin, {"revision": user.revision, "is_active": False}).status_code == 409
    state = class_management(client, teacher)
    result = command(client, "post", f"/courses/{course_id}/transfer", teacher,
                     {"revision": state["revision"], "teacher_id": str(fixture_id("user-teacher_eng"))})
    assert result.status_code == 200
    assert client.get(f"/api/v1/courses/{course_id}", headers=teacher).status_code == 404
    assert client.get(f"/api/v1/courses/{course_id}", headers=auth("teacher_eng")).status_code == 200
    assert command(client, "patch", f"/admin/accounts/{user.id}", admin,
                   {"revision": user.revision, "is_active": False}).status_code == 200
    assert client.get("/api/v1/auth/me", headers=teacher).status_code == 401


def test_join_leave_approval_and_invitation_rotation(client, auth, db):
    teacher, student = auth(), auth("student")
    course_id = fixture_id("course-general")
    command(client, "post", f"/courses/{course_id}/remove-member", teacher, {"username": "student"})
    state = class_management(client, teacher)
    settings = command(client, "patch", f"/courses/{course_id}/settings", teacher,
                       {"revision": state["revision"], "join_approval": True, "leave_approval": True})
    assert settings.status_code == 200
    invite = command(client, "post", f"/courses/{course_id}/invite", teacher,
                     {"revision": settings.json()["revision"], "expires_at": (datetime.now(UTC) + timedelta(days=1)).isoformat()})
    assert invite.status_code == 200
    joining = command(client, "post", "/enrollments/join", student, {"invitation_code": invite.json()["code"]})
    assert joining.status_code == 200 and joining.json()["status"] == "pending_join"
    assert client.get(f"/api/v1/courses/{course_id}", headers=student).status_code == 404
    request_id = joining.json()["request_id"]
    assert command(client, "post", f"/courses/{course_id}/requests/{request_id}/decide", teacher, {"approve": True}).status_code == 200
    leaving = command(client, "post", f"/courses/{course_id}/leave", student)
    assert leaving.json()["status"] == "pending_leave"
    assert client.get(f"/api/v1/courses/{course_id}", headers=student).status_code == 200
    assert command(client, "post", f"/courses/{course_id}/requests/{leaving.json()['request_id']}/decide", teacher,
                   {"approve": True}).status_code == 200
    assert client.get(f"/api/v1/courses/{course_id}", headers=student).status_code == 404
    me = identity(db, "student", "student")
    assert may_read_own_training_history(me, me.user.id)


def twin_class(client, admin):
    original = client.get(f"/api/v1/courses/{fixture_id('course-general')}", headers=admin).json()
    response = command(client, "post", "/courses", admin, {"college_id": str(fixture_id("a-eng")),
        "teacher_id": str(fixture_id("user-teacher_eng")), "code": "TWIN-" + uuid4().hex[:8],
        "title": "同目录第二班", "catalog_id": original["catalog_id"]})
    assert response.status_code == 201, response.text
    return response.json()


def test_catalog_owner_and_cross_college_admin_do_not_gain_sibling_roster(client, auth, db):
    twin = twin_class(client, auth("admin"))
    assert client.get(f"/api/v1/courses/{twin['id']}", headers=auth()).status_code == 404
    assert client.get(f"/api/v1/courses/{twin['id']}/members", headers=auth()).status_code == 404
    assert client.get(f"/api/v1/courses?catalog_id={twin['catalog_id']}&limit=1", headers=auth()).json()["count"] == 1
    assert client.get(f"/api/v1/courses?catalog_id={twin['catalog_id']}", headers=auth("college")).json()["count"] == 1
    assert command(client, "post", "/courses", auth(), {"college_id": str(fixture_id("a-eng")),
        "teacher_id": str(fixture_id("user-teacher")), "code": "NO-CROSS", "title": "越权", "catalog_id": twin["catalog_id"]}).status_code == 403


def test_content_point_and_sql_scopes_agree_on_sharing_and_no_answer_leak(client, auth, db):
    twin = twin_class(client, auth("admin"))
    student = identity(db, "student", "student")
    school_id = fixture_id("school-a")
    descriptors = [
        ResourceDescriptor("catalog", school_id=school_id, catalog_id=UUID_value(twin["catalog_id"]), published=True),
        ResourceDescriptor("course", school_id=school_id, course_id=UUID_value(twin["id"]), published=True),
        ResourceDescriptor("catalog", school_id=school_id, catalog_id=UUID_value(twin["catalog_id"]), published=False),
        ResourceDescriptor("school", school_id=fixture_id("school-b"), published=True),
        ResourceDescriptor("platform_public", published=True),
        ResourceDescriptor("platform_public", school_id=school_id, published=True),
        ResourceDescriptor("catalog", school_id=school_id, catalog_id=UUID_value(twin["catalog_id"]), published=True, audience="staff"),
    ]
    expected = [resource_access(db, student, descriptor).read for descriptor in descriptors]
    assert expected == [True, False, False, False, True, False, False]
    rows = []
    for index, descriptor in enumerate(descriptors):
        values = {"scope": descriptor.scope, "school_id": descriptor.school_id, "college_id": descriptor.college_id,
                  "catalog_id": descriptor.catalog_id, "course_id": descriptor.course_id, "published": descriptor.published,
                  "creator_id": descriptor.creator_id, "audience": descriptor.audience}
        rows.append(sql_select(literal(index).label("id"), *(literal(value, type_=Uuid(as_uuid=True) if key.endswith("_id") else None
            ).label(key) for key, value in values.items())))
    resources = union_all(*rows).subquery()
    columns = ResourceColumns(*(resources.c[field] for field in ResourceColumns.__dataclass_fields__))
    permitted = db.execute(sql_select(resources.c.id).where(read_resource_predicate(student, columns))).scalars().all()
    assert permitted == [0, 4]


def test_unenrollment_revokes_private_but_other_class_keeps_shared_access(client, auth, db):
    admin, student = auth("admin"), auth("student")
    twin = twin_class(client, admin)
    assert command(client, "post", f"/courses/{twin['id']}/members", admin, {"username": "student"}).status_code == 200
    assert command(client, "post", f"/courses/{fixture_id('course-general')}/leave", student).status_code == 200
    current = identity(db, "student", "student")
    assert resource_access(db, current, ResourceDescriptor("catalog", school_id=fixture_id("school-a"),
                           catalog_id=UUID_value(twin["catalog_id"]), published=True)).read
    assert not resource_access(db, current, ResourceDescriptor("course", school_id=fixture_id("school-a"),
                               course_id=fixture_id("course-general"), published=True)).read


def test_archive_preserves_history_and_denies_new_student_access(client, auth, db):
    teacher, student = auth(), auth("student")
    course_id = fixture_id("course-general")
    original = db.exec(select(Enrollment).where(Enrollment.course_id == course_id)).all()
    state = class_management(client, teacher)
    result = command(client, "post", f"/courses/{course_id}/archive", teacher, {"revision": state["revision"]})
    assert result.status_code == 200
    assert client.get(f"/api/v1/courses/{course_id}", headers=student).status_code == 404
    assert client.get(f"/api/v1/courses/{course_id}/members?status=all", headers=teacher).json()["count"] == len(original)
    assert db.get(Course, course_id).archived
    assert command(client, "post", f"/courses/{course_id}/members", teacher, {"username": "student"}).status_code == 404


def test_student_account_invitation_is_scoped_bounded_and_idempotent(client, auth, db):
    admin = auth("admin")
    org = major(client, admin)
    created = command(client, "post", "/admin/account-invitations", admin, {
        "school_id": str(fixture_id("school-a")), "college_id": str(fixture_id("a-chem")), "major_id": org["id"],
        "max_uses": 1, "expires_at": (datetime.now(UTC) + timedelta(days=1)).isoformat()})
    assert created.status_code == 201
    invite = created.json()
    assert "code_hash" not in invite
    context = client.get(f"/api/v1/auth/invitations/{invite['code']}?school_code=demo-a")
    assert context.status_code == 200 and len(context.json()["majors"]) == 1
    assert client.get(f"/api/v1/auth/invitations/{invite['code']}?school_code=demo-b").status_code == 422
    body = {"school_code": "demo-a", "invitation_code": invite["code"], "username": "invited-one",
            "student_no": "INV-1", "display_name": "邀请学生", "password": PASSWORD}
    key = uuid4().hex
    assert command(client, "post", "/auth/register", {}, body, key=key).status_code == 201
    assert command(client, "post", "/auth/register", {}, body, key=key).status_code == 201
    assert command(client, "post", "/auth/register", {}, {**body, "username": "invited-two", "student_no": "INV-2"}).status_code == 422
    assert db.get(AccountInvitation, UUID_value(invite["id"])).used_count == 1
    assert not client.get("/api/v1/auth/me", headers=login(client, "invited-one")).json()["must_change_password"]


def test_db_primary_teacher_unique_index_blocks_direct_duplicate(db):
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(CourseStaff(school_id=fixture_id("school-a"), course_id=fixture_id("course-general"),
                           user_id=fixture_id("user-teacher_eng"), is_primary=True))
        db.flush()
