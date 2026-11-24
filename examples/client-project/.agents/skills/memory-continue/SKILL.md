---
name: memory-continue
description: "Resume prior work or investigate issues by retrieving repository-scoped notes, checking code-anchor drift, and executing Playbook [probe] / [verify] steps."
---

# Memory Continue

1. Resolve current repository provenance with `.ai/scripts/get-developer-context.sh`.
2. Search repository-scoped notes via hybrid retrieval:
   ```python
   search_notes(project="main", query="<error code / class / topic>", metadata_filters={"repository": "<repo>"})
   ```
3. Read matched notes (`read_note` / `build_context(depth=2)`) and run a **Read-Time Drift Check** via `.ai/scripts/check-memory-drift.sh`:
   - `CLEAN` / `MODIFIED_SAFE`: Use the note's `## Playbook` (`[probe]`) to diagnose the issue.
   - `DRIFTED` (`stale`): Inspect current source code, run `## Playbook` (`[verify]`), and update/re-anchor the note via `memory-capture`.
