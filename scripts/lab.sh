#!/usr/bin/env bash
# Host convenience launcher. No host Python, no automatic network reset.
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
lab_home=${SEMINAR_LAB_HOME:-$HOME}
action=${1:---help}
vm=${2:-seminar-agentic-ai}
case "$vm" in seminar-agentic-ai|seminar-agentic-ai-*) ;; *) echo 'Use a seminar-agentic-ai VM name.' >&2; exit 1;; esac
[[ "$vm" =~ ^seminar-agentic-ai(-[a-z0-9-]+)?$ ]] || exit 1
alias=seminar-lab
[[ "$vm" == seminar-agentic-ai ]] || alias="seminar-lab-${vm#seminar-agentic-ai-}"
fail() { echo "Lab: $*" >&2; exit 1; }
case "$action" in setup|open|pause|stop|status) ;; *)
 cat <<'HELP'
Usage: bash scripts/lab.sh setup|open|pause|stop|status [seminar-agentic-ai[-NAME]]
setup: create or safely attach; prepare standard SSH and VS Code
open: start/resume and open the prepared remote workspace; never reset
pause: suspend this VM; stop: shut it down; status: read-only diagnostics
Prerequisites: Multipass, OpenSSH, VS Code. Install help:
https://canonical.com/multipass/install and https://code.visualstudio.com/download
Complete administrator, passphrase, and Workspace Trust dialogs locally.
HELP
 [[ "$action" == --help || "$action" == -h ]] && exit 0
 exit 1;; esac
command -v multipass >/dev/null || fail 'Install Multipass first: https://canonical.com/multipass/install'
# Multipass exec has no native timeout; bound unattended service/guest operations.
bounded() {
 local limit=$1; shift
 "$@" & local child=$!
 (sleeper=; trap '[[ -z "$sleeper" ]] || kill "$sleeper" 2>/dev/null; exit 0' TERM
  sleep "$limit" & sleeper=$!; wait "$sleeper"; kill -TERM "$child" 2>/dev/null || true) & local timer=$!
 local result=0
 wait "$child" || result=$?
 kill "$timer" 2>/dev/null || true
 wait "$timer" 2>/dev/null || true
 [[ $result -ne 143 ]] || echo 'Lab: operation timed out; no automatic recovery/reset was run.' >&2
 return "$result"
}
mp() { bounded 30 multipass "$@"; }
state() {
 local inventory
 inventory=$(mp list --format csv) || fail 'Cannot query Multipass. Check its service; the VM has not been treated as absent.'
 [[ "$(printf '%s\n' "$inventory" | head -1)" == Name,State,* ]] || fail 'Malformed Multipass inventory; refusing to infer that the VM is absent.'
 printf '%s\n' "$inventory" | awk -F, -v name="$vm" '$1==name{print $2}'
}
current=$(state)
if [[ "$action" == status ]]; then
 echo "VM: $vm  State: ${current:-absent}"
 if [[ "$current" == Running ]]; then
  mp exec "$vm" -- sudo python3 /opt/seminar-lab/management/install_workflow.py --probe || echo 'Convenience layer not installed; run setup.'
  echo 'Separate application check (an intentional scenario can fail this):'
  mp exec "$vm" -- sudo /usr/local/sbin/lab-admin verify || exit 1
 fi
 exit 0
fi
if [[ "$action" == pause || "$action" == stop ]]; then
 [[ -n "$current" ]] || fail 'VM does not exist; nothing changed.'
 echo 'Save your editor work first. VS Code will disconnect. No VM or profile will be deleted.'
 if [[ "$action" == pause && "$current" == Suspended || "$action" == stop && "$current" == Stopped ]]; then echo "Already $current."; exit 0; fi
 [[ "$current" == Running || "$action" == stop && "$current" == Suspended ]] || fail "Cannot $action a VM in $current state."
 if [[ "$action" == pause ]]; then bounded 120 multipass suspend "$vm"; else bounded 120 multipass stop "$vm"; fi
 exit 0
fi
case "$(uname -s):$(uname -m)" in Darwin:arm64|Darwin:x86_64|Linux:x86_64|Linux:aarch64|Linux:arm64) ;; *) fail 'This host OS/architecture is outside the documented native targets.';; esac
for tool in ssh ssh-keygen tar awk; do
 if ! command -v "$tool" >/dev/null; then
  if [[ "$(uname -s)" == Linux ]]; then
   fail "Missing $tool. On Ubuntu/Debian: sudo apt install openssh-client tar gawk. Other supported Linux hosts: install equivalent packages with your distribution package manager."
  else fail "Missing $tool. Restore macOS command-line tools; OpenSSH and archive tools are included with macOS. See docs/start-here.md for prerequisites."; fi
 fi
