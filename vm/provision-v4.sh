#!/usr/bin/env bash
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo 'Requires root in an Ubuntu guest' >&2; exit 1; }
case $(dpkg --print-architecture) in amd64|arm64) ;; *) echo 'Requires amd64 or arm64 Ubuntu' >&2; exit 1;; esac
if pgrep -u agent >/dev/null; then echo 'Stop active agent sessions before updating the VM' >&2; exit 1; fi
if docker top clab-seminar-management -eo pid,comm 2>/dev/null | grep -Eq '^[[:space:]]*[0-9]+[[:space:]]+opencode'; then
 echo 'Stop the active management OpenCode session before rebuilding' >&2; exit 1
fi
cd /opt/seminar-lab
python3 vm/configure-accounts.py
bash vm/install-v4-tools.sh
python3 management/prepare_workspace.py
python3 management/prepare_v4.py
bash management/install_controller.sh
docker build -f network/Dockerfile.endpoint -t seminar-endpoint:v4 .
docker build -f network/Dockerfile.management -t seminar-management:v5 .
install -m0700 vm/start-v4.sh /usr/local/sbin/seminar-start
install -m0644 vm/seminar-lab-v4.service /etc/systemd/system/seminar-lab.service
systemctl daemon-reload
systemctl enable seminar-lab.service
touch /var/lib/seminar-lab/rebuild-request
chmod 0600 /var/lib/seminar-lab/rebuild-request
systemctl restart seminar-lab.service
if [[ ! -d /home/student/labs/ui ]]; then /opt/seminar-tools/bin/python management/prepare_ui.py; fi
python3 management/install_workflow.py
echo 'Containerlab baseline and native management provisioned successfully.'
