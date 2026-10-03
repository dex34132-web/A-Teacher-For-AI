# Task 2 Report: `teacher_route` + `teacher_route_stats` plugin tools

**Status: DONE**
**Commit: `e555fb9` — feat(plugin): teacher_route (micro-model assess + lesson report) and teacher_route_stats tools**

## What was implemented

All inside `teacher/plugin_source.py` (`TS_PLUGIN_SOURCE`), per the brief:

1. **Helpers** (inside `Teacher` function, after `recallForExecution`, lines 448–535):
   - `interface RouteDecision { severity; engage; reason }`
   - `function routePrompt(situation): string` — 5-line JSON-only classifier prompt
     ("Respond ONLY with JSON", "Never choose engage none unless…"; ~60 tokens, ≤150 contract).
   - `function parseRouteDecision(text): RouteDecision | null` — extracts first `{…}` block,
     `normalizeSeverity` for severity; engage kept **only** when the response literally says
     `"none"`/`"skill"`/`"both"`, otherwise `engageFor(severity)` (never `none` when unsure —
     satisfies the controller's verbatim-none ruling); reason capped at 300 chars; returns
     `null` on any parse failure.
   - `async function microAssess(client, directory, situation)` — kill switch
     (`TEACHER_ROUTE === "0"` → `null`), scratch `session.create` → `config.get` →
     `small_model` ("provider/model" split) → `session.prompt` → text parts →
     `parseRouteDecision` → `finally` best-effort `session.delete`, raced against
     `ROUTE_TIMEOUT_MS` (10000) via `Promise.race`, outer `catch` → `null`.

2. **`teacher_route` tool** (after `teacher_diagnose`, lines 1150–1298):
   - Args: `mode, situation, severity?, lesson?, outcome?`.
   - **report**: validates bridge + lesson (≤1000 chars), outcome defaults to `helpful`,
     bridge `remember` with `tags: ["routing", outcome]`, outcome mapped
     helpful→`SUCCESS`, useless→`FAILURE`, neutral→`NEUTRAL`, content prefixed
     `Routing lesson (<outcome>): `; evidence row `kind: "report"`.
   - **assess**: `microAssess(ctx.client, ctx.directory, situation)`; fallback chain
     severity arg → default `medium` (source: `micro-model` | `self-rated` | `fallback`);
     evidence row `kind: "assess"` with severity/engage; returns
     `metadata: { engagement: decision.engage }` → after-hook appends
     ` · routing: <engagement>` automatically; `engage === "none"` gets the
     "no routing machinery needed" next-step instead of the skill-load hint.
   - Error paths return `metadata: { engagement: "failed" }` (report success: `"reported"`).

3. **`teacher_route_stats` tool** (lines 1300–1389): reads `routing-stats.jsonl` from
   `memoryRoot`, aggregates `kind: "exec"` rows per tool → `aggregates[tool] = {calls, avg_ms}`,
   `last_activity` = last row ts, `recent` = last `limit` rows (default 20, clamped 1–100),
   `knobs` via `readKnobs`, lessons via bridge `recall` query `"routing lesson"`
   (timeout `HOOK_TIMEOUT_MS`, limit ≤10); `metadata: { engagement: "stats" }`.

### Deviations from the brief's code block (deliberate, tests/constraints forced)
- **Function declarations instead of `const` arrows**: the brief's own tests assert
  `"function microAssess("` and `"function parseRouteDecision("` substrings, which the
  brief's `const microAssess = async (` code would not satisfy. Signatures unchanged.
- **`appendEvidence` calls wrapped in `if (hooksEnabled())`**: binding global constraint
  says `TEACHER_HOOKS=0` disables hooks/evidence/markers; brief's tool code called it
  unconditionally (Task 1 only ever called it from the gated after-hook).
- **Line wrapping** for ≤100 physical chars (outcomes ternary, lesson output, nextStep).
- One test line from the brief (`test_prompt_is_json_only`'s second assert, 120 chars)
  wrapped into a parenthesized `assert A or B` — semantics identical (required by
  "changed test files fully clean" ruff rule).

## TDD evidence

- **RED**: `pytest tests/unit/test_teacher_routing.py -q` after appending `TestRouteTools`
  → `9 failed, 10 passed` — all 9 new tests failed (tools absent, `function microAssess(`
  absent, prompt markers absent, block lookups raised `ValueError`); the 10 Task-1 tests
  stayed green, confirming the failures were caused by the missing implementation only.
- **GREEN**: after implementation → `19 passed in 0.03s`.
- **Focused set**: `test_teacher_routing.py + test_teacher_plugin_hooks.py +
  test_teacher_plugin_bridge.py + test_teacher_identity_compat.py` → `106 passed`.
  (3 failures appeared first from exact-tool-count/order assertions — see below — then passed.)
- **Full suite before commit**: `2506 passed in 142.64s` (2497 baseline + 9 new).

## Verification commands (both, after TS edits)

- Extract + `node --check` → `EXIT=0`.
- `teacher install --force` + parity → `MATCH`.
- Final re-check after all edits → `MATCH` (TS unchanged since; only test files edited after).

## Files changed

| File | Change |
|---|---|
| `teacher/plugin_source.py` | +330 lines: helpers + 2 tools (0 deletions) |
| `tests/unit/test_teacher_routing.py` | +65: `TestRouteTools` (9 tests, brief verbatim + 1 line-wrap) |
| `tests/unit/test_teacher_plugin_bridge.py` | `EXPECTED_OPENCODE_TOOLS` += 2 (order preserved), count 11→13 + rename, docstring 11→13; fixed 3 pre-existing ruff errors (unused `pytest` import, unused `main` import, I001) so the changed file is fully clean |
| `tests/unit/test_teacher_plugin_hooks.py` | tool count 11→13 (additive) |

Identity test needed **no** change (presence-only assertions, no exact count).

## ruff

- Baseline (HEAD versions, extracted to temp with repo pyproject): **19 errors** —
  16 pre-existing E501 in `plugin_source.py` + 3 pre-existing in bridge test.
- After changes: **16 errors** — the same 16 pre-existing `plugin_source.py` E501s only;
  all three test files clean. Python byte-check: lines >100 in `plugin_source.py` = 16
  before and 16 after (same lines, merely shifted) — **no new long lines**.

## Self-review findings

- Greedy `{[\s\S]*}` brace match in `parseRouteDecision` = brief's exact code; failure →
  `null` → fallback, so worst case degrades safely.
- `microAssess` timeout leaves `work` running after race loss; its `finally` still deletes
  the scratch session; a late resolve of a settled promise is a no-op.
- `ctx.client` / `ctx.directory` usage follows the brief; if the SDK shape differs,
  the `!c?.session?.create` guard returns `null` and the self-rated path takes over
  (verified by contract, not a live micro-call).
- Stats reads up to ~2001 JSONL lines (appendEvidence trims at ≥2× cap) — bounded.
- Descriptions are identical TS↔surface strings, domain-general ("for anything, not only
  coding") — Task 3 can copy verbatim.

## Incident (resolved, no data loss)

While getting a clean ruff baseline I ran `git stash --include-untracked`, which removed
6 sessions' `.opencode/goals/state.json.sessions/*/state.json*` files (17 files) and then
exited non-zero so the pop never ran. I restored all 17 files from the stash's untracked
tree (`stash@{0}^3`) via `git restore --worktree` (verified all 17 restored, untracked,
never staged), confirmed the stash's tracked diff was identical to the working tree, then
dropped the stash. The pre-existing `stash@{0}` "temp: stash before filter-branch" from
2026-09-13 is untouched. Baseline ruff was thereafter obtained by extracting HEAD file
versions to a temp dir — no further stashing. Only my 4 files were ever staged/committed.

## Concerns

- None blocking. Note for Task 3: description strings live in the `description:` blocks of
  both tools (lines 1151–1157 and 1301–1306) — copy verbatim.

---

# Fix Report — Review Finding: routePrompt token budget

**Status: DONE**
**Commit: `740d6c4` — fix(plugin): routePrompt truncates situation to 200 chars for <=150-token micro-call contract**

## What changed

- `teacher/plugin_source.py` (`routePrompt`, ~line 452): the situation is now truncated
  **inside the prompt builder** —
  `"You are a routing classifier for teacher tools. Situation: " + situation.slice(0, 200)`
  (line is 94 physical chars). The tool's own `slice(0, 500)` display cap on
  `args.situation` is untouched, per controller ruling: the binding `prompt ≤150 tokens`
  contract beats the brief's verbatim full-situation embedding.
- Worst case after the fix: fixed template literals (342 chars, measured by the test) +
  200-char situation + 4 join newlines ≈ **546 chars** (was ~846 with a 500-char
  situation) — inside the ≤700-char bound, well under 150 tokens.

## Covering test (TDD)

- Added `TestRouteTools::test_route_prompt_truncates_situation_within_budget` in
  `tests/unit/test_teacher_routing.py`, in the file's contract-test style: extracts the
  `routePrompt` body, asserts ` + situation.slice(0, 200)` is present, asserts NO
  untruncated `+ situation` remains (negative look-ahead regex), and pins the worst-case
  bound `len(template literals) + 200 <= 700`.
- **RED:** `pytest tests/unit/test_teacher_routing.py::TestRouteTools::test_route_prompt_truncates_situation_within_budget -q`
  → `1 failed` — `assert " + situation.slice(0, 200)" in body` (body shown still embedding
  raw `+ situation,`) — exactly the finding.
- **GREEN:** after the one-line fix → `49 passed` on the focused set.

## Commands + output

| Step | Command | Result |
|---|---|---|
| Focused | `pytest tests/unit/test_teacher_routing.py tests/unit/test_teacher_plugin_hooks.py -q` | **49 passed in 0.07s** |
| Full suite | `pytest -q` | **2507 passed in 133.74s** (was 2506 + 1 new) |
| TS extract + check | `python -c "…write teacher-extract.ts"; node --check …` | `CHECK_EXIT=0` |
| Install + parity | `python -m teacher install --force` + compare | `MATCH` |
| ruff | `ruff check teacher/plugin_source.py tests/unit/test_teacher_routing.py` | 16 errors — the same 16 **pre-existing** plugin_source E501s only; `test_teacher_routing.py` clean; added lines ≤100 chars (byte-checked: still exactly those 16 >100 lines) |

## Files changed (fix commit)

- `teacher/plugin_source.py` (+1/−1)
- `tests/unit/test_teacher_routing.py` (+18)

## Self-review

- Diff is exactly the truncation line + the one new test; only these 2 files staged.
- Template measurement in the test counts both quote styles (the JSON-only line is
  single-quoted), so the 700-char bound cannot silently undercount.
- `situation.slice(0, 200)` applies at prompt-build time regardless of caller caps —
  `microAssess` is its only caller.
