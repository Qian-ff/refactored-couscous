"""Read-only local tool probes; only writes an optional report explicitly requested by the caller."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import locale
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def probe(args: list[str], timeout: int = 10) -> dict:
    try:
        result = subprocess.run(
            args, capture_output=True, text=True, encoding=locale.getpreferredencoding(False), errors="replace",
            timeout=timeout, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        text = (result.stdout + result.stderr).strip()
        return {"status": "ok" if result.returncode == 0 else "warning",
                "exit_code": result.returncode, "detail": text[:2000]}
    except subprocess.TimeoutExpired:
        return {"status": "warning", "detail": f"Probe timed out after {timeout}s; no installation attempted"}
    except OSError as error:
        return {"status": "missing", "detail": str(error)}


def command(name: str, *args: str) -> dict:
    path = shutil.which(name)
    if not path:
        return {"status": "missing", "detail": "Not on PATH; custom installation may still exist"}
    if Path(path).suffix.lower() in (".cmd", ".bat"):
        # Fixed --version arguments only; no user data or credentials enter a shell.
        if tuple(args) != ("--version",):
            return {"status": "unverified", "detail": "Batch probe is restricted to --version"}
        powershell = shutil.which("pwsh") or str(Path(os.environ.get("SYSTEMROOT", "C:/Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe")
        quoted_path = "'" + path.replace("'", "''") + "'"
        result = probe([powershell, "-NoProfile", "-NonInteractive", "-Command", "& " + quoted_path + " --version"])
    else:
        result = probe([path, *args])
    return {"path": path, **result}


def local_config() -> dict:
    path = ROOT / "others/config/local.json"
    if not path.exists():
        common = probe(["git", "-C", str(ROOT), "rev-parse", "--path-format=absolute", "--git-common-dir"])
        if common["status"] == "ok":
            path = Path(common["detail"].strip()).parent / "others/config/local.json"
    return json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {}


def android_sdk(config: dict) -> dict:
    candidates = [config.get("android_sdk_root"), os.environ.get("ANDROID_SDK_ROOT"),
                  os.environ.get("ANDROID_HOME")]
    home = Path.home()
    appdata = Path(os.environ.get("APPDATA", str(home / "AppData/Roaming")))
    settings = [
        home / ".flutter_settings", home / ".config/flutter/settings",
        appdata / ".flutter_settings", appdata / "flutter/settings",
    ]
    for file in settings:
        if file.is_file():
            try:
                value = json.loads(file.read_text(encoding="utf-8-sig")).get("android-sdk")
                candidates.append(value)
            except (OSError, ValueError):
                pass
    candidates.append(str(Path(os.environ.get("LOCALAPPDATA", str(home / "AppData/Local"))) / "Android/Sdk"))
    for value in candidates:
        if value:
            path = Path(value).expanduser()
            if (path / "platform-tools/adb.exe").is_file() or (path / "platform-tools/adb").is_file():
                return {
                    "status": "ok", "path": str(path),
                    "platforms": sorted(p.name for p in (path / "platforms").glob("*") if p.is_dir()),
                    "build_tools": sorted(p.name for p in (path / "build-tools").glob("*") if p.is_dir()),
                    "note": "Files only; no SDK install, license acceptance or APK build performed",
                }
    return {"status": "unverified", "detail": "Not found in selected environment/settings paths; set android_sdk_root in local.json if installed"}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    config = local_config()
    tools = {
        "git": command("git", "--version"),
        "node": command("node", "--version"),
        "pnpm": command("pnpm", "--version"),
        "python": {"status": "ok", "path": sys.executable, "detail": platform.python_version()},
        "python_installations": command("py", "-0p") if os.name == "nt" else {"status": "unverified"},
        "docker_client": command("docker", "--version"),
        "docker_engine": command("docker", "version", "--format", "{{.Server.Version}}"),
    }
    javac = shutil.which("javac")
    java_home = config.get("java_home") or os.environ.get("JAVA_HOME") or (str(Path(javac).parent.parent) if javac else None)
    java = Path(java_home) / "bin" / ("java.exe" if os.name == "nt" else "java") if java_home else None
    tools["jdk"] = {"path": str(java), **probe([str(java), "-version"])} if java and java.exists() else {"status": "unverified", "detail": "Set java_home in local.json"}
    tools["android_sdk"] = android_sdk(config)
    gpu = shutil.which("nvidia-smi")
    tools["gpu"] = probe([gpu, "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"]) if gpu else {"status": "unverified", "detail": "nvidia-smi not on PATH"}
    if config.get("worker_python"):
        tools["worker_python"] = probe([config["worker_python"], "--version"])
    else:
        tools["worker_python"] = {"status": "not_configured", "detail": "Select and lock the worker environment during framework integration"}
    report = {
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "phase": "preparation",
        "tools": tools,
        "boundaries": [
            "No package/model download or installation",
            "No framework, database or app startup",
            "No camera/microphone capture",
            "Warnings do not establish absence of all custom installations",
        ],
    }
    for name, data in tools.items():
        detail = str(data.get("detail", data.get("path", ""))).splitlines()
        print(f"{name}: {data['status']} - {detail[0] if detail else ''}")
    if args.report:
        target = args.report.resolve()
        allowed = (ROOT / "others/reports").resolve()
        if not target.is_relative_to(allowed):
            parser.error("Reports must stay in the ignored others/reports directory")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("Report: " + str(target))
    return 0 if all(tools[name]["status"] == "ok" for name in ("git", "node", "python")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
