# Installation and daily use

Install [Multipass](https://canonical.com/multipass/install),
[VS Code](https://code.visualstudio.com/download) and its **Remote - SSH** extension.
Windows needs OpenSSH and supported virtualization. Linux needs supported Multipass.
On macOS, enable VS Code's `code` shell command or install it in Applications.
Allow 4 virtual CPUs, 8 GiB RAM and 40 GiB disk plus resources for your host.
Internet access is needed for the pinned tools and images; no local GPU is required.

Clone/unpack this source to a directory you own. In the host terminal:

```sh
bash scripts/lab.sh setup
```

Windows:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\lab.ps1 setup
```

Complete administrator, SSH-key passphrase and VS Code trust dialogs yourself.
Existing VMs and divergent files are preserved; diagnose reported collisions.
Do not delete a VM to retry. Generated per-VM credentials replace device vendor
bootstrap defaults. Configure your own authorized model/provider inside OpenCode.

## Work with the environment

Use `bash scripts/lab.sh open` (Windows: `scripts/lab.ps1 open`). In remote VS Code,
**Tasks: Run Task** exposes:

- **Start OpenCode:** stock agent on management, starting in `/home/agent`.
  Read `workspace/inventory.md`, select your provider/model and supply your own task.
  It can read and configure routers directly using native tools, without a broker
  proposal or approval step. Choose your own instructions and supervision.
- **Choose scenario:** introduce a routing incident or a performance impairment.
- **Check network:** test actual application reachability and administrative access
  restrictions. A deliberate scenario can make this fail while management works.
- **Advanced: workload controls:** inspect, pause or resume background traffic.
  If isolating a measurement, wait 20 seconds after pause and record that condition.
- **Reset network:** restore baseline via device management, retaining agent history.
- **Recover devices (preserve agent history):** rebuild devices out of band when
  management or credentials are broken. Stop OpenCode first. The home is retained;
  SSH/TLS trust and generated device credentials are refreshed.
- **Start fresh trial:** stop OpenCode, privately archive/verify the management home,
  then replace it. Provider configuration may need to be entered again.

The agent sees devices, credentials and services. Keep your operator workspace,
scenario implementation and earlier experiment evidence out of its context.
Router network administration excludes Linux/root and account-role administration;
container/VM controls are not available to the agent. Normal client/server SSH is
available for diagnostics. Independent measurements can be read in `~/observations`.
See [architecture](architecture.md) for the full human-facing design.

For the graph: **Containerlab → Running Labs → seminar → Graph → Graph
(TopoViewer)**. The separate UI folder is an editable example, not the running lab.

## Native device commands

In a management terminal (the same account/environment used by OpenCode):

```sh
ssh r1 'info from state interface ethernet-1/1 oper-state'
gnmic -a 10.79.0.12:57400 get --path '/interface[name=ethernet-1/1]' --type config --encoding json_ietf
```

For a small direct-write exercise, first check that the interface has no existing
description. If it does, record and restore that value instead of deleting it.
The generated `GNMIC_CONFIG` supplies credentials and verified TLS automatically:

```sh
gnmic -a 10.79.0.12:57400 set --update-path '/interface[name=ethernet-1/1]/description' --update-value '"practice-note"' --encoding json_ietf
gnmic -a 10.79.0.12:57400 get --path '/interface[name=ethernet-1/1]/description' --type config --encoding json_ietf
gnmic -a 10.79.0.12:57400 set --delete '/interface[name=ethernet-1/1]/description'
```

These are direct native operations, with no broker or special agent tool. Use
`ssh r1 'tools system configuration save'` when you want the resulting router
configuration to survive reboot. Do not save a temporary exercise unintentionally.

## Pause and stop

`bash scripts/lab.sh pause` suspends; `stop` shuts down; `open` resumes without
resetting the network. Windows uses the corresponding `scripts/lab.ps1` actions.
A router reboot loads saved startup configuration: save device configuration when
needed. Save editor work before disconnecting. Deletion/purge is not normal shutdown.

## Updating an older observer-only installation

Stop all agent sessions, then run `bash scripts/update.sh` for the selected VM
(Windows: `scripts/update.ps1`). This explicit update rebuilds devices and refreshes
native access while preserving the management home and model profile. Re-run setup
to refresh student workspace tasks if needed. Generated unchanged inventory and
legacy assignment are migrated; custom edits cause a collision report and are
preserved. Archive/move a reported custom file yourself before retrying, or reconcile
it with the current inventory. Do not remove your provider/model configuration.
If an old custom instruction/config still prescribes observer-only/broker use,
explicitly archive/remove that restriction before update; it is never silently
rewritten. [Troubleshooting](troubleshooting.md) covers recovery and trust.

Validation scope is described in the [README](../README.md#validation-scope).
