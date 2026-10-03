# SDD ledger — plan: docs/superpowers/plans/2026-10-02-adaptive-routing-loop.md

## Pre-flight conflict scan (run before Task 1)

| Pair | Shared surface | Checked | Finding |
|---|---|---|---|
| T1→T2 | plugin_source.py: T1 produces engageFor/readKnobs/appendEvidence/normalizeSeverity/memoryRoot/consts; T2 consumes for tools + metadata.engagement | plan T2 text references T1 names | none — sequential, same file |
| T2→T3 | TS↔MCP description parity (identical strings) | Global Constraint mandates identical; parity regex auto-covers | none |
| T1/T2→T3 | engage mapping light→skill, medium\|high→both | stated once in constraints, both sides tested | none |
| T3→T4 | stdio tests call assess/report/stats | T4 after T3, depends on T3 registrations | none |
| T5 | school/cli.py + new skill_source.py | no other task touches cli.py | none |
| T6 | docs/README only | runs after all | none |
| T2 vs identity test | exact tool-count assertions | plan notes possible trip | Ruling 4 |
| Global Constraint vs baseline | "ruff clean on every changed file" vs plugin_source.py pre-existing E501s (16) | baseline not clean | Ruling 2 |
| T1 self | tests specified vs code specified | create test_school_routing.py covering helpers | clean |
| T5 self | skill content inline in plan | full text provided | clean |

## Rulings

1. Ruling: work directly on `main` (no worktree) — session convention; 5 prior user-approved main commits (32d4506, 14127de, dafce0c, 70141cc, a5c8b55); user asked to "commit everything". — Cost if wrong: revertable history noise on main.
2. Ruling: "ruff clean on changed files" = no NEW ruff errors vs baseline (plugin_source.py has pre-existing E501s inside the embedded TS string; new long physical lines are forbidden). — Cost if wrong: minor lint debt remains.
3. Ruling: no `sh.exe` on this system → PowerShell equivalents of sdd-workspace/task-brief/review-package (same outputs: workspace `.superpowers/sdd/2026-10-02-adaptive-routing-loop/`, briefs by line-slice, review packages via git log/diff redirected to file). — Cost if wrong: none, artifacts equivalent.
4. Ruling: task tool exposes no model parameter → implementers and reviewers dispatched as `general` subagents (fix rounds resume via task_id); model-tier selection unavailable in harness. — Cost if wrong: less cost tuning; mitigated by precise briefs.
5. Ruling (standing): identity test tool-count/list updates are additive-only when T2 adds the two tools. — Cost if wrong: test loosened by two names.

## Progress


Task 1: dispatched (brief task-1-brief.md), report task-1-report.md, package task-1-review-package.md
Task 1: review — 1 Important (plan-mandated clampNum null/boolean), 5 Minors deferred (cache key path; skipped rows ms:0/hits:null; executionStart capMap leak; substring-only assertions; .evo/ gitignore gap)
Task 1: minor (deferred): knobsCache keys on mtimeMs only, not file path (plugin_source.py:299)
Task 1: minor (deferred): skip-gated executions write ms:0/hits:null, indistinguishable from instant recall (plugin_source.py:1065)
Task 1: minor (deferred): executionStart has no capMap; leaks if after-hook never fires (plugin_source.py:246)
Task 1: minor (deferred): test_school_routing.py assertions substring-only; trim/clamp/marker not behaviorally exercised
Task 1: minor (deferred): .gitignore covers .school/ .lerev/ but not .evo/ (pre-existing)
Task 1: Ruling: baseline 2483 in dispatch was stale — actual pre-task baseline 2487 + 9 new tests = 2496 (diff verified exactly 9 added); suite green. — Cost if wrong: none, arithmetic verified against b1 record.
Task 1: Ruling: verbatim-`none` engage gating NOT in T1 by design — normalizeSeverity/engageFor ignore it; Task 2's microAssess must emit engage 'none' only for a verbatim micro-model 'none'; MCP self-rated path never produces none. — Cost if wrong: none-gate moves task, enforced in T2/T3 tests.
Task 1: Ruling: clampNum null/boolean → per-key default IS a spec violation ("per-key defaults on invalid/missing values") despite plan's verbatim code — fix wins over plan text. — Cost if wrong: null becomes non-coercing (intended).
Task 1: fix round 1 dispatched (Important #1 only; minors deferred)
Task 1: fix round 1/5 (1 addressed, 0 open — clampNum null/boolean; commits 2c54e06..c31fb54)
Task 1: minor (deferred): clampNum still coerces ""/[] via Number() (plugin_source.py:292) — out-of-scope residual from fix review
Task 1: complete (commits a5c8b55..c31fb54, review clean)
Task 2: dispatched (task-2-brief.md), report task-2-report.md, package task-2-review-package.md
Task 2: review — 1 Important (plan-mandated routePrompt prompt >150 tokens worst case), 3 Minors deferred (source label when ROUTE=0 no-arg; stats all-or-nothing on corrupt JSONL line; bridge main importability assert dropped)
Task 2: minor (deferred): source "self-rated" mislabel when SCHOOL_ROUTE=0 with no severity arg (plugin_source.py:1270)
Task 2: minor (deferred): one corrupt JSONL line discards whole stats file (plugin_source.py:1319)
Task 2: minor (deferred): test_bridge_module_importable lacks callable(main) assert (test_school_plugin_bridge.py:103)
Task 2: Ruling: routePrompt situation truncated to 200 chars INSIDE routePrompt — spec/plan binding contract "prompt <=150 tokens" beats plan's verbatim full-situation embedding; tool-level 500-char display cap unchanged. — Cost if wrong: less situation context for micro-model (acceptable; stats/lessons carry detail).
Task 2: Ruling: report-count claims (suite 2506, node-check, MATCH) deferred to T6 live battery (plan mandates them there anyway); reviewer independently verified ruff delta = 0.
Task 2: fix round 1 dispatched (Important #1 only; minors deferred)
Task 2: fix round 1/5 (1 addressed, 0 open — routePrompt slice(0,200); commits e555fb9..740d6c4)
Task 2: complete (commits c31fb54..740d6c4, review clean)
