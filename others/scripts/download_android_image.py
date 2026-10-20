"""Resume the one official A1 emulator image, verify its repository checksum, then assemble."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "others/cache/downloads"
OUTPUT = CACHE / "android-api36-googleapis-x86_64-r07.zip"
PARTS = CACHE / "android-api36-parts"
PACKAGE = "system-images;android-36;google_apis;x86_64"


def digest(path: Path) -> str:
    value = hashlib.sha1()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main():
    metadata = subprocess.run(["curl.exe", "--fail", "--location", "--silent", "--show-error", "--max-time", "45",
        "https://dl.google.com/android/repository/sys-img/google_apis/sys-img2-3.xml"], capture_output=True, check=True).stdout
    document = ET.fromstring(metadata)
    local = lambda node: node.tag.rsplit("}", 1)[-1]
    package = next(node for node in document.iter() if local(node) == "remotePackage" and node.attrib.get("path") == PACKAGE)
    complete = next(node for node in package.iter() if local(node) == "complete")
    values = {local(node): node.text for node in complete}
    # This A1 image is pinned, even if the repository later publishes a revision.
    if values["url"] != "x86_64-36_r07.zip" or values["checksum"] != "c6bf44bdcd885bb902b4ba752d111a073ad7a817":
        raise SystemExit("Official image revision changed; review and pin the new metadata before downloading")
    size = int(values["size"])
    checksum = values["checksum"]
    url = "https://dl.google.com/android/repository/sys-img/google_apis/" + values["url"]
    if OUTPUT.exists() and OUTPUT.stat().st_size == size and digest(OUTPUT) == checksum:
        print("PASS: official emulator archive already complete and verified", flush=True)
        return
    PARTS.mkdir(parents=True, exist_ok=True)
    step = (size + 3) // 4
    # Preserve a previous single-connection download's prefix rather than start over.
    if OUTPUT.exists() and not any(PARTS.glob("*.part")):
        with OUTPUT.open("rb") as source:
            for index in range(4):
                remaining = min(step, size - index * step)
                if remaining <= 0:
                    break
                first = source.read(min(1024 * 1024, remaining))
                if not first:
                    break
                with (PARTS / f"{index}.part").open("wb") as destination:
                    destination.write(first)
                    remaining -= len(first)
                    while remaining:
                        block = source.read(min(1024 * 1024, remaining))
                        if not block:
                            break
                        destination.write(block)
                        remaining -= len(block)

    def download(index: int):
        part = PARTS / f"{index}.part"
        expected = min(step, size - index * step)
        for attempt in range(6):
            existing = part.stat().st_size if part.exists() else 0
            if existing == expected:
                print(f"Segment {index + 1}/4 complete", flush=True)
                return part
            if existing > expected:
                raise RuntimeError("Oversized cached segment; preserve it for inspection")
            pending = PARTS / f"{index}.pending"
            result = subprocess.run(["curl.exe", "--fail", "--location", "--silent", "--show-error",
                "--connect-timeout", "20", "--max-time", "600", "--range",
                f"{index * step + existing}-{index * step + expected - 1}", "--output", str(pending),
                "--write-out", "%{http_code}", url], capture_output=True, text=True)
            if result.stdout.strip() != "206":
                raise RuntimeError(f"Official range request returned {result.stdout.strip()}; existing data preserved")
            received = pending.stat().st_size if pending.exists() else 0
            if not 0 < received <= expected - existing:
                raise RuntimeError("Invalid range response length")
            with part.open("ab") as destination, pending.open("rb") as source:
                shutil.copyfileobj(source, destination, 1024 * 1024)
            print(f"Segment {index + 1}/4: {existing + received}/{expected} bytes retained", flush=True)
        raise RuntimeError("Retry limit reached; rerun to resume preserved segments")

    with ThreadPoolExecutor(max_workers=4) as workers:
        paths = list(workers.map(download, range(4)))
    assembled = CACHE / "android-api36.assembled.zip"
    with assembled.open("wb") as destination:
        for path in paths:
            with path.open("rb") as source:
                shutil.copyfileobj(source, destination, 1024 * 1024)
    if assembled.stat().st_size != size or digest(assembled) != checksum:
        raise SystemExit("Image checksum failed; preserved segments for inspection")
    assembled.replace(OUTPUT)
    print("PASS: official API36 r07 image complete; repository SHA1 verified", flush=True)


if __name__ == "__main__":
    main()
