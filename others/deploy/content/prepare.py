"""Build only the parser closure from uv.lock; write local secrets outside version control."""
from __future__ import annotations

import hashlib
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import urllib.request
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "others/scripts"))
from content_candidate_env import validate  # noqa: E402
from workflow import primary_root  # noqa: E402


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def profile_settings(profile):
    primary = primary_root(ROOT)
    branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()
    if profile == "auto":
        profile = "main" if ROOT.resolve() == primary.resolve() and branch == "main" else "c02"
    if profile in {"main", "cloud"}:
        if ROOT.resolve() != primary.resolve() or branch != "main":
            raise RuntimeError("Main parser profile requires the actual primary/main checkout")
        runtime = ROOT / "others/runtime/content-parser"
        if profile == "cloud":
            sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
            runtime = ROOT / "others/runtime/cloud-ecs/releases" / sha / "parser"
        backend = ROOT / "others/backend/.venv/Scripts/python.exe"
        worker = ROOT / "others/ai_worker/.venv/Scripts/python.exe"
    else:
        if profile == "c1":
            from c1_candidate_env import validate as validate_c1
            validate_c1()
        else:
            validate()
        runtime = ROOT / ("others/runtime/c1-public" if profile == "c1" else "others/runtime/c02-public")
        backend = runtime / "envs/backend/Scripts/python.exe"
        worker = runtime / "envs/worker/Scripts/python.exe"
    return {"profile": profile, "runtime": str(runtime), "backend": str(backend), "worker": str(worker),
            "port": 18768 if profile == "c1" else 18767}


def require_released(runtime, previous, image, protocol):
    journal = runtime / "controller/journal"
    if previous is None and any(journal.glob("*.json")):
        raise RuntimeError("Existing execution history has no controller identity; preserve it for A")
    if previous and (previous["image"] != image or previous["protocol"] != protocol):
        expected = (runtime / "controller").resolve()
        if Path(previous["root"]).resolve() != expected:
            raise RuntimeError("Existing controller root differs; preserve the original instance")
        for path in journal.glob("*.json"):
            record = json.loads(path.read_text(encoding="utf-8"))
            if record.get("released") is not True or record.get("stop_confirmed") is not True:
                raise RuntimeError("Confirm stop and release of old executions before changing image/protocol")


def license_evidence(packages, license_root, *, readonly=False):
    licenses = {}
    if not readonly:
        license_root.mkdir(parents=True, exist_ok=True)
    for name, package in sorted(packages.items()):
        installed = importlib.metadata.distribution(name)
        if installed.version != package["version"]:
            raise RuntimeError("Installed version differs from parser lock: " + name)
        files = {}
        for member in installed.files or []:
            if ".dist-info" not in str(member) or not any(word in member.name.lower() for word in ("license", "licence", "copying")):
                continue
            original = Path(installed.locate_file(member))
            if original.is_file():
                target = license_root / (name + "-" + package["version"] + "-" + member.name)
                if readonly:
                    if not target.is_file() or digest(target) != digest(original):
                        raise RuntimeError("Accepted license evidence differs: " + target.name)
                else:
                    shutil.copyfile(original, target)
                files[target.name] = digest(original)
        if not files:
            raise RuntimeError("Wheel did not provide license evidence: " + name)
        licenses[name] = {"version": package["version"], "source": package["source"], "files": files,
                          "wheel_urls": [file["url"] for file in package["wheels"]]}
    if readonly and json.loads((license_root / "manifest.json").read_text(encoding="utf-8")) != licenses:
        raise RuntimeError("Accepted license manifest differs; fix on executor branch before main activation")
    return licenses


def closure(lock, *, transfers=False):
    packages = {package["name"]: package for package in lock["package"]}
    if len(packages) != len(lock["package"]):
        raise RuntimeError("Ambiguous parser lock versions")
    needed, pending = {}, ["pypdf", "python-docx", "python-pptx", "lxml"]
    if transfers:
        pending.extend(["openpyxl", "defusedxml", "pydantic"])
    while pending:
        name = pending.pop()
        if name in needed:
            continue
        package = packages[name]
        if package.get("source") != {"registry": "https://pypi.org/simple"}:
            raise RuntimeError("Parser dependencies require the locked official PyPI source")
        needed[name] = package
        pending.extend(dependency["name"] for dependency in package.get("dependencies", []))
    return needed


