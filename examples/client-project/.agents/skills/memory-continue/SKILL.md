---
name: memory-continue
description: "Lightweight on-demand memory retrieval: search repository-scoped notes, jump directly to code_paths to verify code_symbols inline, and reuse Playbook [probe]/[verify] commands."
---

# Memory Continue (Zero-Extra-Turn)

1. Search repository-scoped notes via hybrid retrieval (using the repository name from `AGENTS.md` or current workspace directory):
   ```python
   search_notes(project="main", query="<error code / class / topic>", metadata_filters={"repository": "<repo>"})
   ```
2. Read matched notes (`read_note` / `build_context(depth=2)`).
3. **Jump & Verify Inline**: Directly open the files listed in the note's `code_paths` (saving full-repo `grep/find` turns) and verify `code_symbols` inline:
   - Symbols intact (`CLEAN` / `MODIFIED_SAFE`): Reuse `## Playbook` (`[probe]`) to diagnose.
   - Symbols missing (`DRIFTED` / `stale`): Inspect latest code, run `## Playbook` (`[verify]`), and re-anchor the note via `memory-capture`.
