"""Project-scoped ECS transport, immutable release bundles and production deployment."""
import argparse
import gzip
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import runpy
import secrets
import shlex
import shutil
import subprocess
import tarfile
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "others/runtime/cloud-ecs"
CLOUD = ROOT / "others/deploy/cloud"
ACCESS = RUNTIME / "access"
REMOTE_ROOT = "/opt/labconnect"
CLIENT_ORIGINS = ["http://127.0.0.1:48621", "https://localhost", "http://localhost", "capacitor://localhost"]
CLIENT_ORIGINS += [f"http://{host}:{port}" for host in ("127.0.0.1", "localhost") for port in range(5173, 5177)]


def run(args, **kwargs):
    return subprocess.run([str(a) for a in args], check=True, **kwargs)


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True, encoding="utf-8").strip()


def connection():
    value = json.loads((ACCESS / "connection.json").read_text(encoding="utf-8"))
    ipaddress.IPv4Address(value["host"])
    if not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", value["user"]):
        raise ValueError("Invalid SSH username")
    output = subprocess.check_output(["ssh-keygen", "-lf", str(ACCESS / "known_hosts")], text=True)
    if value["host_fingerprint"] not in output.split():
        raise ValueError("The project known_hosts file does not match the verified host fingerprint")
    return value


def transport_options():
    return ["-F", "NUL" if os.name == "nt" else "/dev/null", "-i", str(ACCESS / "id_ed25519"),
            "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
            "-o", "UserKnownHostsFile=" + str(ACCESS / "known_hosts"),
            "-o", "GlobalKnownHostsFile=" + ("NUL" if os.name == "nt" else "/dev/null"),
            "-o", "ConnectTimeout=15", "-o", "ServerAliveInterval=15"]


def remote(script, *args, capture=False):
    value = connection()
    command = "bash -s -- " + " ".join(shlex.quote(str(a)) for a in args)
    # Binary input is deliberate: Windows text mode would turn LF into CRLF in bash scripts.
    return run(["ssh", *transport_options(), "-p", str(value.get("port", 22)),
                value["user"] + "@" + value["host"], command],
               input=script.replace("\r\n", "\n").encode("utf-8"), capture_output=capture)


def upload(path, target):
    value = connection()
    if not target.startswith(REMOTE_ROOT + "/"):
        raise ValueError("Upload target must be inside /opt/labconnect")
    run(["scp", *transport_options(), "-P", str(value.get("port", 22)), str(path),
         value["user"] + "@" + value["host"] + ":" + target])


def prepare(public_host=None):
    value = connection()
    host = public_host or value["host"]
    if not re.fullmatch(r"[a-zA-Z0-9.-]+", host):
        raise ValueError("PUBLIC_HOST must be an IP address or DNS hostname")
    folder = RUNTIME / "secrets"
    folder.mkdir(parents=True, exist_ok=True)
    expected = ["api.env", "db.env", "bootstrap.env", "cloud.env", "ai-master.key", "accounts.json"]
    if any((folder / name).exists() for name in expected):
        if not all((folder / name).is_file() for name in expected):
            raise ValueError("Partial secrets exist; preserve them and investigate instead of rotating silently")
        print("Existing cloud secrets preserved. No passwords or master keys were reset.")
        return
    db_password, admin_password = secrets.token_urlsafe(36), secrets.token_urlsafe(36)
    cors = ["https://" + host, *CLIENT_ORIGINS]
    values = {
        "db.env": f"POSTGRES_USER=labconnect\nPOSTGRES_DB=labconnect\nPOSTGRES_PASSWORD={db_password}\n",
        "api.env": "APP_ENV=production\nSECRET_KEY=" + secrets.token_urlsafe(48)
        + f"\nDATABASE_URL=postgresql+psycopg://labconnect:{db_password}@db:5432/labconnect\n"
        + "CORS_ORIGINS=" + ",".join(cors) + "\n",
        "bootstrap.env": f"LABCONNECT_BOOTSTRAP_USERNAME=labadmin\nLABCONNECT_BOOTSTRAP_PASSWORD={admin_password}\n",
        "cloud.env": f"PUBLIC_HOST={host}\n",
        "accounts.json": json.dumps({"service_url": "https://" + host, "school_code": "platform",
                                     "username": "labadmin", "initial_password": admin_password,
                                     "must_change_password": True}, indent=2) + "\n",
    }
    for name, content in values.items():
        (folder / name).write_text(content, encoding="utf-8", newline="\n")
    (folder / "ai-master.key").write_bytes(secrets.token_bytes(32))
    if os.name == "nt":
        username = os.environ["USERNAME"]
        run(["icacls", str(folder), "/inheritance:r", "/grant:r", f"{username}:(OI)(CI)F"],
            stdout=subprocess.DEVNULL)
    else:
        folder.chmod(0o700)
        for name in expected:
            (folder / name).chmod(0o600)
    print("Generated separate cloud secrets in the ignored project runtime directory; credentials not printed.")


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest() if hasattr(hashlib, "file_digest") else _digest(stream)


