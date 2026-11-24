# Claude Code Memory Rules (CLAUDE.md)

1. **Deterministic Rules**: Always follow project architecture and coding conventions defined in Git (`CLAUDE.md` / `AGENTS.md`).
2. **Recall Before Coding**: When investigating errors, exceptions, or channel integrations, call `search_notes` (`project="main"`, `metadata_filters={"repository": "pay-ledger"}`) to retrieve historical solutions and troubleshooting notes.
3. **Deduplicate Before Writing**: Before persisting a new troubleshooting case or technical decision, run `search_notes` to avoid duplicates. Save validated notes under `projects/pay-ledger/<memory_type>/` with `repository: pay-ledger` frontmatter.
