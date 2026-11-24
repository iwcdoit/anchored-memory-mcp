# Project Memory Workflow (AGENTS.md)

1. **Deterministic Rules**: Always follow architectural boundaries and coding standards tracked in Git (`AGENTS.md` / `CLAUDE.md`).
2. **Recall Before Implementation**: When troubleshooting production errors or designing cross-module changes, query Basic Memory via `search_notes` (`project="main"`, `metadata_filters={"repository": "pay-ledger"}`) and inspect relevant notes with `read_note`.
3. **Deduplicate Before Persisting**: Before saving a new troubleshooting case or architecture decision, run `search_notes` to avoid duplicates. Write structured Markdown notes under `projects/pay-ledger/<memory_type>/` with `repository: pay-ledger` metadata.
