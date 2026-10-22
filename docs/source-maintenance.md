# Source maintenance

This is an independent student repository with clean history. Shared runtime
files come from the upstream maintained lab; student documentation and the
source manifest identify this distribution. The exact selected content hashes
and aggregate digest are in `STUDENT-SOURCE-MANIFEST.json`; the recorded upstream
commit is context, not proof that every exported file came from that commit.

Keep your local changes in your own commits or patches. Do not run source updates
while an experiment is active. A source export/update must preserve divergent
tracked and untracked changes and stop for review rather than overwrite them.
Setup/open also preserve existing installations and edits. `scripts/update.sh`
and its PowerShell counterpart are full guest provisioning, not everyday open;
stop OpenCode and understand the change before deliberately using them.

The student file list bounds what is transferred during installation. Never add
credentials, profiles, generated device state or unrelated files into it.
Dependency versions/images are pinned in `network/versions.json` and Dockerfiles.
Any later platform/device updates need their own review and qualification.
