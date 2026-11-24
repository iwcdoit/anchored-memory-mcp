---
name: memory-capture
description: "Synthesize the current state of an investigation or design thread into a single coherent Basic Memory note (deduplicate and rewrite in place rather than appending logs)."
---

# Memory Capture

1. Resolve Git provenance via `.ai/scripts/get-developer-context.sh`.
2. Deduplicate first using `search_notes(project="main", query="<topic>", metadata_filters={"repository": "<repo>"})`.
3. Synthesize the current verified state (replace outdated hypotheses inline rather than appending a changelog) and persist under `projects/<repo>/<memory_type>/` (`incident` | `debugging` | `solution` | `pitfall` | `practice` | `task-context`).
