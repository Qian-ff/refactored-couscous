"""Download only the pinned speech artifact, archive its license evidence and run a CPU smoke test."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[2]


def main():
    model = json.loads((ROOT / "others/ai_worker/models.lock.json").read_text())["paraformer"]
    base = f"https://huggingface.co/{model['repository']}/resolve/{model['revision']}/"
    directory = ROOT / "others/models/paraformer-2023-09-14"
    directory.mkdir(parents=True, exist_ok=True)
    files = ["model.int8.onnx", "tokens.txt", "README.md", "download-model.py", "test_wavs/0.wav"]
    evidence = {"repository": model["repository"], "revision": model["revision"], "license": model["license"], "files": {}}
    for name in files:
        destination = directory / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        expected = model["files"].get(name)
        if not destination.exists() or (expected and hashlib.sha256(destination.read_bytes()).hexdigest() != expected):
            partial = destination.with_suffix(destination.suffix + ".partial")
            subprocess.run(["curl.exe", "--fail", "--location", "--silent", "--show-error", "--retry", "2", "--retry-all-errors",
                            "--connect-timeout", "20", "--max-time", "600", "--speed-limit", "1024", "--speed-time", "45",
                            "--continue-at", "-", "--output", str(partial), base + name], check=True)
            if expected and hashlib.sha256(partial.read_bytes()).hexdigest() != expected:
                raise RuntimeError("Downloaded model hash does not match pinned source")
            partial.replace(destination)
        evidence["files"][name] = hashlib.sha256(destination.read_bytes()).hexdigest()
        print("Verified " + name, flush=True)
    license_file = directory / "Apache-2.0.txt"
    if not license_file.exists():
        with urllib.request.urlopen("https://www.apache.org/licenses/LICENSE-2.0.txt", timeout=30) as response:
            license_file.write_bytes(response.read())
    if "apache-2.0" not in (directory / "README.md").read_text().lower():
        raise RuntimeError("Pinned model publisher license declaration missing")
    evidence["files"][license_file.name] = hashlib.sha256(license_file.read_bytes()).hexdigest()
    (directory / "source-and-license.json").write_text(json.dumps(evidence, indent=2) + "\n")
    archive = ROOT / "others/licenses/paraformer"
    archive.mkdir(parents=True, exist_ok=True)
    for name in ("README.md", "Apache-2.0.txt", "source-and-license.json"):
        (archive / name).write_bytes((directory / name).read_bytes())
    interpreter = ROOT / "others/ai_worker/.venv/Scripts/python.exe"
    code = r'''
import ctypes, json, os, sys, time, wave
from pathlib import Path
import numpy as np
import sherpa_onnx
root = Path(sys.argv[1])
with wave.open(str(root / "test_wavs/0.wav")) as audio:
    assert audio.getnchannels() == 1 and audio.getsampwidth() == 2
    rate = audio.getframerate()
    samples = np.frombuffer(audio.readframes(audio.getnframes()), dtype=np.int16).astype(np.float32) / 32768
started = time.perf_counter()
recognizer = sherpa_onnx.OfflineRecognizer.from_paraformer(
    paraformer=str(root / "model.int8.onnx"), tokens=str(root / "tokens.txt"),
    num_threads=2, sample_rate=16000, feature_dim=80, decoding_method="greedy_search", provider="cpu")
stream = recognizer.create_stream()
stream.accept_waveform(rate, samples)
recognizer.decode_stream(stream)
text = stream.result.text
assert len(text.strip()) > 3 and any("\u4e00" <= c <= "\u9fff" for c in text)
runtime = sherpa_onnx.onnxruntime_version
runtime = runtime() if callable(runtime) else runtime
library = None
if os.name == "nt":
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
    kernel.GetModuleHandleW.restype = ctypes.c_void_p
    kernel.GetModuleFileNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint]
    buffer = ctypes.create_unicode_buffer(32768)
    handle = kernel.GetModuleHandleW("onnxruntime.dll")
    assert handle and kernel.GetModuleFileNameW(handle, buffer, len(buffer))
    loaded = Path(buffer.value).resolve()
    assert loaded.is_relative_to(Path(sys.prefix).resolve()), "ASR loaded a runtime outside the project worker"
    library = loaded.relative_to(Path(sys.prefix).resolve()).as_posix()
print(json.dumps({"status":"passed", "provider":"cpu", "sample_rate":rate,
    "duration_seconds":len(samples)/rate,"elapsed_seconds":round(time.perf_counter()-started,3),
    "onnxruntime":runtime,"runtime_library":library,"recognized_text":text}, ensure_ascii=True))
'''
    result = subprocess.run([str(interpreter), "-X", "faulthandler", "-c", code, str(directory)], capture_output=True, text=True)
    if result.returncode:
        sys.stderr.write(result.stderr)
        raise RuntimeError("CPU speech verification failed, exit code " + str(result.returncode))
    report = ROOT / "others/reports/a0/speech.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(result.stdout, encoding="utf-8")
    print(result.stdout.strip())


if __name__ == "__main__":
    main()
