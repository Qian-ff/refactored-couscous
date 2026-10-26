"""Build the standard-library-only controller closure; no local runtime configuration."""
import hashlib
import json
import shutil
import subprocess

FILES = (
    "others/deploy/content/control.py", "others/deploy/content/output_files.py", "others/deploy/content/probe.py",
    "others/backend/app/core/content_runner.py", "others/backend/app/domains/content/parse_runner.py",
)


def context(root, destination):
    lock = json.loads((root / 'others/deploy/cloud/images.lock.json').read_text(encoding='utf-8'))
    dockerfile = (root / 'others/deploy/cloud/Dockerfile.control').read_text(encoding='utf-8')
    if any('FROM ' + lock[key] not in dockerfile for key in ('controller_python', 'docker_cli')):
        raise RuntimeError('Controller base differs from the official pinned image lock')
    licenses = root / 'others/licenses/cloud-controller'
    manifest = json.loads((licenses / 'manifest.json').read_text(encoding='utf-8'))
    for name, expected in manifest['docker_cli']['files'].items():
        if hashlib.sha256((licenses / name).read_bytes()).hexdigest() != expected:
            raise RuntimeError('Controller upstream license evidence differs')
    destination.mkdir(parents=True, exist_ok=True)
    for package in ("app", "app/core", "app/domains", "app/domains/content"):
        target = destination / "others/backend" / package / "__init__.py"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("", encoding="utf-8")
    for name in FILES:
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / name, target)
    shutil.copyfile(root / "others/deploy/cloud/Dockerfile.control", destination / "Dockerfile")
    shutil.copytree(root / "others/licenses/cloud-controller", destination / "licenses", dirs_exist_ok=True)
    return {p.relative_to(destination).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(destination.rglob("*")) if p.is_file()}


def build(root, target, sha):
    files = context(root, target / "controller-context")
    image = "labconnect-control:" + sha[:12]
    subprocess.run(["docker", "build", "--platform", "linux/amd64", "--build-arg", "SOURCE_SHA=" + sha,
                    "-t", image, str(target / "controller-context")], check=True)
    identifier = subprocess.check_output(["docker", "image", "inspect", "--format", "{{.Id}}", image], text=True).strip()
    result = {"source_sha": sha, "image": image, "image_id": identifier, "source_files": files,
              "docker_cli_version": "29.9.2", "standard_library_only": True}
    (target / "controller-image.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result
