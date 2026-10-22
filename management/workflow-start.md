# Your network lab

Open **Terminal → Run Task…** (or **Tasks: Run Task** in the Command Palette), then choose a **Lab:** task.

1. **Check network** to see the baseline. An intentional scenario can make this check fail.
2. **Choose scenario** when you want to start an experiment.
3. **Start OpenCode** to open the agent's interactive terminal. Read `workspace/inventory.md` and give it `workspace/task.txt`; choose an authorized model with `/models`.
4. **Review proposed change** to import a native file and inspect the exact candidate. This applies nothing.
5. **Approve reviewed change** only after your own review. Paste the full candidate ID, review it again, then type that ID to confirm. Application and independent verification are separate results.
6. **Reset network** to restore baseline. History stays intact. **Start fresh trial** instead archives and replaces the agent home; stop OpenCode first.

For the running graph, open **Containerlab → Running Labs → seminar (root) → Graph → Graph (TopoViewer)**. The reference file is `/var/lib/seminar-lab/runtime/topology.clab.yml`. The separate `ui` folder is an editing copy; viewing the reference does not require deployment.

**Advanced: workload controls** pauses/resumes traffic deliberately. Wait 20 seconds after pause before isolated measurements and declare that condition.

You are `student` in the VM. OpenCode is `agent` inside management. Keep this operator workspace, fault controls, and historical solutions outside the model's context. Native proposed files belong under `/home/agent/workspace`; the harness starts from `/home/agent` so its ordinary observer files remain in scope.

Save edits before leaving. On your host run `bash scripts/lab.sh pause` (Windows: the same `pause` action in `scripts/lab.ps1`). Resume later with `open`. Cold start after shutdown restores the baseline through the existing boot service; suspend/resume preserves current runtime state.
