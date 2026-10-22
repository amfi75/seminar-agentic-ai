# Legacy VM bootstrap inputs

These files are required by the preserved original VM provisioning stages.
They are copied to the VM-side legacy bootstrap account, not installed as the
current management container's agent instructions. In particular, the historical
`labctl submit` text is not the current submission interface.

Current management uses stock OpenCode from `/home/agent`, ordinary generated
`workspace/inventory.md` and `workspace/task.txt`, and no custom instruction file.
The human uses the separate Review/Approve native-file workflow. See
[the current student guide](../../docs/start-here.md).
