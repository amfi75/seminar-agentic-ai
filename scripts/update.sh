#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
vm_name=${1:-seminar-agentic-ai}
[[ "$vm_name" =~ ^seminar-agentic-ai(-[a-z0-9-]+)?$ ]] || exit 1
multipass exec "$vm_name" -- sudo cloud-init status --wait
scripts/sync-v4.sh "$vm_name"
multipass exec "$vm_name" -- sudo bash /opt/seminar-lab/vm/provision-v4.sh
