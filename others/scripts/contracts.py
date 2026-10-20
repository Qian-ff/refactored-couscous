"""Export real FastAPI schemas and generate/check the shared TypeScript client."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "others/backend"
PYTHON = BACKEND / (".venv/Scripts/python.exe" if os.name == "nt" else ".venv/bin/python")
SCHEMA = ROOT / "others/contracts/openapi.json"


def export_schema() -> str:
    process = subprocess.run([str(PYTHON), "-c", "import json; from app.main import app; print(json.dumps(app.openapi(), ensure_ascii=True))"],
                             cwd=BACKEND, capture_output=True, text=True, encoding="utf-8", check=True)
    return json.dumps(json.loads(process.stdout), ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def generate_client(output: Path | None = None):
    package = ROOT / "node_modules/@hey-api/openapi-ts"
    metadata = json.loads((package / "package.json").read_text(encoding="utf-8"))
    entry = metadata["bin"]
    if isinstance(entry, dict):
        entry = entry["openapi-ts"]
    command = [shutil.which("node") or "node", str(package / entry)]
    if output:
        command += ["--output", str(output)]
    subprocess.run(command, cwd=ROOT / "web", check=True)
    # Normalize generator whitespace consistently for both export and verification.
    for file in (output or ROOT / "web/src/client").rglob("*.ts"):
        content = "\n".join(line.rstrip() for line in file.read_text(encoding="utf-8").splitlines()).rstrip() + "\n"
        file.write_text(content, encoding="utf-8", newline="\n")


def source_files(path: Path) -> dict[str, bytes]:
    return {file.relative_to(path).as_posix(): file.read_bytes() for file in path.rglob("*.ts")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["generate", "check"])
    mode = parser.parse_args().mode
    schema = export_schema()
    release = json.loads((ROOT / "others/config/application.json").read_text(encoding="utf-8"))["version"]
    version = {"version": release, "status": "implemented", "openapi_sha256": hashlib.sha256(schema.encode("utf-8")).hexdigest()}
    if mode == "generate":
        SCHEMA.write_text(schema, encoding="utf-8", newline="\n")
        (SCHEMA.parent / "version.json").write_text(json.dumps(version, indent=2) + "\n", encoding="utf-8")
        generate_client()
        print("Exported implemented OpenAPI and generated shared client")
    else:
        if not SCHEMA.is_file() or SCHEMA.read_text(encoding="utf-8") != schema:
            raise SystemExit("OpenAPI differs from implemented routes; run pnpm generate-client")
        if json.loads((SCHEMA.parent / "version.json").read_text()) != version:
            raise SystemExit("Contract version/hash differs")
        temp_root = ROOT / "others/.tmp"
        temp_root.mkdir(exist_ok=True, parents=True)
        with tempfile.TemporaryDirectory(prefix="client-check-", dir=temp_root) as temporary:
            target = Path(temporary).resolve()
            assert target.is_relative_to(temp_root.resolve()) and target != temp_root.resolve()
            generate_client(target)
            if source_files(target) != source_files(ROOT / "web/src/client"):
                raise SystemExit("Generated client differs; run pnpm generate-client")
        print("PASS: implemented OpenAPI, version hash and generated client agree")


if __name__ == "__main__":
    main()
