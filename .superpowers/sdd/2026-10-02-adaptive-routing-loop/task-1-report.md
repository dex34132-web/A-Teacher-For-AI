# Task 1 Report: TS routing core — helpers, knobs, evidence tracking, routing marker

**Status:** DONE
**Commit:** `2c54e06` feat(plugin): routing core - knobs, evidence tracking, engage mapping, routing marker

## What I implemented

All deliverables from the brief, verbatim:

1. **`school/plugin_source.py`**
   - Extended `node:fs` import to `{ existsSync, appendFileSync, readFileSync, writeFileSync, mkdirSync, statSync }` (wrapped across 2 lines to stay ≤100 chars; multi-line form still matches the test's `import \{ ([^}]+) \} from "node:fs"` regex).
   - `const executionStart = new Map<string, number>()` declared next to `promptRecalls`.
   - After `hooksEnabled()`: `ROUTE_TIMEOUT_MS = 10000`, `ROUTE_STATS_MAX_LINES = 2000`, `RoutingKnobs` interface, `DEFAULT_KNOBS` (wired to `HOOK_*` consts), `engageFor`, `normalizeSeverity`, `memoryRoot`, `clampNum`, `strList`, `knobsCache` (mtime-based), `readKnobs` (reads `routing.json`, per-key clamps, `statSync` cache), `appendEvidence` (`routing-stats.jsonl`, `mkdirSync`, trims to last 2000 lines when ≥2× cap, `appendFileSync`, never throws).
   - `recallForExecution`: `const knobs = readKnobs(ctx.worktree)` right after the `!bridge` guard; bridge call now uses `knobs.recall_threshold / knobs.hook_budget / knobs.hook_limit / knobs.hook_timeout_ms`.
   - `tool.execute.before`: after `hooksEnabled()` — skip/force gate (`skip_tools` match && !`force_tools` match → `executionRecalls.set(callID, null); return`), then `executionStart.set(callID, Date.now())`.
   - `tool.execute.after`: after `const marker` — computes `started` (fallback `Date.now()`), deletes from `executionStart`, reads `output.metadata.engagement` (string only), appends ` · routing: <engagement>` suffix to title, and calls `appendEvidence(..., { kind: "exec", tool, ms, ok, hits })`. Existing context-block logic untouched.
2. **`tests/unit/test_school_routing.py`** (new) — byte-for-byte verbatim copy of the brief's test file (programmatically verified `actual == block: True`).
3. **`tests/unit/test_school_plugin_hooks.py`** — updated `test_recall_uses_budget_constants`, which asserted the OLD contract (`confidence_threshold: HOOK_THRESHOLD` etc.). The plan explicitly replaces those usages with knobs, so the test now asserts the new contract: knob-driven params (`knobs.recall_threshold`, `knobs.hook_budget`, `knobs.hook_limit`, `knobs.hook_timeout_ms`) AND that `DEFAULT_KNOBS` still wires `recall_threshold: HOOK_THRESHOLD`, `hook_budget: HOOK_BUDGET`, `hook_limit: HOOK_LIMIT`, `hook_timeout_ms: HOOK_TIMEOUT_MS` (budget guarantees preserved via defaults).

## TDD Evidence

### RED (write failing tests, watch them fail)

Command:
```
$env:PYTHONIOENCODING='utf-8'; & ".venv\Scripts\python.exe" -m pytest tests/unit/test_school_routing.py -q
```
Result: **9 failed in 0.09s** — every test failed for the expected "feature missing" reason:
- `test_constants_present`: `assert 'const ROUTE_TIMEOUT_MS = 10000' in TS_PLUGIN_SOURCE`
- `test_engage_mapping`: `AssertionError: engageFor missing`
- `test_evidence_append_and_cap`: `assert 'function appendEvidence(' in TS_PLUGIN_SOURCE`
- `test_knobs_reader`: `assert 'function readKnobs(' in TS_PLUGIN_SOURCE`
- `test_knobs_used_in_recall_path`: `assert 'readKnobs' in block`
- `test_before_hook_skip_force`: `assert 'skip_tools' in block`
- `test_after_hook_tracks_evidence_and_start_time`: `assert 'kind: "exec"' in block`
- `test_routing_marker_suffix`: `assert 'routing: ' in block`
- `test_node_fs_imports_extended`: `assert {...} <= {'existsSync'}` (5 names missing)

### GREEN (implement, watch them pass)

Command:
```
$env:PYTHONIOENCODING='utf-8'; & ".venv\Scripts\python.exe" -m pytest tests/unit/test_school_routing.py -q
```
Result: **9 passed in 0.03s**.

## Verification results

| Check | Command | Result |
|---|---|---|
| TS extract + syntax | extract to temp `.ts`; `node --check` | exit 0 |
| Install parity | `python -m school install --force` + compare installed plugin to `TS_PLUGIN_SOURCE` | `MATCH` |
| Focused tests | `pytest tests/unit/test_school_routing.py -q` | 9 passed |
| Adjacent contract tests | `pytest tests/unit/test_school_plugin_hooks.py -q` | 29 passed (1 test updated to new contract) |
| Full suite | `pytest -q` | **2496 passed** (first run: 1 failed = old-contract hooks test; fixed as above, re-ran green) |
| ruff new/changed lines | `ruff check school/plugin_source.py tests/unit/test_school_routing.py tests/unit/test_school_plugin_hooks.py` | test files: All checks passed; `plugin_source.py`: exactly **16 E501 = baseline HEAD's 16 E501** (verified by running ruff on `git show HEAD:school/plugin_source.py`), all on pre-existing tool-implementation lines — **0 new errors**; automated diff check: 0 added lines >100 chars |
| Non-ASCII integrity | Python `repr()`/`ord()` check of `·`(183) ×3, `–`(8211) ×1, `—`(8212) ×23 | correct, matches expected counts |

## Files changed

- `school/plugin_source.py` (+117 / −6) — routing core helpers, knob-aware recall, hooks evidence/marker
- `tests/unit/test_school_routing.py` (new, 75 lines) — brief's 9 contract tests, verbatim
- `tests/unit/test_school_plugin_hooks.py` (+8 / −3) — budget-constants test updated to knob-aware contract

Staged only these three; `.opencode/` never staged. Known harmless `.git/worktrees/...` delete warnings appeared during commit (per environment notes).

## Self-review findings

- Verified test file is byte-identical to the brief's code block (scripted comparison, not by eye).
- Verified all brief-required identifiers present in `plugin_source.py` (14 substring checks, all OK).
- Diff read end-to-end: context-block logic in after-hook untouched; skip-gated calls get `executionStart` fallback `Date.now()` (ms≈0) — exactly what the brief's code specifies.
- Import line wrapped deliberately: unwrapped form is 102 chars (>100 ruff limit); wrapped form still satisfies the test's regex (greedy `[^}]+` backtracks over the space before `}`), confirmed by the passing test.
- YAGNI check: `ROUTE_TIMEOUT_MS`, `engageFor`, `normalizeSeverity`, `strList` are not yet called in TS — they are explicit brief deliverables consumed by Task 2 (`school_route` tool), so not speculative code.
- Line endings: repo uses `autocrlf=true` with LF blobs in HEAD; `git add` normalized the edited files, staged numstat shows only real content changes (117/6, 8/3, 75/0).

## Concerns

- **Minor:** `test_recall_uses_budget_constants` in `test_school_plugin_hooks.py` needed updating because the plan's Step 3 changes its subject behavior. Updated assertions are strictly stronger than before (knob params + default wiring). Flagging it since it's outside the brief's declared file list — but "full suite green" is a binding global constraint, and the old assertions contradicted the required implementation.
- **Note for Task 2:** `ROUTE_TIMEOUT_MS` and `engageFor`/`normalizeSeverity` are exported at module scope but unused so far — Task 2 must consume them (micro-call timeout; severity→engagement mapping) to keep TS linters/doc honest.

---

# Fix Report — Review Finding: `clampNum` coerces null/boolean knob values

**Status:** DONE
**Commit:** `c31fb54` fix(plugin): clampNum falls back to per-key default for null/boolean knob values

## What I changed

1. **`school/plugin_source.py`** — one line added at the top of `clampNum` (review-mandated, spec over plan-verbatim):

```ts
function clampNum(v: unknown, fallback: number, lo: number, hi: number): number {
  if (v == null || typeof v === "boolean") return fallback
  const n = Number(v)
  return Number.isFinite(n) ? Math.min(hi, Math.max(lo, n)) : fallback
}
```

Before: `Number(null) === 0` and `Number(true/false) === 1/0` fell through to the clamp, so `{"recall_threshold": null}` → 0 (not 0.2) and `{"hook_timeout_ms": null}` → clamped to 250ms (not 1500ms). Now null/undefined/boolean are treated as invalid and return the per-key default, matching the binding constraint "per-key defaults on invalid/missing values". Missing keys, non-numeric strings, and `strList` were already correct; only numeric keys were inconsistent.

2. **`tests/unit/test_school_routing.py`** — new test `test_clamp_num_defaults_on_null_and_boolean` (existing tests were checked first: grep confirmed no test pinned the old coercing behavior, so nothing needed updating). Coverage:
   - `clampNum` body contains `v == null` and `typeof v === "boolean"` guards;
   - guard appears **before** `Number(v)` (ordering proves no coercion happens first);
   - `recall_threshold: HOOK_THRESHOLD` + `HOOK_THRESHOLD = 0.2` → `recall_threshold: null` resolves to **0.2**;
   - `hook_timeout_ms: HOOK_TIMEOUT_MS` + `HOOK_TIMEOUT_MS = 1500` → `hook_timeout_ms: null` resolves to **1500**.

## TDD Evidence

**RED** — command: `& ".venv\Scripts\python.exe" -m pytest tests/unit/test_school_routing.py -q`
Output: `1 failed, 9 passed` with
`test_clamp_num_defaults_on_null_and_boolean ... assert "v == null" in body` → `AssertionError: assert 'v == null' in '  const n = Number(v)\n  return Number.isFinite(n) ? Math.min(hi, Math.max(lo, n)) : fallback'` — fails for the exact expected reason (guard absent, coercion intact).

**GREEN** — after the one-line fix, same command: `10 passed in 0.02s`.

## Re-verification

| Check | Command | Result |
|---|---|---|
| Focused tests | `pytest tests/unit/test_school_routing.py -q` | **10 passed** |
| Full suite (once) | `pytest -q` | **2497 passed** (2496 prior + 1 new) |
| TS extract + syntax | extract → `node --check` | exit 0 |
| Install parity | `school install --force` + compare vs `TS_PLUGIN_SOURCE` | `MATCH` |
| ruff | `ruff check tests/unit/test_school_routing.py` | All checks passed |
| ruff (pre-existing) | `ruff check school/plugin_source.py` | still exactly 16 baseline E501s — no new errors; automated check: 0 added lines >100 chars |
| Staged files | `git diff --cached --numstat` | `1 0 school/plugin_source.py`, `20 0 tests/unit/test_school_routing.py` (`.opencode/` untouched) |

## Concerns

None. The fix is the controller-approved spec-over-plan deviation; no other code path calls `clampNum` differently, and `strList`/missing-key paths were verified unaffected.

