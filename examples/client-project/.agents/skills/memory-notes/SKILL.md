---
name: memory-notes
description: "Author structured Basic Memory notes with YAML frontmatter, categorized [observation] facts, and [[Wiki-Link]] graph relations."
---

# Memory Notes Structure

Every note under `projects/<repository>/<memory_type>/` follows three layers:
1. **Frontmatter**: `title`, `repository`, `memory_type`, `status` (`draft` | `verified` | `promoted`), `branch`, `commit`, `developer_id`, `tags`.
2. **Observations**: Atomic categorized facts (`- [root_cause] ...`, `- [decision] ...`, `- [fix] ...`, `- [verification] ...`).
3. **Relations**: Directional graph edges (`- relates_to [[Target Note]]`, `- implements [[ADR Spec]]`).
