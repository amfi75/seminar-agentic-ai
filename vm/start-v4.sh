#!/usr/bin/env bash
set -euo pipefail
[[ $EUID -eq 0 ]] || exit 1
if pgrep -u agent >/dev/null; then echo 'Stop active agent sessions before rebuilding the reference network' >&2; exit 1; fi
exec 9>/var/lib/seminar-lab/lifecycle.lock
flock 9
if docker top clab-seminar-management -eo pid,comm 2>/dev/null | grep -Eq '^[[:space:]]*[0-9]+[[:space:]]+opencode'; then
 echo 'Stop the active management OpenCode session before rebuilding' >&2; exit 1
fi
cd /opt/seminar-lab
modprobe sch_netem
start_ns=$(python3 -c 'import time;print(time.monotonic_ns())')
state=/var/lib/seminar-lab
# Runtime is private and separate from the source/ownership synchronization.
install -d -m0700 "$state/runtime"
# Bind sources must exist before Containerlab validates the topology.
install -d -m0750 /var/log/seminar-lab
count=$(docker ps -a --format '{{.Names}}' | grep -Ec '^clab-seminar-(management|client|r1|r2|server)$' || true)
rebuild=false
if [[ -f "$state/rebuild-request" ]]; then rebuild=true
elif [[ "$count" == 5 && -f "$state/management-home-identity.json" ]]; then
 # Normal service/VM startup resumes existing devices; it never injects/reset faults.
 docker start clab-seminar-r1 clab-seminar-r2 clab-seminar-client clab-seminar-server clab-seminar-management >/dev/null
 python3 management/restore_links.py
elif [[ "$count" == 0 ]]; then rebuild=true
else echo 'Partial topology preserved. Use the explicit Recover devices action.' >&2; exit 1
fi
if [[ "$rebuild" == true ]]; then
 if [[ "$count" != 0 ]]; then containerlab destroy -t "$state/runtime/topology.clab.yml" --cleanup; fi
 cp network/topology.clab.yml "$state/runtime/topology.clab.yml"
 cd "$state/runtime"
 containerlab deploy -t topology.clab.yml
 cd /opt/seminar-lab
 LAB_DIRECTORY="$state/runtime/clab-seminar" /opt/seminar-tools/bin/python management/bootstrap_devices.py
 /opt/seminar-tools/bin/python management/publish_observer.py
 rm -f "$state/rebuild-request"
fi
/opt/seminar-tools/bin/python management/wait_devices.py
bash management/setup_collection.sh
/opt/seminar-tools/bin/python management/configure_collectors.py
systemctl restart seminar-collect
python3 management/prepare_management.py
python3 management/network_boundary.py
if [[ "$rebuild" == true ]]; then /usr/local/sbin/lab-admin reset; fi
end_ns=$(python3 -c 'import time;print(time.monotonic_ns())')
python3 - "$start_ns" "$end_ns" <<'PY'
import sys,json,pathlib,time
p=pathlib.Path('/var/lib/seminar-lab/startup-history.jsonl')
with p.open('a') as f:f.write(json.dumps({'recorded_wall_ns':time.time_ns(),'start_monotonic_ns':int(sys.argv[1]),'ready_monotonic_ns':int(sys.argv[2]),'duration_s':(int(sys.argv[2])-int(sys.argv[1]))/1e9})+'\n')
p.chmod(0o600)
PY
