"""Checks runnable without a DB using --confcutdir=app/domains/core/tests for this file only."""
import json
from uuid import uuid4

from fastapi import FastAPI
from pydantic import SecretStr

from app.domains.core.class_routes import router as classes
from app.domains.core.csv_tools import csv_template, fingerprint, parse_csv
from app.domains.core.import_routes import router as imports
from app.domains.core.management_routes import router as management
from app.domains.learning.availability import tutoring_status


def test_request_fingerprints_include_passwords_without_storing_them():
    first = {"temporary_password": SecretStr("Synthetic-First-Secret")}
    second = {"temporary_password": SecretStr("Synthetic-Other-Secret")}
    assert fingerprint(first) != fingerprint(second)
    assert "Synthetic" not in fingerprint(first)


def test_csv_bom_header_duplicate_and_secret_errors():
    header = csv_template("accounts")
    row = "student-one,20261001,学生,chem,chemistry,student,Synthetic-First-Secret,,\r\n"
    rows, errors = parse_csv(header + row + row, "accounts")
    assert len(rows) == 2
    assert {error["field"] for error in errors} == {"username", "student_no"}
    assert "Synthetic-First-Secret" not in json.dumps(errors)
    assert parse_csv("username,username\na,b\n", "roster")[1]
    assert parse_csv("unknown\na\n", "accounts")[1]


def test_csv_counts_invalid_rows_against_limit():
    rows, errors = parse_csv("username\n" + "a,b\n" * 600, "roster")
    assert not rows
    assert len(errors) == 501
    assert "500" in errors[-1]["message"]


def test_new_domain_routes_export_actual_typed_operations():
    app = FastAPI()
    for router in (management, classes, imports):
        app.include_router(router, prefix="/api/v1")
    schema = app.openapi()
    assert "/api/v1/admin/accounts" in schema["paths"]
    assert "/api/v1/courses/{course_id}/transfer" in schema["paths"]
    assert not any("tutoring" in path or "training-records" in path for path in schema["paths"])
    assert schema["components"]["schemas"]["AccountCreate"]["properties"]["temporary_password"]["writeOnly"]


def test_unimplemented_exam_gate_never_allows_students():
    gate = tutoring_status(uuid4())
    assert gate.state == "unavailable" and not gate.implemented
