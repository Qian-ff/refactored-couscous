"""Archive licenses for A0's new Python dependencies from their locked installed wheels."""
from email.parser import Parser
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request

ROOT = Path(__file__).resolve().parents[2]


def main():
    records = []
    for environment, package, version in (("backend", "cryptography", "50.0.2"),
                                          ("ai_worker", "sherpa_onnx", "1.13.8"),
                                          ("ai_worker", "sherpa_onnx_core", "1.13.8"),
                                          ("ai_worker", "numpy", "2.4.4")):
        installed = ROOT / f"others/{environment}/.venv/Lib/site-packages/{package}-{version}.dist-info"
        metadata = Parser().parsestr((installed / "METADATA").read_text(encoding="utf-8"))
        files = [p for p in installed.rglob("*") if p.is_file()
                 and any(word in p.name.lower() for word in ("license", "notice", "copying"))]
        fallback = package == "sherpa_onnx_core" and not files
        if fallback:
            # The core wheel declares Apache-2.0 but omits the text; its matching main wheel retains it.
            installed = ROOT / f"others/ai_worker/.venv/Lib/site-packages/sherpa_onnx-{version}.dist-info"
            files = [installed / "licenses/LICENSE"]
        if not files or any(not p.is_file() for p in files):
            raise RuntimeError("Installed license missing: " + package)
        output = ROOT / f"others/licenses/python/{package}-{version}"
        for source in files:
            target = output / source.relative_to(installed)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        records.append({"package":metadata["Name"], "version":metadata["Version"],
                        "source":f"https://pypi.org/project/{metadata['Name']}/{version}/",
                        "license_expression":metadata.get("License-Expression") or metadata.get("License"),
                        "license_origin":"matching sherpa-onnx upstream/main wheel" if fallback else "installed wheel",
                        "project_urls":metadata.get_all("Project-URL", []),
                        "files":[p.relative_to(installed).as_posix() for p in files]})
    native = ROOT / "others/licenses/onnxruntime-1.28.2"
    native.mkdir(parents=True, exist_ok=True)
    sources = {}
    for name in ("LICENSE", "ThirdPartyNotices.txt"):
        url = f"https://raw.githubusercontent.com/microsoft/onnxruntime/v1.28.2/{name}"
        target = native / name
        if not target.exists():
            with urllib.request.urlopen(url, timeout=45) as response:
                target.write_bytes(response.read())
        sources[name] = {"url":url,"sha256":hashlib.sha256(target.read_bytes()).hexdigest()}
    (native / "sources.json").write_text(json.dumps(sources, indent=2) + "\n", encoding="utf-8")
    (ROOT / "others/licenses/python-a0.json").write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    print(f"Archived licenses for {len(records)} locked Python distributions and bundled ONNX Runtime 1.28.2")


if __name__ == "__main__":
    main()
