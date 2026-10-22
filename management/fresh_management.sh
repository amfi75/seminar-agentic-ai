#!/usr/bin/env bash
# Explicit operator action: archive a workstation home and create a fresh context.
set -euo pipefail
[[ $EUID -eq 0 && $# -eq 0 ]] || exit 1
exec 9>/var/lib/seminar-lab/lifecycle.lock
flock 9
if docker top clab-seminar-management -eo pid,comm | grep -Eq '^[[:space:]]*[0-9]+[[:space:]]+opencode'; then
 echo 'Stop OpenCode before making a fresh trial' >&2; exit 1
fi
state=/var/lib/seminar-lab
volume=$(docker volume inspect -f '{{.Mountpoint}}' seminar-management-home)
[[ "$volume" == /var/lib/docker/volumes/seminar-management-home/_data ]] || exit 1
archive="$state/profile-archives/management-$(date -u +%Y%m%dT%H%M%SZ)-$RANDOM.tar.gz"
install -d -m0700 "$state/profile-archives"
docker stop clab-seminar-management >/dev/null
# Archive and verify every file byte before removing this volume.
python3 /opt/seminar-lab/management/archive_home.py "$volume" "$archive"
docker rm clab-seminar-management >/dev/null
docker volume rm seminar-management-home >/dev/null
rm -f "$state/management-home-identity.json"
flock -u 9
systemctl restart seminar-lab
echo 'Fresh management home ready; previous profile retained privately.'
