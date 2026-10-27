# Troubleshooting

- **Setup/open fails:** retain the VM and diagnostic output. Check Multipass service,
  available memory/disk, virtualization support, host OpenSSH and VS Code Remote -
  SSH. Complete administrator/passphrase/trust prompts locally. No automatic reset
  or destructive retry is performed.
- **Scenario breaks HTTP:** expected application failure is separate from management
  access. Use the stock agent/native tools to diagnose and change the network, then
  independently test client-to-server traffic. No proposal/approval task is needed.
- **Router unreachable or credentials changed:** stop OpenCode and run **Recover
  devices (preserve agent history)**. This recreates devices from the baseline,
  refreshes native access and retains your management home. Reset through device
  APIs may fail when management is broken; use recovery instead.
- **Permission denied:** network configuration is allowed, while router Linux/root,
  device identities/authorization and VM/container control are outside the issued
  role. Normal student infrastructure tasks run from the separate human workspace.
- **Host trust changed:** normal open preserves host verification. For an intentional
  VM rebuild run setup and verify the new VM identity. Never disable host/TLS checks.
  Device recovery refreshes device trust through the VM's provisioning path.
- **Update reports custom file/restriction:** your work is preserved. Stop agents,
  privately archive/reconcile the named old inventory/assignment or old custom lab
  policy yourself, then retry. Provider settings and sessions must not be removed.
- **Need an independent trial:** reset and device recovery preserve history. Use
  **Start fresh trial** only when you intend an archived replacement of the home.
- **New install reports success but agent unavailable:** inspect services and images;
  do not interpret exported source/dependency checks as a desktop qualification.

For daily commands and native access locations, see [the guide](start-here.md).
