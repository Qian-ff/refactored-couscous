"""Back up PostgreSQL before additive migrations and verify retained A0 identity/class data."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = r'''
import hashlib, json, sys
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from app.core.db import engine
columns = {
    "school":"id,code,name", "college":"id,school_id,code,name",
    "app_user":"id,school_id,college_id,username,display_name,hashed_password,is_active",
    "role_grant":"id,user_id,school_id,role,college_id",
    "course_catalog":"id,school_id,college_id,owner_id,code,title,created_at",
    "course":"id,school_id,college_id,catalog_id,code,title,created_at",
    "course_staff":"id,school_id,course_id,user_id,is_primary",
    "enrollment":"id,school_id,course_id,user_id,status",
    "login_session":"id,user_id,expires_at,revoked,default_work_role",
}
tables = set(inspect(engine).get_table_names())
requested = json.loads(sys.argv[1]) if len(sys.argv) > 1 else None
with engine.connect() as c:
    result = {"tables":{}}
    for table, names in columns.items():
        if table not in tables or (requested is not None and table not in requested):
            continue
        # Fresh A1 databases do not yet have A0 catalog/default-role columns.
        actual = {col["name"] for col in inspect(engine).get_columns(table)}
        fields = requested[table] if requested is not None else [name for name in names.split(",") if name in actual]
        rows = sorted(str(tuple(row)) for row in c.execute(text("SELECT " + ",".join(fields) + " FROM " + table)))
        result["tables"][table] = {"columns":fields,"count":len(rows),
            "sha256":hashlib.sha256("\n".join(rows).encode()).hexdigest()}
    result["revision"] = c.execute(text("SELECT version_num FROM alembic_version")).scalar_one() if "alembic_version" in tables else None
result["target"] = ScriptDirectory.from_config(Config("alembic.ini")).get_current_head()
print(json.dumps(result))
'''


def snapshot(columns=None):
    # Use the shared configuration/source bootstrap, without putting credentials in command arguments.
    module = "__migration_snapshot_" + uuid4().hex
    temporary = ROOT / "others/backend" / (module + ".py")
    temporary.write_text(SNAPSHOT, encoding="utf-8")
    try:
        arguments = [] if columns is None else [json.dumps(columns)]
        result = subprocess.run([sys.executable, "others/scripts/shared_env.py", "backend", module, *arguments],
                                cwd=ROOT, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    from workflow import primary_root
    if ROOT != primary_root(ROOT):
        raise RuntimeError("Only A in the primary checkout runs shared database migrations")
    before = snapshot()
    if before["revision"] == before["target"]:
        print("Database already matches migration " + before["target"])
        return
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = ROOT / f"others/backups/pre-migration-{stamp}-{uuid4().hex[:8]}.dump"
    backup.parent.mkdir(parents=True, exist_ok=True)
    compose = ["docker", "compose", "--env-file", ".env", "-f", "others/deploy/compose.yml"]
    container = subprocess.check_output([*compose,"ps","-q","db"], cwd=ROOT, text=True).strip()
    if not container:
        raise RuntimeError("Project PostgreSQL container is not running")
    remote = "/tmp/" + backup.name
    subprocess.run([*compose,"exec","-T","db","sh","-c",
                    'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom -f "$1"',
                    "migration-backup",remote], cwd=ROOT, check=True)
    manifest = subprocess.run([*compose,"exec","-T","db","pg_restore","--list",remote],
                              cwd=ROOT, capture_output=True, check=True)
    subprocess.run(["docker","cp",container+":"+remote,str(backup)], check=True)
    if backup.read_bytes()[:5] != b"PGDMP" or not manifest.stdout:
        raise RuntimeError("Backup archive verification failed; migration not started")
    subprocess.run([sys.executable,"others/scripts/shared_env.py","backend","alembic","upgrade","head"],
                   cwd=ROOT, check=True)
    after = snapshot({table: original["columns"] for table, original in before["tables"].items()})
    for table, original in before["tables"].items():
        # This tool protects the named A0 data; later schema changes need an explicit compatibility update.
        if after["tables"].get(table) != original:
            raise RuntimeError("Existing data changed in " + table + "; backup preserved for inspection")
    report = {"status":"passed","before":before,"after":after,
              "backup":backup.relative_to(ROOT).as_posix(),
              "backup_sha256":hashlib.sha256(backup.read_bytes()).hexdigest()}
    path = ROOT / "others/reports/b1-public/database-migration.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report,indent=2) + "\n",encoding="utf-8")
    print("PASS: backed up database and preserved all existing identity/class relationships")


if __name__ == "__main__":
    main()
