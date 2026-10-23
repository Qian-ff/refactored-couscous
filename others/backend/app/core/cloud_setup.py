"""A-only cloud provider preparation/probe. No public configuration route, no school auto-enablement."""
import argparse
import json
import urllib.error
import urllib.request

from app.core.providers import EncryptedProfile, master_key, open_key, platform_profile, seal_key, shared_root


def prepare():
    root = shared_root()
    folder = root / "others/runtime/cloud-ecs/secrets"
    profile = platform_profile()
    if profile.spec.base_url != "https://api.deepseek.com" or profile.spec.model != "deepseek-flash":
        raise RuntimeError("Cloud preflight requires the existing authorized official Flash configuration")
    secret = open_key(profile.ciphertext, scope="platform", revision=profile.revision, key=master_key())
    cloud_key = (folder / "ai-master.key").read_bytes()
    value = EncryptedProfile(revision=profile.revision, spec=profile.spec,
        ciphertext=seal_key(secret.get_secret_value(), scope="platform", revision=profile.revision, key=cloud_key))
    (folder / "platform-ai.json").write_text(value.model_dump_json(indent=2) + "\n", encoding="utf-8")
    print(json.dumps(value.public_status()))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        return None


def probe():
    import fcntl
    folder = shared_root() / "others/runtime/files"
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / "cloud-provider-preflight.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _probe()


def _probe():
    profile = platform_profile()
    if profile.spec.base_url != "https://api.deepseek.com" or profile.spec.model != "deepseek-flash":
        raise RuntimeError("Probe is restricted to official Flash; no endpoint/model substitution")
    folder = shared_root() / "others/runtime/files"
    folder.mkdir(parents=True, exist_ok=True)
    report_file = folder / "cloud-provider-preflight.json"
    previous = json.loads(report_file.read_text()) if report_file.exists() else {}
    if previous.get("revision") == str(profile.revision) and previous.get("status") == "passed":
        print(json.dumps(previous))
        return
    if previous.get("requests", 0) >= 1:
        raise RuntimeError("Preflight request allowance exhausted; inspect the saved result before another authorization")
    secret = open_key(profile.ciphertext, scope="platform", revision=profile.revision, key=master_key())
    payload = {"model": profile.spec.model, "thinking": {"type": "disabled"}, "stream": False,
        "max_tokens": 128, "response_format": {"type": "json_object"},
        "messages": [{"role": "user", "content": 'Return only JSON {"status":"OK","answer":2}. Synthetic check: 1+1=2.'}]}
    report = {"revision": str(profile.revision), "model": profile.spec.model,
              "requests": 1, "status": "pending"}
    # Persist the bound before making a request. No retries, top-ups or Pro calls.
    report_file.write_text(json.dumps(report) + "\n")
    request = urllib.request.Request(profile.spec.base_url + "/chat/completions", method="POST",
        headers={"Authorization": "Bearer " + secret.get_secret_value(), "Content-Type": "application/json"},
        data=json.dumps(payload).encode())
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=45) as response:
            body = json.loads(response.read(65536))
            report["http_status"] = response.status
        value = json.loads(body["choices"][0]["message"]["content"])
        if value != {"status": "OK", "answer": 2}:
            raise ValueError()
        report.update(status="passed", usage=body.get("usage", {}), json_structure_validated=True)
    except urllib.error.HTTPError as error:
        report.update(status="failed", http_status=error.code, error="provider_http")
    except (OSError, ValueError, KeyError, IndexError):
        report.update(status="failed", error="provider_transport_or_structure")
    report_file.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    if report["status"] != "passed":
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "probe"])
    args = parser.parse_args()
    if args.command == "prepare":
        prepare()
    else:
        probe()


if __name__ == "__main__":
    main()
