"""Read-only cloud access/security regression using existing synthetic accounts; never seed/reset data."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import socket
import ssl
import sys
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "others/scripts"))
import cloud  # noqa: E402


def main():
    state = json.loads((cloud.RUNTIME / "secrets/accounts.json").read_text(encoding="utf-8"))
    base = "https://" + cloud.connection()["host"]
    assert state["service_url"] == base
    checks = []

    def request(method, path, body=None, token=None, expected=200, headers=None):
        value = {"Content-Type": "application/json", **(headers or {})}
        if token:
            value["Authorization"] = "Bearer " + token
        req = urllib.request.Request(base + path, method=method, headers=value,
            data=json.dumps(body).encode() if body is not None else None)
        try:
            response = urllib.request.urlopen(req, timeout=15)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            assert response.status == expected, f"HTTP status mismatch: {method} {path}"
            raw = response.read()
        checks.append({"method": method, "path": path, "status": expected})
        return json.loads(raw) if raw and method != "OPTIONS" and expected < 400 else None

    health = request("GET", "/api/v1/health")
    assert health == {"status": "ok", "database": "postgresql", "contract": "0.3.2", "migration": "b1c0e0a00001"}
    info = request("GET", "/build-info.json")
    tokens = {}
    request("GET", "/api/v1/courses", expected=401)
    for label, entry in state["demo_accounts"].items():
        token = request("POST", "/api/v1/auth/login", {"school_code": entry["school_code"],
            "username": entry["username"], "password": entry["password"]})["access_token"]
        tokens[label] = token
        me = request("GET", "/api/v1/auth/me", token=token)
        assert me["active_work_role"] == ("administrator" if label == "admin" else entry["role"])
        courses = request("GET", "/api/v1/courses", token=token)["data"]
        assert any(item["id"] == state["demo_course_id"] for item in courses) == (label != "teacher_b")
    relations = request("GET", "/api/v1/enrollments/mine", token=tokens["student"])
    assert any(item["course_id"] == state["demo_course_id"] for item in relations["data"])
    request("GET", "/api/v1/courses/" + state["demo_course_id"], token=tokens["teacher_b"], expected=404)
    request("GET", "/api/v1/courses", token=tokens["student"], expected=403,
            headers={"X-Work-Role": "administrator"})
    for origin, code in [("http://127.0.0.1:48621", 200), ("https://localhost", 200), ("http://localhost", 200),
                         ("https://evil.invalid", 400)]:
        request("OPTIONS", "/api/v1/auth/login", expected=code, headers={"Origin": origin,
            "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type,authorization"})
    for path in ("/api/v1/dev/identity", "/api/v1/docs", "/docs", "/redoc", "/api/v1/asr", "/api/v1/assistant"):
        request("GET", path, expected=404)
    for token in tokens.values():
        request("POST", "/api/v1/auth/logout", token=token)
        request("GET", "/api/v1/auth/me", token=token, expected=401)

    def reachable(port):
        try:
            with socket.create_connection((cloud.connection()["host"], port), timeout=3):
                return str(port), True
        except OSError:
            return str(port), False

    with ThreadPoolExecutor(max_workers=8) as pool:
        ports = dict(pool.map(reachable, [22, 80, 443, 5432, 55432, 8000, 3389, 18765]))
    assert all(ports[str(p)] for p in (22, 80, 443))
    assert not any(ports[str(p)] for p in (5432, 55432, 8000, 3389, 18765))
    with socket.create_connection((cloud.connection()["host"], 443), timeout=10) as raw:
        with ssl.create_default_context().wrap_socket(raw, server_hostname=cloud.connection()["host"]) as tls:
            cert = tls.getpeercert()
            tls_status = {"trusted": True, "protocol": tls.version(), "not_after": cert["notAfter"]}
    report = {"status": "passed", "service": base, "web": info, "health": health,
              "http_checks": len(checks), "checks": checks, "ports": ports, "tls": tls_status,
              "synthetic_accounts": 4, "data_reset": False}
    folder = ROOT / "others/reports/cloud-asr"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "access.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "checks"}))


if __name__ == "__main__":
    main()
