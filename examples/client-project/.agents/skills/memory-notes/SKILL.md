---
name: memory-notes
description: "Author verifiable living memory notes with YAML code anchors (commit, code_paths, code_symbols), Observations, Playbook ([probe]/[verify]), and Relations."
---

# Living Memory Note Structure

Every note under `projects/<repository>/<memory_type>/` comprises four sections:
1. **Frontmatter & Code Anchors**: `title`, `repository`, `memory_type`, `status` (`draft` | `verified` | `stale` | `promoted`), `commit`, `code_paths`, `code_symbols`, `tags`.
2. **Observations**: Atomic categorized facts (`- [root_cause] ...`, `- [decision] ...`, `- [fix] ...`, `- [verification] ...`).
3. **Playbook**: Controlled diagnostic probes (`- [probe] <read-only SQL/log query>`) and regression commands (`- [verify] <unit test command>`).
4. **Relations**: Directional graph edges (`- relates_to [[Target Note]]`).
