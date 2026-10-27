# Source and maintenance

This is the student distribution of the shared environment. Shared runtime source
is maintained upstream and exported through an exact reviewed file list; human
student guides and source-transfer wrappers have student-specific ownership.
`STUDENT-SOURCE-MANIFEST.json` records authoritative per-file hashes and source
provenance; `STUDENT-FILES.txt` is the exact transfer list. Do not add local keys,
provider files, histories or runtime state to that list.

Keep your own changes in Git. Updates to generated distributions refuse conflicting
tracked, untracked or committed edits; reconcile work explicitly rather than
resetting or deleting it. Student source history is independent of instructor
history. The current network-access model replaces the initial observer-only
revision: devices can be configured directly, while infrastructure controls stay
outside the agent environment. See [architecture](architecture.md).

VM updates are explicit and can recreate devices. Stop agents first and retain
profiles/work. Baseline reset is different from out-of-band recovery and a fresh
trial; see [the guide](start-here.md). No provider/model request is selected or paid
for automatically. Generated credentials and trust remain private per-VM data.