done
code=$(command -v code || true)
if [[ -z "$code" && -x '/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code' ]]; then code='/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code'; fi
if [[ -z "$code" && -x "$lab_home/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code" ]]; then code="$lab_home/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"; fi
[[ -n "$code" ]] || fail 'Install VS Code: https://code.visualstudio.com/download (on Linux, make its code CLI available).'
settings="$lab_home/.config/Code/User/settings.json"
[[ "$(uname -s)" != Darwin ]] || settings="$lab_home/Library/Application Support/Code/User/settings.json"
if [[ -f "$settings" ]] && grep -Eq '"remote.SSH.configFile"[[:space:]]*:[[:space:]]*"[^"]+"' "$settings"; then
 fail 'VS Code uses a nondefault remote.SSH.configFile. Select your standard ~/.ssh/config in Settings before using this launcher; other preferences were not changed.'
fi
if [[ "$action" == setup ]]; then
 echo 'Reference VM allocation: 4 vCPU, 8 GiB RAM, 40 GiB disk. Leave room for your host OS and applications.'
 df -Pk "$root" | tail -1
 if [[ "$(uname -s)" == Darwin ]]; then sysctl -n hw.memsize; else awk '/MemTotal/{print "Host RAM:", $2, $3}' /proc/meminfo; fi
fi
if [[ -z "$current" ]]; then
 [[ "$action" == setup ]] || fail 'Run setup first; open does not create a VM.'
 bash "$root/scripts/create.sh" "$vm" || fail 'VM creation/provisioning failed. Preserve the partial VM and inspect the output; no deletion was performed.'
elif [[ "$current" == Stopped || "$current" == Suspended ]]; then
 bounded 330 multipass start "$vm" --timeout 300
elif [[ "$current" != Running ]]; then fail "VM is $current. Preserve it and diagnose before continuing."; fi
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
installer=/opt/seminar-lab/management/install_workflow.py
if [[ "$action" == setup ]]; then
 guest_stage=$(mp exec "$vm" -- mktemp -d /home/ubuntu/lab-workflow.XXXXXX)
 [[ "$guest_stage" =~ ^/home/ubuntu/lab-workflow\.[A-Za-z0-9]+$ ]] || fail 'Unexpected guest staging path.'
 for file in install_workflow.py workflow.py fresh_trial_entry.py workflow-start.md; do
  mp transfer "$root/management/$file" "$vm:$guest_stage/$file"
 done
 installer="$guest_stage/install_workflow.py"
fi
ready=false
ready_attempts=${SEMINAR_LAB_READY_ATTEMPTS:-30}
[[ "$ready_attempts" =~ ^[0-9]+$ && "$ready_attempts" -ge 1 && "$ready_attempts" -le 30 ]] || fail 'Readiness attempts must be 1..30.'
for attempt in $(seq 1 "$ready_attempts"); do
 if probe=$(mp exec "$vm" -- sudo python3 "$installer" --probe) && printf '%s' "$probe" | grep -q '"ready": true'; then ready=true; break; fi
 sleep 2
done
[[ "$ready" == true ]] || fail 'The recognized v5 infrastructure is not ready. Run setup if this layer is absent; diagnose services/containers otherwise. No reset was performed.'
if [[ "$action" == setup ]] && printf '%s' "$probe" | grep -q '"active_opencode": true'; then fail 'Stop OpenCode before installing the convenience layer; no profile was changed.'; fi
sshdir="$lab_home/.ssh"
for path in "$lab_home" "$sshdir" "$sshdir/config" "$sshdir/$alias" "$sshdir/$alias.pub" "$sshdir/known_hosts.$alias"; do [[ ! -L "$path" ]] || fail "Refusing linked host path: $path"; done
mkdir -p "$sshdir"; chmod 700 "$sshdir"
key="$sshdir/$alias"; trust="$sshdir/known_hosts.$alias"; config="$sshdir/config"
[[ "$lab_home" != *'"'* && "$lab_home" != *$'\n'* ]] || fail 'Unsupported quote/newline in home path.'
if [[ ! -f "$key" ]]; then
 [[ "$action" == setup ]] || fail 'Dedicated SSH key is absent; run setup.'
 echo 'Create your lab key below. A passphrase is recommended; enter it locally. Choosing an empty passphrase is your explicit choice.'
 ssh-keygen -t ed25519 -f "$key"