def _digest(stream):
    result = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        result.update(chunk)
    return result.hexdigest()


def build():
    if git("branch", "--show-current") != "main" or git("status", "--porcelain"):
        raise ValueError("Release bundles require clean, committed A/main source")
    sha = git("rev-parse", "HEAD")
    target = RUNTIME / "releases" / sha
    bundle = target / "bundle.tar"
    if bundle.is_file():
        print(str(bundle))
        return
    target.mkdir(parents=True, exist_ok=True)
    lock = json.loads((CLOUD / "images.lock.json").read_text(encoding="utf-8"))
    if "FROM " + lock["python"] not in (ROOT / "others/backend/Dockerfile").read_text(encoding="utf-8"):
        raise ValueError("Backend base image differs from images.lock.json")
    if "FROM " + lock["caddy"] not in (CLOUD / "Dockerfile.web").read_text(encoding="utf-8"):
        raise ValueError("Web base image differs from images.lock.json")
    pnpm = shutil.which("pnpm.cmd" if os.name == "nt" else "pnpm")
    if pnpm is None:
        raise ValueError("Use the existing project pnpm environment before building")
    run([pnpm, "run", "build:web"], cwd=ROOT)
    web_context = target / "web-context"
    shutil.copytree(ROOT / "web/dist", web_context / "dist", dirs_exist_ok=True)
    shutil.copy2(CLOUD / "Caddyfile", web_context / "Caddyfile")
    shutil.copy2(CLOUD / "Dockerfile.web", web_context / "Dockerfile")
    api_image, web_image = "labconnect-api:" + sha[:12], "labconnect-web:" + sha[:12]
    run(["docker", "build", "--build-arg", "SOURCE_SHA=" + sha, "-f", ROOT / "others/backend/Dockerfile",
         "-t", api_image, ROOT])
    run(["docker", "build", "--build-arg", "SOURCE_SHA=" + sha, "-t", web_image, web_context])
    identify = runpy.run_path(str(ROOT / "others/backend/app/core/provenance.py"))["identity"]
    manifest = {"source_sha": sha, "contract": identify(ROOT, "api")["contract"],
                "api_fingerprint": identify(ROOT, "api")["source_fingerprint"],
                "web_fingerprint": identify(ROOT, "web")["source_fingerprint"], "base_images": lock,
                "api_image": api_image, "web_image": web_image, "image_ids": {}}
    for label, image in (("api", api_image), ("web", web_image), ("postgres", lock["postgres"])):
        manifest["image_ids"][label] = subprocess.check_output(
            ["docker", "image", "inspect", "--format", "{{.Id}}", image], text=True).strip()
    with gzip.open(target / "images.tar.gz", "wb", compresslevel=3) as output:
        process = subprocess.Popen(["docker", "save", api_image, web_image, lock["postgres"]], stdout=subprocess.PIPE)
        try:
            shutil.copyfileobj(process.stdout, output, length=1024 * 1024)
        finally:
            process.stdout.close()
        if process.wait() != 0:
            raise RuntimeError("Docker image export failed")
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    (target / "release.env").write_text(
        f"API_IMAGE={api_image}\nWEB_IMAGE={web_image}\nPOSTGRES_IMAGE={manifest['image_ids']['postgres']}\n",
        encoding="ascii", newline="\n")
    for name in ("compose.yml", "release.sh", "asr-session.py"):
        shutil.copy2(CLOUD / name, target / name)
    names = ["images.tar.gz", "manifest.json", "release.env", "compose.yml", "release.sh", "asr-session.py"]
    (target / "SHA256SUMS").write_text("".join(digest(target / name) + "  " + name + "\n" for name in names),
                                      encoding="ascii", newline="\n")
    for name in ("release.env", "release.sh", "SHA256SUMS"):
        if b"\r" in (target / name).read_bytes():
            raise ValueError("Linux release control files must use LF: " + name)
    with tarfile.open(bundle, "w") as archive:
        for name in [*names, "SHA256SUMS"]:
            archive.add(target / name, arcname=name)
    print(str(bundle))


