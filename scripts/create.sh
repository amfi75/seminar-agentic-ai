#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
vm_name=${1:-seminar-agentic-ai}
[[ "$vm_name" =~ ^seminar-agentic-ai(-[a-z0-9-]+)?$ ]] || { echo 'Use a seminar-agentic-ai name' >&2; exit 1; }
command -v multipass >/dev/null || { echo 'Install Multipass first; see docs/quickstart.md' >&2; exit 1; }
# Refuse reuse: this command is a clean build, never an overwrite operation.
inventory=$(multipass list --format json)
if printf '%s' "$inventory" | grep -Eq '"name"[[:space:]]*:[[:space:]]*"'"$vm_name"'"'; then
  echo 'VM already exists. Use scripts/update.sh, or choose a fresh lab name.' >&2
  exit 1
fi
multipass launch 24.04 --name "$vm_name" --cpus 4 --memory 8G --disk 40G \
  --cloud-init vm/cloud-init.yaml --timeout 900
scripts/update.sh "$vm_name"
