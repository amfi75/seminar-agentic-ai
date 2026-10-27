#!/usr/bin/env bash
set -euo pipefail
install -m 0700 /opt/seminar-lab/broker/labctl_v5.py /usr/local/sbin/lab-admin
# Remove only the recognized obsolete installed alias, never an unrelated file.
if [[ -f /usr/local/sbin/labctl ]] && grep -q "human lab-admin import" /usr/local/sbin/labctl; then rm /usr/local/sbin/labctl; fi
cat > /etc/sudoers.d/seminar-lab <<'SUDOERS'
Defaults:agent env_reset
student ALL=(agent) NOPASSWD: ALL
student ALL=(root) NOPASSWD: /usr/local/sbin/lab-admin workload *, /usr/local/sbin/lab-admin verify, /usr/local/sbin/lab-admin reset, /usr/local/sbin/lab-admin fault, /usr/local/sbin/lab-admin delay, /usr/local/sbin/lab-admin loss, /usr/local/sbin/lab-admin rate, /usr/local/sbin/lab-admin clear-impairment
SUDOERS
chmod 0440 /etc/sudoers.d/seminar-lab
visudo -cf /etc/sudoers.d/seminar-lab
