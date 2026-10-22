# Architecture and authority

A local Ubuntu VM runs Containerlab: client, two SR Linux routers, server and a
management workstation. Client application traffic uses the separate data path;
router management protocols use the management network. Existing HTTP/UDP
workloads, SNMP/gNMI collectors and Syslog provide ordinary observations.

The host's human student operator owns the VM. Local scenario/reset/workload
controls and exact native configuration approval are human actions. The
executing OpenCode account is non-root in management, with observer credentials,
no Docker socket, no human home and no operator credentials. SSH/TLS identities
are verified. No instruction or tool result grants additional write authority.

There is no lecture component or model observer. Model/provider configuration is
ordinary user-owned OpenCode configuration. The current generated inventory and
task live in `/home/agent/workspace`; credential/trust files live privately in
that account's `.lab`/`.ssh`. Historical bootstrap inputs in the source are not
custom instructions installed into the current management home.

The human can inspect all local source and VM state, including built-in scenarios.
This separation protects the agent's role; it does not hide scenario code from
a VM administrator. Baseline/device credentials are generated per VM and local
profiles/archives remain private runtime state, not repository content.
