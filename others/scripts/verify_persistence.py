"""Use real HTTP/DB; run write, restart services, then read. No credentials printed."""
import argparse
import json
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["write", "read"])
    args = parser.parse_args()
    fixtures = json.loads((ROOT / "others/runtime/demo-accounts.json").read_text(encoding="utf-8"))
    evidence = ROOT / "others/reports/a1/persistence.json"
    evidence.parent.mkdir(parents=True, exist_ok=True)

    def request(route, body=None, token=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        data = json.dumps(body).encode("utf-8") if body is not None else None
        with urlopen(Request("http://127.0.0.1:8000/api/v1" + route, data=data, headers=headers), timeout=10) as response:
            return json.load(response)

    def login(username, school="demo-a"):
        return request("/auth/login", {"school_code": school, "username": username, "password": fixtures["password"]})["access_token"]

    if args.mode == "write":
        record = request("/courses", {"college_id": fixtures["ids"]["colleges"]["a-chem"],
            "teacher_id": fixtures["ids"]["users"]["teacher"], "code": "PERSIST-" + str(int(time.time())),
            "title": "A1 服务重启持久化验证"}, login("teacher"))
        evidence.write_text(json.dumps({"course": record, "written_at": time.time(), "read_after_restart": False}, ensure_ascii=False, indent=2), encoding="utf-8")
        print("PASS: course written through the real API; restart services before read")
    else:
        result = json.loads(evidence.read_text(encoding="utf-8"))
        actual = request("/courses/" + result["course"]["id"], token=login("admin"))
        assert actual == result["course"]
        try:
            request("/courses/" + actual["id"], token=login("admin_b", "demo-b"))
        except HTTPError as error:
            assert error.code == 404
        else:
            raise AssertionError("Cross-school read unexpectedly succeeded")
        result.update(read_after_restart=True, verified_at=time.time(), cross_tenant_read="denied")
        evidence.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print("PASS: previously written course survives service restart; cross-school read denied")


if __name__ == "__main__":
    main()
