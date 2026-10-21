#!/usr/bin/env bash
set -euo pipefail
umask 077
ROOT=/opt/labconnect
mode=${1:?Specify apply, backup or status}
sha=${2:-}
if [[ "$mode" == apply ]]; then
  [[ "$sha" =~ ^[0-9a-f]{40}$ ]] || { echo 'Invalid release SHA' >&2; exit 2; }
  release="$ROOT/releases/$sha"
else
  release=$(readlink -f "$ROOT/current")
fi
[[ -f "$release/compose.yml" && -f "$release/release.env" ]]
dc() { docker compose --env-file "$ROOT/shared/cloud.env" --env-file "$release/release.env" -f "$release/compose.yml" "$@"; }
exec 9>"$ROOT/deployment.lock"
flock -n 9 || { echo 'Another deployment or backup is running' >&2; exit 1; }
backup() {
  mkdir -p "$ROOT/backups"
  stamp=$(date -u +%Y%m%dT%H%M%SZ)
  backup_path="$ROOT/backups/$stamp-before-${sha:-manual}.dump"
  dc exec -T db sh -c 'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$backup_path"
  dc exec -T db pg_restore --list < "$backup_path" > /dev/null
  sha256sum "$backup_path" > "$backup_path.sha256"
  echo "Verified PostgreSQL backup: $backup_path"
}
case "$mode" in
  apply)
    cd "$release"
    sha256sum --check SHA256SUMS
    gzip -dc images.tar.gz | docker load
    python3 - <<'PY'
import json, subprocess
from pathlib import Path
manifest = json.loads(Path('manifest.json').read_text())
for name, image in [('api', manifest['api_image']), ('web', manifest['web_image']),
                    ('postgres', manifest['image_ids']['postgres'])]:
    actual = json.loads(subprocess.check_output(['docker', 'image', 'inspect', image]))[0]
    if actual['Id'] != manifest['image_ids'][name]:
        raise SystemExit('Loaded image digest mismatch: ' + name)
    if name != 'postgres' and actual['Config']['Labels'].get('org.opencontainers.image.revision') != manifest['source_sha']:
        raise SystemExit('Loaded source version mismatch: ' + name)
print('Verified loaded image IDs and source labels.')
PY
    dc up -d --wait db
    dc stop web api
    backup
    dc run --rm --no-deps migrate
    dc run --rm --no-deps bootstrap
    dc up -d --wait api web
    [[ ! -e "$ROOT/current" || -L "$ROOT/current" ]] || { echo 'Unexpected current directory; preserved' >&2; exit 1; }
    ln -sfn "$release" "$ROOT/current"
    printf '{"source_sha":"%s","status":"containers_ready_tls_check_pending"}\n' "$sha" > "$ROOT/deployment.json"
    dc ps
    ;;
  backup) backup ;;
  status) cat "$ROOT/deployment.json"; dc ps; ss -lnt ;;
  *) echo 'Unknown operation' >&2; exit 2 ;;
esac
