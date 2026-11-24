---
name: memory-capture
description: "Synthesize verified findings into Basic Memory, or re-anchor a drifted (stale) note back to verified after running its Playbook."
---

# Memory Capture & Self-Healing

1. Resolve Git provenance (`repository`, `branch`, `commit`) via `.ai/scripts/get-developer-context.sh`.
2. Deduplicate first using `search_notes(project="main", query="<topic>", metadata_filters={"repository": "<repo>"})`.
3. **Synthesize or Re-anchor**:
   - When updating an existing or `stale` note after source code evolution, synthesize the latest verified logic in place, refresh `commit`, `code_paths`, and `code_symbols`, and set `status: verified`.
   - When capturing a new note, store it under `projects/<repo>/<memory_type>/` (`incident` | `debugging` | `solution` | `pitfall` | `practice` | `task-context`).
