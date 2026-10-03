# Context Optimizer Design (Phase 7 / T7)

**Date:** 2026-10-03
**Status:** approved design (decisions answered by user in-session; spec pending user review before plan)

## Goal

Stop agents from ballooning context with raw file dumps. Every tool result the
model sees passes through a fast local skeletonizer that keeps structural
semantics (signatures, declarations, control-flow shape) and elides bodies and
boilerplate: a 50K-token read arrives as ~2K tokens with the logic map intact.

## User decisions (answered in-session)

1. **Interception surfaces: both.**
   - **OpenCode plugin:** `tool.execute.after` post-processes the results of
     *native* tools (read, grep, glob, bash, and every other tool) before the
     model sees them — zero workflow change, no duplicate tools.
   - **MCP mirror:** new `school_read` / `school_grep` tools on the MCP server
     for non-OpenCode clients (Claude, Cursor, …), producing already-skeletonized
     output server-side.
2. **Scope: everything the model sees** — all tool results on the plugin
   surface, subject to the trigger rule and guardrails below (user accepted
   guardrails explicitly).
3. **Languages: best coverage** — real tree-sitter grammars for the big-6
   (Python, TypeScript/JavaScript, Go, Rust, Java, C/C++) plus a universal
   heuristic skeleton (indentation/comment/string-aware) for every other file
   type. Nothing passes through raw once above threshold.
4. **Trigger: threshold ~1000 tokens.** Results estimated under ~1000 tokens
   (est. = `ceil(chars / 4)`, no tokenizer dependency) pass through untouched —
   zero latency on the common small-result case. Escape hatch: re-reading with
   `offset`/`limit` returns raw text because slices land under threshold.
5. **Parsing architecture: hybrid mix of both approaches** (user: "both mix"):
   - **MCP surface:** in-process tree-sitter (long-lived Python server — fast,
     native wheels, no subprocess).
   - **Plugin surface:** attempt AST-grade parsing via the existing Python
     bridge path (one payload per oversized result, inside the same budget/
     timeout discipline as recall); on timeout/failure, fall back to a pure-TS
     structural skeleton (dependency-free, in-process); total failure fails
     **open** (raw text) — compression may degrade, tool execution never breaks.

## Architecture

```
model sees result
   │
   ├─ plugin (OpenCode): tool.execute.after
   │     estimate tokens ── <1000? ── pass raw (no work, no marker)
   │     ≥1000 ── bridge AST (big-6) ── fail/timeout ── TS heuristic skeleton
   │                │ success                                   │
   │                └─── both produce the same skeleton contract ┘
   │     append footer `[school ctx: <in>→<out> tokens]` when compressed
   │
   └─ MCP (other clients): school_read / school_grep
         same threshold; in-process tree-sitter big-6, heuristic fallback
         output already skeletonized + same footer
```

**Skeleton contract (both surfaces, contract-tested not byte-tested):**
- Keep: file/module header, imports/requires, all declarations (functions,
  classes, methods, exports) with full signatures, decorators/annotations,
  docstring first lines, control-flow skeleton lines (if/for/return keywords
  with their conditions), and `// …`/`# …` elision markers naming what was
  dropped with its size (e.g. `# … fetch_user() — 42 lines`).
- Drop: function/method bodies beyond the first line, block comments and
  boilerplate, blank runs, license banners, imports not referenced anywhere in
  the kept skeleton.
- JSON/tool payloads below threshold are untouched by construction; above
  threshold they get the *heuristic* path only (never AST-mangling), and any
  parse doubt ⇒ fail open.

## Guardrails (spec-level)

- Fail open everywhere: parser/bridge/timeout errors ⇒ raw result + no footer.
- Never touch a result that is an error message (tool errors pass raw).
- Never modify tool *inputs* — outputs only.
- One footer max per result; footer itself excluded from downstream estimates.
- Budget: bridge parse capped at 2000 ms (separate constant, not the recall
  budget); heuristic path must stay under ~50 ms per result (no I/O).
- Kill switch: `SCHOOL_CTX=0` disables compression entirely (raw world);
  independent of `SCHOOL_HOOKS`.

## Non-goals

- Not a tokenizer/caching layer; no embedding or semantic indexing.
- No byte-parity between surfaces (different tools, same contract).
- No compression of messages the *user* sees (terminal rendering untouched).
- No change to memory storage, routing, or skill systems (Phases 1–6).

## Testing approach (for the plan)

- Contract tests per language corpus (big-6 + 2 heuristic-only samples):
  signatures retained, bodies elided, footer format, threshold boundary
  (999/1001 tokens), fail-open paths, `SCHOOL_CTX=0`.
- MCP: stdio integration for `school_read`/`school_grep` (skeletonized output,
  threshold, raw small reads, unknown-path errors).
- Plugin: source-contract tests (hooks wiring, constants, footer) in the
  existing style; live check = a real oversized read observed compressed.

## Risks

- **Model confusion** from missing details → mitigated by elision markers
  naming dropped symbols + offset/limit escape hatch.
- **Latency** on the plugin bridge path → mitigated by threshold gate,
  2000 ms cap, heuristic fallback.
- **tree-sitter wheels on Windows** for big-6 → pin versions, heuristic
  fallback keeps the feature useful if a wheel is missing.
- **Scope creep** into reading files the agent never requested → outputs only.

## Build order

After Phase 1 adaptive-routing T3–T6 complete (same package, same test
conventions). Name everything `school_*` from day one.
