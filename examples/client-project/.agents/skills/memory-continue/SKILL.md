---
name: memory-continue
description: "Resume prior work or investigate issues by rebuilding context from Basic Memory via search_notes, build_context, and recent_activity."
---

# Memory Continue

1. Resolve current repository provenance with `.ai/scripts/get-developer-context.sh`.
2. Search repository-scoped notes first:
   ```python
   search_notes(project="main", query="<error code / class / topic>", metadata_filters={"repository": "<repo>"})
   ```
3. Traverse related notes via `build_context(url="memory://<permalink>", depth=2)` and read full details with `read_note`.
