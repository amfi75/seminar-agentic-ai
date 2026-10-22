# Troubleshooting

Run `bash scripts/lab.sh status` (Windows: `scripts/lab.ps1 status`) on your host.
A failed application check can be an intentional scenario, not broken SSH.

- Missing prerequisites: install Multipass, VS Code and OpenSSH using their
  normal platform instructions; check `multipass list` before rerunning setup.
- Partial installation: retain the VM and inspect the error; no automatic
  deletion or destructive recovery is performed.
- SSH identity change: verify an intentional rebuild through Multipass and use
  setup's explicit identity confirmation. Do not disable host-key checking.
- Existing OpenCode session: return to its terminal or quit it before opening
  another, changing profiles or installing convenience files.
- No provider/model: use OpenCode's normal authentication and `/models`. Your
  provider access is your own; never commit keys or print credential files.
- Proposal rejected: inspect target, protocol and native payload; review a new
  candidate after any source edit. Approval requires the exact reviewed ID.
- Network reset versus fresh trial: reset preserves history; fresh trial archives
  and replaces the management home, explicitly and with OpenCode stopped.
- Source changes: [maintenance guide](source-maintenance.md). Do not use an
  updater intended for a different distribution or overwrite your local edits.

The launchers have bounded waits and report unsafe reuse/collisions. If an error
persists, retain its non-secret message and your OS/architecture. Do not include
private keys, provider credentials or full saved agent profiles in reports.
