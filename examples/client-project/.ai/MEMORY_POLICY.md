# Engineering Memory Policy

## 1. Scope & Boundary
Use MCP Memory for durable engineering experience (troubleshooting, pitfalls, verified solutions, and cross-session task context). It complements—never replaces—code, tests, ADRs, or mandatory Git-tracked repository rules.

Retrieve relevant knowledge on demand. Never dump the entire memory store into context.

## 2. Deterministic Git Provenance
Before reading or writing memory, resolve repository and developer provenance via:

```bash
.ai/scripts/get-developer-context.sh
```

Use its JSON output (`repository`, `branch`, `commit`, `developer_id`, `created_at`) as authoritative metadata so notes across microservices remain cleanly scoped without manual configuration.

## 3. Retrieval (`memory-continue`)
When investigating a recurring issue, resuming prior work, or modifying a high-risk module, query the current repository first:

```python
search_notes(
    project="main",
    query="<error code, class name, module, or symptom>",
    metadata_filters={"repository": "<repository>"},
)
```

Use `build_context(url="memory://...", depth=2)` to traverse `[[Relations]]` when multi-hop context is needed.

## 4. Deduplication & Capture (`memory-capture` / `memory-notes`)
Before creating a note, search by error identifiers and module symptoms:
- **Match found**: update or synthesize into the existing note via `edit_note` / `write_note(overwrite=True)`.
- **No match**: create a new structured note under:

```text
projects/<repository>/<memory_type>/
```

### Allowed `<memory_type>` Categories
- `incident` — production/test incident symptoms, root causes, and fixes
- `debugging` — diagnostic paths, evidence, and ruled-out hypotheses
- `solution` — verified implementation patterns and technical solutions
- `pitfall` — recurring traps, framework caveats, and edge cases
- `practice` — team engineering practices and tooling workflows
- `task-context` — state and decisions for multi-session tasks

### Knowledge Lifecycle (`status`)
- `draft` — work-in-progress findings (clearly separating verified facts from hypotheses)
- `verified` — root cause or solution confirmed via test/production validation
- `promoted` — stable knowledge promoted into Git-tracked `docs/adr/` or `docs/development/conventions.md`

## 5. Safety & Sanitization
Never store passwords, tokens, private keys, raw production identifiers, or unfiltered customer logs. Retain only sanitized, reusable engineering facts and parameterized diagnostic steps.
