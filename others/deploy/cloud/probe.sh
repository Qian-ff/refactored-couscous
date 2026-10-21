#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' '--- system ---'
head -n 4 /etc/os-release
id
uname -m
nproc
free -m
df -h /
printf '%s\n' '--- instance identity ---'
curl -fsS --max-time 3 http://100.100.100.200/latest/meta-data/instance-id
printf '\n%s\n' '--- docker ---'
docker version --format '{{.Server.Version}}'
docker compose version
printf '%s\n' '--- listeners ---'
ss -lntp
printf '%s\n' '--- containers ---'
docker ps -a --format '{{.Names}} {{.Image}} {{.Status}}'
docker volume ls --format '{{.Name}}'
