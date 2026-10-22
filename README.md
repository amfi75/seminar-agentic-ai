# Agentic AI network lab — student edition

A self-contained local lab for exploring how an AI agent investigates network
problems. One Ubuntu VM contains a management workstation running stock OpenCode,
a client/server workload, and two Nokia SR Linux routers.

```text
Client ── R1 ── R2 ── Server
          management workstation: OpenCode + native diagnostics
```

You are the human operator. The agent has observer access and may propose native
configuration files; you separately review and approve exact changes. Built-in
routing and performance scenarios are included as ordinary local lab source.
You own the VM and can inspect that source. This is not an examination sandbox.

## Setup

Install Multipass and VS Code with Remote - SSH, and provide Internet access.
The lab requests 4 virtual CPUs, 8 GiB RAM and 40 GiB disk. Docker, Containerlab,
OpenCode and native clients are installed inside the VM. A local LLM is not
required. Configure your own authorized model access in OpenCode; no shared key,
secret service or external private repository is required.

From the cloned repository directory:

```sh
bash scripts/lab.sh setup
```

On Windows PowerShell:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\lab.ps1 setup
```

Follow [installation and daily use](docs/start-here.md). Administrator, SSH-key
passphrase and VS Code trust prompts are completed locally by you.

## Daily use

```sh
bash scripts/lab.sh open
bash scripts/lab.sh status
bash scripts/lab.sh pause
bash scripts/lab.sh stop
```

On Windows, use the same actions with `scripts/lab.ps1`. Open resumes the lab;
it does not reset an experiment. In remote VS Code, use **Tasks: Run Task → Lab:**
for OpenCode, network checks, scenarios, review/approval, reset and fresh trials.

There is no lecture controller, stepper, observer model or live teaching pane.
Ordinary OpenCode runs from `/home/agent` in management. Read the generated
`workspace/inventory.md` and `workspace/task.txt`; select an authorized model with
`/models`. Keep proposed native files in `workspace/` and submit them through the
human **Review proposed change** task, then the separate **Approve reviewed
change** task. A successful device write is not proof that the application works.

## Support and provenance

The original runtime has historical Apple-Silicon/ARM64 lab evidence. This
separated source distribution has export, dependency, archive and recorded
transfer checks; it has **not been freshly installed in a VM or desktop-qualified**.
Windows, Intel Mac and Linux paths are supplied without new platform qualification.
Do not interpret source checks as a successful end-to-end install on your machine.

`STUDENT-SOURCE-MANIFEST.json` records exact exported file hashes and a source
digest. `STUDENT-FILES.txt` lists the intended distribution files. Start with
[the guide](docs/start-here.md), [troubleshooting](docs/troubleshooting.md),
[architecture](docs/architecture.md) and [source maintenance](docs/source-maintenance.md).
Runtime credentials are generated privately on your own VM, never supplied in Git.
