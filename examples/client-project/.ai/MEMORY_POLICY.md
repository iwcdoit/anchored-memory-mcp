# Engineering Memory Policy

## 1. Scope & Boundary
Use MCP Memory for durable engineering experience (troubleshooting, pitfalls, verified solutions, and cross-session task context). It complements—never replaces—code, tests, ADRs, or mandatory Git-tracked repository rules.

Retrieve relevant knowledge on demand. Never dump the entire memory store into context.

## 2. Deterministic Git Provenance & Code Anchors
Before reading or writing memory, resolve repository and developer provenance via:

```bash
.ai/scripts/get-developer-context.sh
```

Every technical or troubleshooting note must bind **Code Anchors** in its frontmatter:
- `commit`: Git commit SHA at which the note was verified
- `code_paths`: Core relative source file paths (e.g. `[pay-ledger-server/.../HotAccountShardingService.java]`)
- `code_symbols`: Core `ClassName#methodName` or error/config constants (e.g. `[HotAccountShardingService#routeSubAccount, ERR_ACCOUNT_LOCK_TIMEOUT]`)

## 3. Retrieval & Read-Time Drift Verification (`memory-continue`)
1. Query current repository notes via `search_notes(project="main", query="...", metadata_filters={"repository": "<repo>"})`.
2. **Read-Time Lazy Drift Check**: When a retrieved note contains `code_paths` and `code_symbols`, verify its freshness against the local Git working tree via `.ai/scripts/check-memory-drift.sh`:
   - `CLEAN`: Source files unchanged since `commit`; adopt directly.
   - `MODIFIED_SAFE`: Files evolved, but all `code_symbols` remain intact; adopt while reviewing recent diffs.
   - `DRIFTED` (`stale`): Target file or symbol moved/deleted; inspect current source code and run the note's **`## Playbook` (`[verify]`)** before adopting, then re-anchor the note.

## 4. Deduplication, Playbook & 4-State Lifecycle (`memory-capture` / `memory-notes`)
Before creating a note, search by error identifiers and module symptoms:
- **Match found**: synthesize into the existing note via `edit_note` / `write_note(overwrite=True)` and refresh `commit`.
- **No match**: create a structured note under `projects/<repository>/<memory_type>/` (`incident` | `debugging` | `solution` | `pitfall` | `practice` | `task-context`).

### Executable `## Playbook` Section
Include a `## Playbook` section with controlled, repeatable steps:
- `- [probe] ...`: Read-only diagnostic queries (log search expressions, parameterized read-only SQL, or `grep` probes).
- `- [verify] ...`: Targeted unit/integration test commands to verify the mechanism still holds.

### 4-State Living Memory Lifecycle (`status`)
- `draft` — work-in-progress findings (separating verified facts from hypotheses)
- `verified` — root cause or solution validated and anchored to current `commit` + `code_paths` + `code_symbols`
- `stale` — code anchor drifted after source refactoring; awaits re-verification via `Playbook [verify]` and re-anchoring back to `verified`
- `promoted` — stable rule promoted into Git-tracked `docs/adr/` or `docs/development/conventions.md`

## 5. Safety & Sanitization
Never store passwords, tokens, private keys, raw production identifiers, or destructive commands in `## Playbook`.