fi
chmod 600 "$key"
if [[ ! -f "$key.pub" ]]; then ssh-keygen -y -f "$key" > "$stage/public"; cp "$stage/public" "$key.pub"; fi
# Inspect without a neighboring .pub: ssh-keygen otherwise prefers that sidecar.
cp "$key" "$stage/identity-check"; chmod 600 "$stage/identity-check"
private_fingerprint=$(ssh-keygen -lf "$stage/identity-check" | awk '{print $2}')
public_fingerprint=$(ssh-keygen -lf "$key.pub" | awk '{print $2}')
[[ "$private_fingerprint" == "$public_fingerprint" ]] || fail 'The public key does not match the dedicated private identity. Existing keys preserved.'
pub=$(cat "$key.pub")
[[ "$pub" == ssh-ed25519\ * ]] || fail 'The dedicated key must be Ed25519; do not overwrite an existing identity.'
address=$(mp info "$vm" --format csv | awk -F, -v name="$vm" '$1==name{print $3}')
[[ "$address" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ && "$address" != 10.79.* && "$address" != 172.17.* ]] || fail 'Multipass did not report a usable host-reachable IPv4 address.'
hostkey=$(mp exec "$vm" -- sudo cat /etc/ssh/ssh_host_ed25519_key.pub | awk '{print $1 " " $2}')
[[ "$hostkey" == ssh-ed25519\ * ]] || fail 'Could not read the VM public identity through Multipass.'
expected="$alias $hostkey"
if [[ -f "$trust" && "$(cat "$trust")" != "$expected" ]]; then
 echo 'VM identity changed. Normal open will not replace host trust.' >&2
 [[ "$action" == setup ]] || fail 'If you intentionally rebuilt the VM, run setup and confirm its new Multipass identity.'
 read -r -p "Confirm an intentional rebuild by typing $vm: " answer
 [[ "$answer" == "$vm" ]] || fail 'Host trust unchanged.'
 cp -p "$trust" "$trust.before-workflow-$(date +%s)"
fi
if [[ ! -f "$trust" || "$(cat "$trust")" != "$expected" ]]; then
 [[ "$action" == setup ]] || fail 'Managed trust is absent; run setup.'
 printf '%s\n' "$expected" > "$trust"; chmod 600 "$trust"
fi
[[ -f "$config" ]] || { [[ "$action" == setup ]] || fail 'Run setup to create the standard SSH entry.'; touch "$config"; chmod 600 "$config"; }
if ! awk -v marker="# BEGIN managed $alias" '{sub(/\r$/, "");if($0==marker)found=1} END{exit !found}' "$config"; then
 [[ "$action" == setup ]] || fail 'Run setup once to adopt this connection safely.'
 if grep -Ei "^[[:space:]]*Host[[:space:]]+.*$alias" "$config" >/dev/null; then
  effective=$(ssh -G "$alias" 2>/dev/null)
  printf '%s\n' "$effective" | grep -Fxq "hostname $address" || fail 'Existing alias points elsewhere; preserve it and resolve the conflict.'
  printf '%s\n' "$effective" | grep -Fxq 'user student' || fail 'Existing alias uses another account; preserve it.'
  original_identities=$(printf '%s\n' "$effective" | sed -n 's/^identityfile //p')
  [[ "$original_identities" == "~/.ssh/$alias" || "$original_identities" == "$key" ]] || fail 'Existing alias uses additional/different identities; preserve it.'
 fi
fi
awk -v operation="$action" -v alias="$alias" -v address="$address" -v identity="$key" -v trust="$trust" -f "$root/scripts/lab-ssh-config.awk" "$config" > "$stage/config" || fail 'SSH configuration conflict; original unchanged.'
effective=$(ssh -G -F "$stage/config" "$alias" 2>/dev/null)
for expected_line in "hostname $address" 'user student' 'identitiesonly yes' 'stricthostkeychecking true' "hostkeyalias $alias" "userknownhostsfile $trust"; do
 printf '%s\n' "$effective" | grep -Fxq "$expected_line" || fail 'An existing SSH rule overrides the managed entry. Original configuration preserved; resolve the reported alias conflict.'
done
identities=$(printf '%s\n' "$effective" | sed -n 's/^identityfile //p')
[[ "$identities" == "$key" ]] || fail 'An SSH wildcard/include adds a different identity. Original configuration preserved; resolve the alias conflict.'
if ! cmp -s "$stage/config" "$config"; then cp -p "$config" "$config.before-workflow-$(date +%s)"; cp "$stage/config" "$config"; chmod 600 "$config"; fi
if [[ "$action" == setup ]]; then
 mp exec "$vm" -- sudo python3 "$installer" --authorize-key "$pub"
 mp exec "$vm" -- sudo python3 "$installer" --source-dir "$guest_stage"
 mp exec "$vm" -- rm -r "$guest_stage"
 "$code" --install-extension ms-vscode-remote.remote-ssh
fi
ssh -o ConnectTimeout=10 "$alias" true || fail 'SSH failed. Check key/passphrase/trust above; no host checks were disabled.'
echo 'Connection ready. Application status is separate (a scenario outage is preserved):'
mp exec "$vm" -- sudo /usr/local/sbin/lab-admin verify || echo 'Application check failed. Existing scenario/state preserved; no reset.'
# Remote installation is targeted explicitly, not a local-only recommendation.
"$code" --remote "ssh-remote+$alias" --install-extension srl-labs.vscode-containerlab@0.26.3
extensions=$("$code" --remote "ssh-remote+$alias" --list-extensions --show-versions)
printf '%s\n' "$extensions" | grep -Fxiq 'srl-labs.vscode-containerlab@0.26.3' || fail 'Remote Containerlab extension could not be verified. Retain the output; no manual fallback was assumed.'
"$code" --new-window --remote "ssh-remote+$alias" /home/student/labs/control/lab.code-workspace
echo 'VS Code launch requested. Complete any native Trust/Linux/passphrase dialogs, then use Tasks: Run Task → Lab: ...'