def deploy(bundle):
    with tarfile.open(bundle) as archive:
        expected = {"images.tar.gz", "manifest.json", "release.env", "compose.yml", "release.sh", "SHA256SUMS"}
        if "asr-session.py" in archive.getnames():
            expected.add("asr-session.py")
        if set(archive.getnames()) != expected or any(not item.isfile() for item in archive):
            raise ValueError("Unexpected release archive contents")
        manifest = json.load(archive.extractfile("manifest.json"))
        sums = archive.extractfile("SHA256SUMS").read().decode("ascii").splitlines()
        if len(sums) != len(expected) - 1 or {line.split("  ", 1)[-1] for line in sums} != expected - {"SHA256SUMS"}:
            raise ValueError("Incomplete release checksums")
        for line in sums:
            wanted, name = line.split("  ", 1)
            if name not in expected - {"SHA256SUMS"} or _digest(archive.extractfile(name)) != wanted:
                raise ValueError("Release checksum mismatch")
    sha = manifest["source_sha"]
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Invalid source SHA")
    run(["git", "-C", ROOT, "merge-base", "--is-ancestor", sha, "main"])
    remote("set -eu\numask 077\nmkdir -p /opt/labconnect/shared /opt/labconnect/incoming /opt/labconnect/releases\n")
    folder = RUNTIME / "secrets"
    result = remote("set -eu\ncount=0\nfor name in api.env db.env bootstrap.env cloud.env ai-master.key; do\n"
                    "  if test -f /opt/labconnect/shared/$name; then count=$((count+1)); fi\ndone\n"
                    "if test $count -eq 0; then echo empty; elif test $count -eq 5; then echo configured; else echo partial; fi\n",
                    capture=True)
    if result.stdout.strip() == b"partial":
        raise ValueError("Partial server secrets detected; preserve them and complete configuration before retrying")
    if result.stdout.strip() == b"empty":
        for name in ("api.env", "db.env", "bootstrap.env", "cloud.env", "ai-master.key"):
            upload(folder / name, REMOTE_ROOT + "/shared/" + name)
        remote("set -eu\nchmod 700 /opt/labconnect/shared\nchmod 600 /opt/labconnect/shared/*\n"
               "chown 10001:10001 /opt/labconnect/shared/ai-master.key\nchmod 400 /opt/labconnect/shared/ai-master.key\n")
    else:
        print("Existing server secrets preserved.")
    remote("set -eu\nmkdir -p /opt/labconnect/shared/asr /opt/labconnect/shared/ai\n"
           "chown 10001:10001 /opt/labconnect/shared/asr /opt/labconnect/shared/ai\n"
           "chmod 700 /opt/labconnect/shared/asr /opt/labconnect/shared/ai\n")
    target = REMOTE_ROOT + "/incoming/" + sha + ".tar"
    upload(bundle, target)
    remote("set -euo pipefail\nsha=$1\ndigest=$2\nroot=/opt/labconnect\n"
           "echo \"$digest  $root/incoming/$sha.tar\" | sha256sum --check\n"
           "mkdir -p \"$root/releases/$sha\"\n"
           "tar -xf \"$root/incoming/$sha.tar\" -C \"$root/releases/$sha\"\n"
           "bash \"$root/releases/$sha/release.sh\" apply \"$sha\"\n", sha, digest(bundle))


def verify(url):
    target = urllib.parse.urlsplit(url)
    configured = dict(line.split("=", 1) for line in (RUNTIME / "secrets/cloud.env").read_text().splitlines() if "=" in line)
    if (target.scheme != "https" or target.hostname not in {connection()["host"], configured.get("PUBLIC_HOST")}
            or target.username or target.password or target.query or target.fragment or target.path not in {"", "/"}
            or target.port not in {None, 443}):
        raise ValueError("Verification requires this project's configured public HTTPS gateway")
    health = json.load(urllib.request.urlopen(url.rstrip("/") + "/api/v1/health", timeout=15))
    info = json.load(urllib.request.urlopen(url.rstrip("/") + "/build-info.json", timeout=15))
    if health.get("status") != "ok" or health.get("contract") != info.get("contract"):
        raise ValueError("Cloud health and client contract do not match")
    remote("""set -eu
umask 077
python3 - "$1" <<'PY'
from datetime import datetime, timezone
import json, os, subprocess, sys
from pathlib import Path
root=Path('/opt/labconnect')
manifest=json.loads((root/'current/manifest.json').read_text())
sha=sys.argv[1]
if manifest['source_sha'] != sha:
    raise SystemExit('HTTPS client does not match the current server release')
for name in ['labconnect-cloud-api-1','labconnect-cloud-web-1']:
    revision=subprocess.check_output(['docker','inspect','--format','{{index .Config.Labels "org.opencontainers.image.revision"}}',name],text=True).strip()
    if revision != sha: raise SystemExit('Container source version mismatch')
actual=subprocess.check_output(['docker','exec','labconnect-cloud-api-1','.venv/bin/python','-c','import os; print(os.environ["LABCONNECT_SOURCE_SHA"])'],text=True).strip()
if actual != sha: raise SystemExit('Running API source version mismatch')
value={'source_sha':sha,'status':'trusted_https_verified','verified_at':datetime.now(timezone.utc).isoformat()}
temporary=root/'deployment.pending.json'
temporary.write_text(json.dumps(value)+'\\n')
os.replace(temporary,root/'deployment.json')
print('Verified trusted HTTPS, running API and both container source versions.')
PY
""", info["source_sha"])
    print(json.dumps({"health": health, "web": info}, ensure_ascii=True))


