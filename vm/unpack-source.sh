#!/usr/bin/env bash
# Shared transfer bootstrap: run as root in the newly created guest.
set -euo pipefail
[[ $EUID -eq 0 ]] || exit 1
install -d -o root -g student -m 0750 /opt/seminar-lab
tar --no-overwrite-dir -xzf /home/ubuntu/v4-source.tar.gz -C /opt/seminar-lab
find /opt/seminar-lab -name 'clab-*' -prune -o -exec chown root:student {} +
find /opt/seminar-lab -name 'clab-*' -prune -o -exec chmod go-w {} +
chmod 0750 /opt/seminar-lab
rm /home/ubuntu/v4-source.tar.gz
