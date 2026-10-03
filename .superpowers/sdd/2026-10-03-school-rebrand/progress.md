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