def cache_linux_wheel(package, directory, *, reuse=None):
    """Fixed image uses CPython 3.13/glibc x86_64. Fetch only an official locked wheel."""
    candidates = [wheel for wheel in package.get("wheels", []) if
        wheel["url"].endswith("none-any.whl") or
        ("-cp313-cp313-manylinux" in wheel["url"] and "x86_64" in wheel["url"])]
    if not candidates:
        raise RuntimeError("No locked wheel for the fixed parser image: " + package["name"])
    wheel = sorted(candidates, key=lambda value: value["url"])[0]
    url = urlparse(wheel["url"])
    if url.scheme != "https" or url.hostname != "files.pythonhosted.org" or url.username:
        raise RuntimeError("Unexpected wheel origin")
    target = directory / url.path.rsplit("/", 1)[-1]
    if target.exists() and "sha256:" + digest(target) == wheel["hash"]:
        return target
    cached = reuse / target.name if reuse is not None else None
    if cached is not None and cached.is_file() and "sha256:" + digest(cached) == wheel["hash"]:
        shutil.copyfile(cached, target)
        return target
    with urllib.request.urlopen(wheel["url"], timeout=30) as response:
        data = response.read(32 * 1024 * 1024 + 1)
    if len(data) > 32 * 1024 * 1024 or "sha256:" + hashlib.sha256(data).hexdigest() != wheel["hash"]:
        raise RuntimeError("Official locked wheel hash mismatch")
    temporary = target.with_suffix(".new")
    temporary.write_bytes(data)
    temporary.replace(target)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("auto", "main", "cloud", "c02", "c1"), default="c02")
    parser.add_argument("--describe-profile", action="store_true", help="Read-only fixed paths and role validation")
    args = parser.parse_args()
    settings = profile_settings(args.profile)
    if args.describe_profile:
        print(json.dumps(settings))
        return
    profile = settings["profile"]
    transfers = profile in {"c1", "main", "cloud"}
    if profile in {"main", "cloud"}:
        if Path(sys.executable).resolve() != Path(settings["worker"]).resolve():
            raise RuntimeError("Main prepare must run with the fixed shared worker interpreter")
        # A receives the exact lock first; local tracked edits cannot silently select new pins.
        subprocess.run(["git", "diff", "--exit-code", "HEAD", "--", "others/ai_worker/uv.lock",
                        "others/ai_worker/pyproject.toml", "others/licenses/content-transfer"], cwd=ROOT, check=True)
    import tomllib
    worker = ROOT / "others/ai_worker"
    lock = tomllib.loads((worker / "uv.lock").read_text(encoding="utf-8"))
    packages = closure(lock, transfers=transfers)
    license_root = ROOT / ("others/licenses/content-transfer" if transfers else "others/licenses/content-parser")
    licenses = license_evidence(packages, license_root, readonly=profile in {"main", "cloud"})
    runtime = Path(settings["runtime"])
    destination = runtime / "build"
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "content").mkdir(exist_ok=True)
    wheelhouse = destination / "wheels"
    wheelhouse.mkdir(exist_ok=True)
    copied = {}
    if transfers:
        reuse = ROOT / "others/runtime/content-parser/build/wheels" if profile == "cloud" else None
        with ThreadPoolExecutor(max_workers=3) as downloads:
            for wheel in downloads.map(lambda package: cache_linux_wheel(package, wheelhouse, reuse=reuse), packages.values()):
                copied["wheels/" + wheel.name] = digest(wheel)
    # Only the pure CLI package closure; no API, DB, SQLModel, .env or speech modules.
    for name in ("app/__init__.py", "app/domains/__init__.py", "app/domains/content/__init__.py",
                 "app/domains/content/questions/__init__.py"):
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("", encoding="utf-8")
        copied[name] = digest(target)
    if transfers:
        for name in ("app/domains/content/schemas.py", "app/domains/content/questions/schemas.py",
                     "app/domains/content/questions/transfer_codec.py", "app/domains/content/questions/transfer_cli.py"):
            source, target = ROOT / "others/backend" / name, destination / name
            shutil.copyfile(source, target)
            copied[name] = digest(source)
    for name in ("__init__.py", "archive.py", "cli.py", "parser.py", "protocol.py"):
        path = worker / "content" / name
        shutil.copyfile(path, destination / "content" / name)
        copied["content/" + name] = digest(path)
    for name in ("Dockerfile", "container_entry.py"):
        path = Path(__file__).parent / name
        shutil.copyfile(path, destination / name)
        copied[name] = digest(path)
    requirements = []
    for name, package in sorted(packages.items()):
        hashes = sorted({file["hash"] for file in package.get("wheels", [])})
        if not hashes or any(not value.startswith("sha256:") for value in hashes):
            raise RuntimeError("Missing locked wheel hashes")
        requirements.append(name + "==" + package["version"] + " " + " ".join("--hash=" + value for value in hashes))
    requirement_file = destination / "requirements.txt"
    requirement_file.write_text("\n".join(requirements) + "\n", encoding="utf-8", newline="\n")
    copied["requirements.txt"] = digest(requirement_file)
    fingerprint = hashlib.sha256(json.dumps(copied, sort_keys=True).encode()).hexdigest()
    source_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    tag = "labconnect-content:" + fingerprint[:16]
    subprocess.run(["docker", "build", "--tag", tag, "--label", "labconnect.parse.source-sha=" + source_sha,
                    "--label", "labconnect.parse.content-fingerprint=" + fingerprint, str(destination)], check=True)
    image = subprocess.check_output(["docker", "image", "inspect", "--format", "{{.Id}}", tag], text=True).strip()
    evidence = {"source_sha": source_sha, "content_fingerprint": fingerprint, "image": image,
                "source_files": copied, "worker_lock_sha256": digest(worker / "uv.lock"),
                "parser_packages": sorted(packages), "contains_speech_models": False}
    if profile == "cloud":
        # Pure build: no local controller credentials, identity, journal or license writes.
        (runtime / "image.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(evidence))
        return
    server_path = runtime / "control.json"
    previous = json.loads(server_path.read_text()) if server_path.exists() else None
    root = runtime / "controller"
    root.mkdir(mode=0o700, exist_ok=True)
    protocol = "labconnect.content-control/2" if transfers else "labconnect.parse-control/1"
    require_released(runtime, previous, image, protocol)
    key = previous["key"] if previous else secrets.token_urlsafe(48)
    instance = previous["instance"] if previous else secrets.token_hex(16)
    endpoint = ({"host": "127.0.0.1", "port": settings["port"]} if os.name == "nt" else
                {"socket": str(runtime / "parse-control.sock")})
    client = {"protocol": protocol, "key": key, **endpoint}
    server = {**client, "root": str(root), "image": image, "instance": instance}
    for name, value in (("control.json", server), ("parser-client.json", client)):
        path = runtime / name
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        path.chmod(0o600)
    (runtime / "image.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    if profile != "main":
        (license_root / "manifest.json").write_text(json.dumps(licenses, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence))


if __name__ == "__main__":
    main()
