# Install and use the local lab

Install [Multipass](https://canonical.com/multipass/install) and
[VS Code](https://code.visualstudio.com/download), with its **Remote - SSH**
extension. Windows requires its OpenSSH client and supported virtualization;
Linux requires a working supported Multipass installation. macOS users can use
VS Code's **Shell Command: Install 'code' command in PATH**. The launcher also
recognizes the usual macOS application installation.

Clone or unpack the student source into a directory you own. Allow room for a
4-CPU,8-GiB,40-GiB VM plus your host applications. Do not run several heavy lab VMs
at once on a constrained laptop. A local language model or GPU is not required.

## First setup

In your host terminal, from the repository:

```sh
bash scripts/lab.sh setup
```

On Windows PowerShell:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\lab.ps1 setup
```

Setup creates or safely recognizes the named VM, installs its tools, configures
a standard `seminar-lab` SSH connection and opens the human workspace. An existing
VM or divergent edits are preserved; follow the reported diagnostic rather than
deleting a VM to retry. Complete administrator/passphrase/trust prompts locally.
A default vendor bootstrap password in provisioning is replaced with generated
per-VM credentials; it is not a student model-provider credential.

## Open and operate

Run `bash scripts/lab.sh open`, or `scripts/lab.ps1 open` on Windows. In remote
VS Code, **Tasks: Run Task** provides:

- **Lab: Start OpenCode** — stock agent as a non-root management user. Configure
  your own provider through its normal login/model selection. No model request
  or paid provider is selected automatically by this repository.
- **Lab: Check network** — explicit client-to-service and access-rule checks;
  a deliberately broken scenario can fail while management still works.
- **Lab: Choose scenario** — routing incident, delay/jitter, loss or rate limit.
- **Lab: Review proposed change** — import an existing native gNMI/NETCONF file
  from `/home/agent/workspace`, inspect the resulting exact candidate.
- **Lab: Approve reviewed change** — separately confirm that full candidate ID;
  then check observed application behavior, not only configuration readback.
- **Lab: Reset network** — restore the baseline while preserving agent history.
- **Lab: Start fresh trial** — explicitly archive and replace the management
  profile; stop OpenCode first. This is different from an ordinary reset.
- **Lab: Advanced: workload controls** — explicitly pause/resume background traffic.

For topology, use **Containerlab → Running Labs → seminar → Graph → Graph
(TopoViewer)**. The separate editable UI lab is not the running reference lab.

OpenCode starts in `/home/agent`, where ordinary observer trust/config files are
in scope. Read generated `workspace/inventory.md` and `workspace/task.txt`.
The human operator owns Docker/control access; the executing agent does not.
The old `network/agent-inputs/` files are VM bootstrap inputs, not current
management instructions. See its [bootstrap note](../network/agent-inputs/README.md).

## Pause, stop and recovery

`bash scripts/lab.sh pause` suspends the VM; `stop` shuts it down. `open` starts
or resumes it without reset. Windows uses the corresponding `scripts/lab.ps1`
actions. Save editor work before disconnecting. VM deletion/purge is not a normal
shutdown operation. Consult [troubleshooting](troubleshooting.md).

This source split is not freshly VM-installed or desktop-qualified. See
[the README support statement](../README.md#support-and-provenance).