def sync_cors():
    """Update only CORS for the known clients; keep every credential and data volume unchanged."""
    path = RUNTIME / "secrets/api.env"
    lines = path.read_text(encoding="utf-8").splitlines()
    existing = next((line.split("=", 1)[1].split(",") for line in lines if line.startswith("CORS_ORIGINS=")), [])
    value = "CORS_ORIGINS=" + ",".join(dict.fromkeys([*existing, *CLIENT_ORIGINS]))
    path.write_text("\n".join([line for line in lines if not line.startswith("CORS_ORIGINS=")] + [value]) + "\n",
                    encoding="utf-8", newline="\n")
    remote("""set -eu
python3 - "$1" <<'PY'
import os, sys
from pathlib import Path
p=Path('/opt/labconnect/shared/api.env')
lines=[line for line in p.read_text().splitlines() if not line.startswith('CORS_ORIGINS=')]
temporary=p.with_suffix('.env.pending')
temporary.write_text('\\n'.join(lines+[sys.argv[1]])+'\\n')
temporary.chmod(0o600)
os.replace(temporary,p)
print('Updated client CORS origins; credentials preserved.')
PY
release=$(readlink -f /opt/labconnect/current)
docker compose --env-file /opt/labconnect/shared/cloud.env --env-file "$release/release.env" -f "$release/compose.yml" up -d --force-recreate --wait api
""", value)


def provision_ai():
    """Initial encrypted platform profile only. A later replacement needs C's test/enable workflow."""
    import sys
    run([sys.executable, ROOT / "others/scripts/shared_env.py", "backend", "app.core.cloud_setup", "prepare"], cwd=ROOT)
    local = RUNTIME / "secrets/platform-ai.json"
    profile = json.loads(local.read_text(encoding="utf-8"))
    checksum = digest(RUNTIME / "secrets/ai-master.key")
    result = remote(r'''set -eu
python3 - "$1" "$2" <<'PY'
import hashlib,json,os,sys
from pathlib import Path
root=Path('/opt/labconnect/shared')
if hashlib.sha256((root/'ai-master.key').read_bytes()).hexdigest()!=sys.argv[1]:
    raise SystemExit('Cloud encryption key differs from the project copy; preserved')
directory=root/'ai'
directory.mkdir(exist_ok=True)
os.chown(directory,10001,10001)
directory.chmod(0o700)
active=directory/'platform-ai.json'
if active.exists():
    if json.loads(active.read_text())['revision']!=sys.argv[2]:
        raise SystemExit('Different active profile preserved; use the tested revision/enable workflow')
    print('configured')
else: print('empty')
PY
''', checksum, profile["revision"], capture=True)
    if result.stdout.strip() == b"empty":
        upload(local, REMOTE_ROOT + "/shared/ai/platform-ai.pending.json")
        remote("set -eu\nchown 10001:10001 /opt/labconnect/shared/ai/platform-ai.pending.json\n"
               "chmod 400 /opt/labconnect/shared/ai/platform-ai.pending.json\n"
               "mv /opt/labconnect/shared/ai/platform-ai.pending.json /opt/labconnect/shared/ai/platform-ai.json\n")
    print("Encrypted cloud platform profile prepared; school selections remain unconfigured.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("probe")
    prepare_parser = sub.add_parser("prepare")
    prepare_parser.add_argument("--public-host")
    sub.add_parser("build")
    deploy_parser = sub.add_parser("deploy")
    deploy_parser.add_argument("bundle", type=Path)
    sub.add_parser("status")
    sub.add_parser("backup")
    sub.add_parser("sync-cors")
    sub.add_parser("provision-ai")
    sub.add_parser("probe-ai")
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("url")
    args = parser.parse_args()
    if args.command == "probe":
        remote((CLOUD / "probe.sh").read_text(encoding="utf-8"))
    elif args.command == "prepare":
        prepare(args.public_host)
    elif args.command == "build":
        build()
    elif args.command == "deploy":
        deploy(args.bundle)
    elif args.command in {"status", "backup"}:
        remote((CLOUD / "release.sh").read_text(encoding="utf-8"), args.command)
    elif args.command == "verify":
        verify(args.url)
    elif args.command == "sync-cors":
        sync_cors()
    elif args.command == "provision-ai":
        provision_ai()
    elif args.command == "probe-ai":
        remote("docker exec labconnect-cloud-api-1 .venv/bin/python -m app.core.cloud_setup probe\n")


if __name__ == "__main__":
    main()
