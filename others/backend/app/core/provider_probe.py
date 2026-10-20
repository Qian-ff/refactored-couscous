"""Bounded A0 live test. Writes only redacted status/usage, never request headers or keys."""
import json
import re

import httpx
from pydantic import BaseModel, ConfigDict, Field

from app.core.providers import master_key, open_key, platform_profile, shared_root


class ProbeQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question_type: str = Field(pattern="^single$")
    stem: str = Field(min_length=1, max_length=120)
    options: dict[str, str]
    answer: str
    source_id: str = Field(pattern="^synthetic-test-1$")


def main():
    root = shared_root()
    report_path = root / "others/reports/a0/provider.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    counter = root / "others/runtime/a0-provider-request-count.json"
    profile = platform_profile()
    if profile.spec.base_url != "https://api.deepseek.com" or profile.spec.model != "deepseek-flash":
        raise SystemExit("A0 live test is restricted to the authorized official Flash profile")
    secret = open_key(profile.ciphertext, scope="platform", revision=profile.revision, key=master_key())
    state = json.loads(counter.read_text()) if counter.exists() else {"requests": 0}
    report = {"provider": profile.spec.base_url, "model": profile.spec.model,
              "revision": str(profile.revision), "calls": [], "status": "incomplete"}
    prompts = ["Reply with exactly OK.",
        'Return JSON only, with fields question_type="single", stem="1+1=?", options={"A":"2","B":"3"}, '
        'answer="A", source_id="synthetic-test-1". The supplied synthetic source says 1+1=2.']
    try:
        with httpx.Client(timeout=45, follow_redirects=False) as client:
            for index, prompt in enumerate(prompts):
                attempt = 0
                while True:
                    if state["requests"] >= 3:
                        raise RuntimeError("authorized_request_limit_reached")
                    state["requests"] += 1
                    counter.write_text(json.dumps(state) + "\n", encoding="utf-8")
                    payload = {"model": "deepseek-flash", "thinking": {"type": "disabled"},
                               "stream": False, "max_tokens": 512,
                               "messages": [{"role": "user", "content": prompt}]}
                    if index:
                        payload["response_format"] = {"type": "json_object"}
                    try:
                        response = client.post("https://api.deepseek.com/chat/completions",
                            headers={"Authorization": "Bearer " + secret.get_secret_value()}, json=payload)
                        report["calls"].append({"test": "json_schema" if index else "connection", "http_status": response.status_code})
                        if response.status_code in (401, 402, 403, 429):
                            raise RuntimeError("provider_http_" + str(response.status_code))
                        response.raise_for_status()
                        body = response.json()
                        report["calls"][-1]["usage"] = body.get("usage", {})
                        content = body["choices"][0]["message"]["content"]
                        if index:
                            item = ProbeQuestion.model_validate_json(content)
                            if item.options != {"A": "2", "B": "3"} or item.answer != "A":
                                raise RuntimeError("business_schema_failed")
                        elif content.strip() != "OK":
                            raise RuntimeError("connection_content_failed")
                        report["calls"][-1]["validated"] = True
                        break
                    except (httpx.TransportError, httpx.HTTPStatusError):
                        if attempt or state["requests"] >= 3:
                            raise RuntimeError("provider_transport_failed") from None
                        attempt += 1
        report["status"] = "passed"
    except Exception as error:
        # Do not serialize arbitrary exception messages: HTTP libraries may include headers/body.
        code = str(error) if re.fullmatch(r"[a-z_0-9]+", str(error)) else type(error).__name__
        report["error"] = code
    report["total_requests"] = state["requests"]
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))
    if report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
