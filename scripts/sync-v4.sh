#!/usr/bin/env bash
# Student-owned distribution wrapper; runtime provisioning remains unchanged.
set -euo pipefail
cd "$(dirname "$0")/.."
vm_name=${1:-seminar-agentic-ai}
[[ "$vm_name" =~ ^seminar-agentic-ai(-[a-z0-9-]+)?$ ]] || exit 1
[[ -f STUDENT-FILES.txt && ! -L STUDENT-FILES.txt ]] || { echo 'Missing student source file list' >&2; exit 1; }
while IFS= read -r file; do
 [[ "$file" =~ ^[A-Za-z0-9_.-]+(/[A-Za-z0-9_.-]+)*$ ]] || { echo 'Invalid source path' >&2; exit 1; }
 [[ "$file" != -* ]] || { echo 'Option-like source path refused' >&2; exit 1; }
 case "/$file/" in */../*|*/./*|*/.git/*) echo 'Unsafe source path' >&2; exit 1;; esac
 part=$file
 while [[ "$part" != . ]]; do
  [[ ! -L "$part" ]] || { echo 'Linked source path refused' >&2; exit 1; }
  if [[ "$part" == */* ]]; then part=${part%/*}; else part=.; fi
 done
 [[ -f "$file" ]] || { echo "Missing student source: $file" >&2; exit 1; }
done < STUDENT-FILES.txt
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
COPYFILE_DISABLE=1 tar --no-xattrs -czf "$stage/source.tar.gz" -T STUDENT-FILES.txt
chmod 0600 "$stage/source.tar.gz"
multipass transfer "$stage/source.tar.gz" "$vm_name:/home/ubuntu/v4-source.tar.gz"
multipass transfer vm/unpack-source.sh "$vm_name:/home/ubuntu/lab-unpack-source.sh"
multipass exec "$vm_name" -- sudo bash /home/ubuntu/lab-unpack-source.sh
