# Agentic AI network environment — student edition

A local environment for working with stock AI agents and real network-management
interfaces. One Ubuntu VM contains a management workstation, a client/server
workload and two Nokia SR Linux routers. You choose the task, agent instructions,
provider and level of supervision.

```text
client ── R1 ── R2 ── server       application traffic
           │     │
       management workstation    native SSH / gNMI / NETCONF

student controls → scenarios, measurements, reset and recovery
```

The agent can configure the network directly. There is no mandatory proposal
format or broker approval. It has network-administration access, without device
Linux/root, account-role administration, container or VM controls. Infrastructure
and experiment controls are for you, outside the agent's environment. There is
no lecture component or observer model.

## Setup

Install [Multipass](https://canonical.com/multipass/install),
[VS Code](https://code.visualstudio.com/download) and **Remote - SSH**. Allow
4 CPUs, 8 GiB RAM and 40 GiB disk for the VM. From this repository:

```sh
bash scripts/lab.sh setup
```

Windows PowerShell:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\lab.ps1 setup
```

Tools and the pinned stock OpenCode binary are installed inside the VM. Configure
your own model/provider access through OpenCode. No shared key or private service
is required. Follow the [installation and daily guide](docs/start-here.md).

## Daily use

```sh
bash scripts/lab.sh open
bash scripts/lab.sh status
bash scripts/lab.sh pause
bash scripts/lab.sh stop
```

Use **Tasks: Run Task → Lab: Start OpenCode** in remote VS Code. The agent starts
in `/home/agent`; `workspace/inventory.md` describes devices and native access.
Supply your own task. The shell and agent tools are ordinary off-the-shelf tools.
You operate scenarios and recovery from the separate student workspace.

An agent can break routing, access rules or its own management connection.
**Reset network** restores baseline using device management; **Recover devices**
rebuilds devices out of band while preserving agent history. **Start fresh trial**
archives and replaces the agent home. Stop OpenCode before recovery/fresh trial.
Open resumes devices without a harness reset; router reboots use saved startup
configuration, so save device configuration when persistence is intended.

See [architecture](docs/architecture.md), [troubleshooting](docs/troubleshooting.md)
and [source maintenance](docs/source-maintenance.md). Credentials and trust are
generated privately per VM and never supplied in Git. Students own the VM and can
inspect its implementation; the agent is deliberately given only an operational
view, with no promise that virtualization cannot be inferred.

## Validation scope

The direct-device revision was checked in an isolated Ubuntu ARM64 VM: direct
CLI/gNMI/NETCONF writes, permission boundaries, cold restart, recovery and profile
preservation. No paid model calls were made.
This is not Windows, Intel Mac or Linux-desktop qualification, a model-performance
benchmark, or a teaching-mode qualification. Exact files and hashes are in
`STUDENT-SOURCE-MANIFEST.json`; transfer uses `STUDENT-FILES.txt`.
