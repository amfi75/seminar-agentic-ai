# Your network environment

Open **Tasks: Run Task**, then choose a **Lab:** task.

- **Start OpenCode** opens stock OpenCode on the management workstation. Give it
  your own task and choose your authorized model/provider. It can investigate and
  configure routers directly through native tools; there is no review/approval
  gateway. Decide for yourself how you supervise it.
- **Choose scenario**, **Check network** and **Advanced: workload controls** are
  student experiment controls outside the agent environment.
- **Reset network** restores the baseline through device management and preserves
  the agent home/history. If a device is inaccessible or its credentials changed,
  use **Recover devices (preserve agent history)** after stopping OpenCode.
  Recovery rebuilds devices out of band and restores access, preserving the home.
- **Start fresh trial** instead archives and replaces the management home. Stop
  OpenCode first. This is separate from reset/recovery.

The agent sees a management machine and operational inventory. Keep your scenario
controls, implementation source, historical experiments and this workspace outside
its context. It gets network-administration privileges, not container/VM control,
Linux host access on routers or permission to change its own device role.

For the running graph, use **Containerlab → Running Labs → seminar → Graph →
Graph (TopoViewer)**. The separate UI folder is an editing example.

On the host use `bash scripts/lab.sh pause` or `stop`; resume with `open`.
Ordinary open resumes devices without a harness baseline reset. A router reboot
uses that router's saved startup configuration, just as a normal device does;
save device configuration when you want it to survive a reboot.
