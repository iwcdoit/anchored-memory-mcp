# Engineering Memory Policy (Lightweight & Zero-Extra-Turn)

## 1. Scope & Lightweight Principle
Use MCP Memory for durable engineering experience (troubleshooting, pitfalls, verified solutions, and cross-session task context). Retrieve relevant knowledge on demand and never preload the entire memory store into context.

## 2. Code Anchors & Zero-Turn Inline Verification
Every technical or troubleshooting note binds **Code Anchors** in its frontmatter (~70 tokens total, saving 3–5 full-repo search turns):
- `repository`: Target service repository name (declared in `AGENTS.md` or derived from workspace directory; run `.ai/scripts/get-developer-context.sh` only when exact Git commit/branch provenance is needed on write).
- `commit`: Git commit SHA at which the note was verified.
- `code_paths`: Core relative source file paths (e.g. `[pay-ledger-server/.../HotAccountShardingService.java]`).
- `code_symbols`: Core `ClassName#methodName` or error/config constants (e.g. `[HotAccountShardingService#routeSubAccount, ERR_ACCOUNT_LOCK_TIMEOUT]`).

## 3. Retrieval & Inline Drift Check (`memory-continue`)
1. Query current repository notes via `search_notes(project="main", query="...", metadata_filters={"repository": "<repo>"})`.
2. **Inline Drift Check (Zero Extra Tool Turn)**: After reading a matched note, directly open the source files listed in `code_paths` (skipping full-repo `grep/find`) and check whether `code_symbols` remain intact:
   - **CLEAN / MODIFIED_SAFE**: Target files and `code_symbols` are intact; use the note's `## Playbook` (`[probe]`) directly.
   - **DRIFTED (`stale`)**: Target file or symbol was refactored/deleted; inspect current source code, run `## Playbook` (`[verify]`), and re-anchor the note.
   *(Note: Offline batch drift inspection across all notes is handled out-of-loop via `python3 -m coding_memory.drift` with zero LLM token cost.)*

## 4. Deduplication, Playbook & 4-State Lifecycle (`memory-capture` / `memory-notes`)
Before creating a note, search by error identifiers and module symptoms:
- **Match found**: synthesize into the existing note via `edit_note` / `write_note(overwrite=True)` and refresh `commit`.
- **No match**: create a structured note under `projects/<repository>/<memory_type>/` (`incident` | `debugging` | `solution` | `pitfall` | `practice` | `task-context`).

### Executable `## Playbook` Section
- `- [probe] ...`: Read-only diagnostic queries (log search expressions or parameterized read-only SQL).
- `- [verify] ...`: Targeted unit/integration test commands to verify the mechanism still holds.

### 4-State Living Memory Lifecycle (`status`)
- `draft` — work-in-progress findings (separating verified facts from hypotheses)
- `verified` — validated and anchored to current `commit` + `code_paths` + `code_symbols`
- `stale` — code anchor drifted after refactoring; awaits re-verification and re-anchoring back to `verified`
- `promoted` — stable rule promoted into Git-tracked `docs/adr/` or `docs/development/conventions.md`
