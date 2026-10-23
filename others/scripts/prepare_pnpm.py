"""Restore the pinned pnpm in the primary checkout cache, without a global install."""
import argparse
import base64
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import tempfile
from urllib.request import urlopen

from workflow import primary_root

ROOT = Path(__file__).resolve().parents[2]


def digest(path, algorithm="sha256"):
    result = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.digest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify the existing shared cache without network access")
    args = parser.parse_args()
    primary = primary_root(ROOT).resolve()
    pin = json.loads((primary / "others/config/toolchain.json").read_text(encoding="utf-8"))["pnpm"]
    manager = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["packageManager"]
    if manager != "pnpm@" + pin["version"]:
        raise RuntimeError("Project packageManager differs from A's pinned toolchain")
    target = (primary / "others/cache/tools/pnpm" / pin["version"]).resolve()
    if not target.is_relative_to(primary / "others/cache/tools"):
        raise RuntimeError("Tool cache resolved outside the project cache")
    manifest = target / "installed.json"
    if target.exists():
        if not manifest.is_file():
            raise RuntimeError("Existing tool cache is incomplete; it was preserved")
        installed = json.loads(manifest.read_text(encoding="utf-8"))
        if installed["integrity"] != pin["integrity"]:
            raise RuntimeError("Existing pnpm integrity record differs; cache preserved")
        for name, expected in installed["files"].items():
            path = (target / name).resolve()
            if not path.is_relative_to(target) or digest(path).hex() != expected:
                raise RuntimeError("Installed pnpm file verification failed")
        print(f"Verified project pnpm {pin['version']}: {target}")
        return
    if args.check:
        raise RuntimeError("Pinned pnpm cache is missing; A must run prepare_pnpm.py")
    if ROOT.resolve() != primary:
        raise RuntimeError("Only A's primary checkout may install the shared pnpm tool")
    downloads = primary / "others/cache/downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    archive = downloads / f"pnpm-{pin['version']}.tgz"
    if not archive.exists():
        with tempfile.NamedTemporaryFile(dir=downloads, prefix="pnpm-", suffix=".part", delete=False) as temporary:
            partial = Path(temporary.name).resolve()
            if not partial.is_relative_to(downloads.resolve()):
                raise RuntimeError("Download target resolved outside the project cache")
            with urlopen(pin["url"], timeout=30) as response:
                shutil.copyfileobj(response, temporary)
        expected = pin["integrity"].removeprefix("sha512-")
        if base64.b64encode(digest(partial, "sha512")).decode() != expected:
            raise RuntimeError("Downloaded pnpm integrity differs; partial download preserved")
        partial.rename(archive)
    if "sha512-" + base64.b64encode(digest(archive, "sha512")).decode() != pin["integrity"]:
        raise RuntimeError("Cached pnpm archive integrity differs; archive preserved")
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="pnpm-staging-", dir=target.parent)).resolve()
    if not staging.is_relative_to(primary / "others/cache/tools"):
        raise RuntimeError("Staging path resolved outside the project cache")
    with tarfile.open(archive, "r:gz") as bundle:
        for member in bundle.getmembers():
            parts = PurePosixPath(member.name).parts
            destination = (staging / member.name).resolve()
            if (not parts or parts[0] != "package" or ".." in parts or "\\" in member.name
                    or not destination.is_relative_to(staging) or not (member.isfile() or member.isdir())):
                raise RuntimeError("Unexpected package member; staging preserved")
        bundle.extractall(staging)  # All member paths and types were checked; links are rejected.
    package = json.loads((staging / "package/package.json").read_text(encoding="utf-8"))
    if package["version"] != pin["version"] or not (staging / "package/bin/pnpm.cjs").is_file():
        raise RuntimeError("Archive does not contain the pinned pnpm CLI")
    (staging / "pnpm.cmd").write_bytes(b'@echo off\r\nnode "%~dp0package\\bin\\pnpm.cjs" %*\r\nexit /b %errorlevel%\r\n')
    files = {path.relative_to(staging).as_posix(): digest(path).hex() for path in staging.rglob("*") if path.is_file()}
    (staging / "installed.json").write_text(json.dumps({"version": pin["version"], "integrity": pin["integrity"],
        "source": pin["url"], "files": files}, indent=2) + "\n", encoding="utf-8")
    staging.rename(target)
    print(f"Installed project pnpm {pin['version']}: {target}")
    print("Dot-source others/scripts/Use-ProjectEnvironment.ps1 in the current shell")


if __name__ == "__main__":
    main()
