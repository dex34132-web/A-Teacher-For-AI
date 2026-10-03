# SDD ledger — plan: docs/superpowers/plans/2026-10-03-school-rebrand.md

## Pre-flight scan

| Pair / task | Shared surface | Finding | Ruling |
|---|---|---|---|
| T1→T2 | pyproject.toml | T1 bulk-renames content (incl. `lerev` alias value → `school.cli:main`); T2 rewrites `[project.scripts]` and its RED test asserts post-bulk state (`lerev =` still present) | Sequential OK; T2 brief already written against post-bulk pyproject |
| T1→T3 | school/cli.py | T3 adds `_clean_stale_brand` using post-bulk `SchoolConfig` | Fixed in plan self-review (annotation + anchor) |
| T1→T4 | audit | T4 runs after all renames | OK |
| T1 self | bulk script | EXCLUDE set = .gitignore + rebrand spec + .opencode only; script lives in TEMP, never committed, run-once | Ephemeral script deleted after run (or left in temp, never staged) |
| T1 self | tests/unit/test_cli.py | T3 test target exists (verified: yes) | — |
| T1 env | pip install -e . | hatchling not installed; needs network or cache; console scripts needed by T2 | Ruling: if install fails offline, suite may run via cwd imports (`python -m pytest`) and T2 retries install; flag concern in report |
| Global vs rubric | test teachers | Plan prescribes exact test code everywhere; no assert-nothing tests; no verbatim logic duplication between tasks | Clean |

## Rulings
- Ruling: pip install failure due to no network is not BLOCKED — proceed with suite via cwd, retry in T2 — cost if wrong: T2 console-script verification delays.

## Task lines
Task 1: implementer DONE (commit 5db61c5, suite 2506, ruff 0 new, node --check 0, install resolves). Concerns: non-assertion comment/docstring edits (2), ruff baseline recount, suite 2506=2507-1 reconciled, .superpowers tracked, report uncommitted.
Task 1: minor (deferred): test_school_plugin_bridge removal of stale EVO_HOME comment (ratified, accuracy fix, 0 assertions)
Task 1: minor (deferred): test_school_identity_compat docstring rewrite (same class)
Task 1: minor (deferred): plugin_source invokeBridge comment still mentions legacy lerev.bridge alias (cosmetic staleness)
Task 1: minor (deferred): rebrand plan prose has mechanical SCHOOL_* -> SCHOOL_* self-reference (spec'd exclusion effect)
Task 1: complete (commits 3579262..5db61c5, review clean)
Task 2: Ruling: brief test line "assert "school =" not in text" was self-contradictory (plan defect) — implementer's "assert "teacher =" not in text" stands, matches spec final-state — cost if wrong: lerev alias could hide (mitigated: separate assert "lerev =" not in text in same test)
Task 2: minor (deferred): identity script assertions are substring-based, not TOML key-set (binding constraints covered)
Task 2: minor (deferred): worktree delete warnings dismissed without evidence in report (cosmetic)
Task 2: complete (commits 5db61c5..d868272, review clean)
Task 3: Ruling: brief's stale-name literals were bulk-corrupted to school.ts/school-routing (plan file was not in rename exclusion set); dispatch directive restored intentional teacher.ts/teacher-routing literals — cost if wrong: cleanup would delete the NEW plugin (catastrophic); implementer followed directive.
Task 3: Ruling: plan-file Task 4 text found bulk-corrupted pre-dispatch (gitignore block, git grep "teacher"->"school", allowlist classes, ledger/handoff notes) — controller fixed 6 edits before brief extraction.
Task 3: minor (deferred): skill-directory branch exercised only by unit fixture, not a live teacher-routing dir
Task 3: complete (commits d868272..4c6b7ab, review clean)
Task 4: implementer COMPLETE (777422f, pushed, 2507/0-new/MATCH/8-8-62). Audit: 79 hits all allowlisted, 0 product prose fixes. Swept controller plan-fix edits + ledger into commit (acknowledged).
Task 4: minor (deferred): plan-file brief-echo text fits none of 3 allowlist classes literally (unfixable by design)
Task 4: complete (commits 4c6b7ab..777422f, pushed, review clean)
Final review: 2 Important (memory tuple missing .teacher; spec count 13->11) + 1 Minor (workspace trail) + 7 deferred Minors triaged OK-KEEP.
Final fix wave round 1: 02393b0 (F1, F3, F2-line33); re-review: F1/F3 ADDRESSED, F2 NOT ADDRESSED (line 9).
Final fix wave round 2: 152fdf0 (F2 line 9); re-review: ADDRESSED, no new breakage.
PLAN COMPLETE (3579262..152fdf0, all reviews clean, all findings addressed or triaged OK-KEEP).
