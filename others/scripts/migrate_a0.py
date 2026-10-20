"""Back up the existing demo DB, apply additive A0 migration and verify retained relationships."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime

ROOT = Path(__file__).resolve().parents[2]

SNAPSHOT = r'''
import hashlib, json
from sqlalchemy import text
from app.core.db import engine
with engine.connect() as c:
    result = {}
    for table in ("course", "course_staff", "enrollment"):
        rows = sorted(str(tuple(row)) for row in c.execute(text("SELECT * FROM " + table)))
        # Course gained catalog_id; compare only columns which existed in A1.
        if table == "course":
            rows = sorted(str(tuple(row)) for row in c.execute(text(
                "SELECT id,school_id,college_id,code,title,created_at FROM course")))
        result[table] = {"count":len(rows),"sha256":hashlib.sha256("\n".join(rows).encode()).hexdigest()}
    result["migration"] = c.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
print(json.dumps(result))
'''


def snapshot():
    # Use the same configuration and source binding as all other backend tools.
    code = "import sys; sys.path.insert(0,'others/scripts'); import shared_env; " \
           "from pathlib import Path; from workflow import primary_root; " \
           "root=Path.cwd(); primary=primary_root(root); " \
           "import subprocess; raise SystemExit(subprocess.run([str(primary/'others/backend/.venv/Scripts/python.exe')," \
           "'-c',shared_env.BOOTSTRAP,str(root),str(primary),'__a0_snapshot__']).returncode)"
    # runpy can execute a temporary local module while preserving shared_env's setup.
    module = ROOT / "others/backend/__a0_snapshot__.py"
    try:
        module.write_text(SNAPSHOT, encoding="utf-8")
        result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    finally:
        module.unlink(missing_ok=True)


def main():
    before = snapshot()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = ROOT / f"others/backups/a0-before-{stamp}.dump"
    backup.parent.mkdir(parents=True, exist_ok=True)
    compose = ["docker", "compose", "--env-file", ".env", "-f", "others/deploy/compose.yml"]
    container = subprocess.check_output([*compose, "ps", "-q", "db"], cwd=ROOT, text=True).strip()
    if not container:
        raise RuntimeError("Existing PostgreSQL container is not running")
    temporary = f"/tmp/labconnect-a0-before-{stamp}.dump"
    subprocess.run([*compose, "exec", "-T", "db", "sh", "-c",
                    'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom -f "$1"',
                    "a0-backup", temporary], cwd=ROOT, check=True)
    subprocess.run(["docker", "cp", f"{container}:{temporary}", str(backup)], check=True)
    if backup.stat().st_size < 1000:
        raise RuntimeError("Database backup is unexpectedly small; migration was not started")
    subprocess.run([sys.executable, "others/scripts/shared_env.py", "backend", "alembic", "upgrade", "head"],
                   cwd=ROOT, check=True)
    after = snapshot()
    for table in ("course", "course_staff", "enrollment"):
        if before[table] != after[table]:
            raise RuntimeError("Existing relationship changed: " + table)
    report = {"status":"passed", "before":before, "after":after,
              "backup":backup.relative_to(ROOT).as_posix(), "backup_sha256":hashlib.sha256(backup.read_bytes()).hexdigest()}
    destination = ROOT / "others/reports/a0/demo-migration.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
