"""Build only the parser closure from uv.lock; write local secrets outside version control."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "others/scripts"))
from content_candidate_env import validate  # noqa: E402


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def closure(lock):
    packages = {package["name"]: package for package in lock["package"]}
    if len(packages) != len(lock["package"]):
        raise RuntimeError("Ambiguous parser lock versions")
    needed, pending = {}, ["pypdf", "python-docx", "python-pptx", "lxml"]
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


def main():
    validate()
    worker = ROOT / "others/ai_worker"
    lock = tomllib.loads((worker / "uv.lock").read_text(encoding="utf-8"))
    packages = closure(lock)
    destination = ROOT / "others/runtime/c02-public/build"
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "content").mkdir(exist_ok=True)
    copied = {}
    for name in ("__init__.py", "archive.py", "cli.py", "parser.py", "protocol.py"):
        path = worker / "content" / name
        shutil.copyfile(path, destination / "content" / name)
        copied["content/" + name] = digest(path)
    for name in ("Dockerfile", "container_entry.py"):
        path = Path(__file__).parent / name
        shutil.copyfile(path, destination / name)
        copied[name] = digest(path)
    requirements = []
    licenses = {}
    license_root = ROOT / "others/licenses/content-parser"
    license_root.mkdir(parents=True, exist_ok=True)
    for name, package in sorted(packages.items()):
        installed = importlib.metadata.distribution(name)
        if installed.version != package["version"]:
            raise RuntimeError("Candidate installed version differs from parser lock: " + name)
        hashes = sorted({file["hash"] for file in package.get("wheels", [])})
        if not hashes or any(not value.startswith("sha256:") for value in hashes):
            raise RuntimeError("Missing locked wheel hashes")
        requirements.append(name + "==" + package["version"] + " " + " ".join("--hash=" + value for value in hashes))
        files = {}
        for member in installed.files or []:
            if ".dist-info" not in str(member) or "license" not in member.name.lower():
                continue
            original = Path(installed.locate_file(member))
            if original.is_file():
                target = license_root / (name + "-" + package["version"] + "-" + member.name)
                shutil.copyfile(original, target)
                files[target.name] = digest(target)
        if not files:
            raise RuntimeError("Wheel did not provide license evidence: " + name)
        licenses[name] = {"version": package["version"], "source": package["source"], "files": files,
                          "wheel_urls": [file["url"] for file in package["wheels"]]}
    requirement_file = destination / "requirements.txt"
    requirement_file.write_text("\n".join(requirements) + "\n", encoding="utf-8", newline="\n")
    copied["requirements.txt"] = digest(requirement_file)
    fingerprint = hashlib.sha256(json.dumps(copied, sort_keys=True).encode()).hexdigest()
    source_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    tag = "labconnect-content:" + fingerprint[:16]
    subprocess.run(["docker", "build", "--tag", tag, "--label", "labconnect.parse.source-sha=" + source_sha,
                    "--label", "labconnect.parse.content-fingerprint=" + fingerprint, str(destination)], check=True)
    image = subprocess.check_output(["docker", "image", "inspect", "--format", "{{.Id}}", tag], text=True).strip()
    runtime = ROOT / "others/runtime/c02-public"
    server_path = runtime / "control.json"
    previous = json.loads(server_path.read_text()) if server_path.exists() else None
    root = runtime / "controller"
    root.mkdir(mode=0o700, exist_ok=True)
    if previous and previous["image"] != image:
        if any(not json.loads(path.read_text()).get("released") for path in (root / "journal").glob("*.json")):
            raise RuntimeError("Stop and release the old parser executions before changing image")
    key = previous["key"] if previous else secrets.token_urlsafe(48)
    instance = previous["instance"] if previous else secrets.token_hex(16)
    endpoint = ({"host": "127.0.0.1", "port": 18767} if os.name == "nt" else
                {"socket": str(runtime / "parse-control.sock")})
    client = {"protocol": "labconnect.parse-control/1", "key": key, **endpoint}
    server = {**client, "root": str(root), "image": image, "instance": instance}
    for name, value in (("control.json", server), ("parser-client.json", client)):
        path = runtime / name
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        path.chmod(0o600)
    evidence = {"source_sha": source_sha, "content_fingerprint": fingerprint, "image": image,
                "source_files": copied, "worker_lock_sha256": digest(worker / "uv.lock"),
                "parser_packages": sorted(packages), "contains_speech_models": False}
    (runtime / "image.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    (license_root / "manifest.json").write_text(json.dumps(licenses, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence))


if __name__ == "__main__":
    main()
