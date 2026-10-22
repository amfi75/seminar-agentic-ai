#!/usr/bin/env bash
set -euo pipefail
install -m 0700 /opt/seminar-lab/broker/labctl_v5.py /usr/local/sbin/labctl
install -m 0700 /opt/seminar-lab/broker/labctl_v5.py /usr/local/sbin/lab-admin
cat > /etc/sudoers.d/seminar-lab <<'SUDOERS'
Defaults:agent env_reset
student ALL=(agent) NOPASSWD: ALL
student ALL=(root) NOPASSWD: /usr/local/sbin/lab-admin import *, /usr/local/sbin/lab-admin workload *, /usr/local/sbin/lab-admin verify, /usr/local/sbin/lab-admin reset, /usr/local/sbin/lab-admin fault, /usr/local/sbin/lab-admin show *, /usr/local/sbin/lab-admin approve *, /usr/local/sbin/lab-admin delay, /usr/local/sbin/lab-admin loss, /usr/local/sbin/lab-admin rate, /usr/local/sbin/lab-admin clear-impairment
SUDOERS
chmod 0440 /etc/sudoers.d/seminar-lab
visudo -cf /etc/sudoers.d/seminar-lab
