# Task 1 report — atomic rename: teacher → school (package, tests, packaging, docs)

Status: **DONE**
BASE: `3579262` (`docs(plans): school rebrand implementation plan (4 tasks)`)
Commit: **`5db61c5`** `refactor(rebrand): rename teacher to school across package, tests, packaging, and docs`
Suite: **2506 passed, 0 failed** (baseline 2507 — net −1 test, see "Suite totals" below)
Ruff: **0 NEW errors** (like-for-like BASE 226 → now 224; see "Ruff gate")
TS extract: `node --check` **exit 0**
Install: editable `school 2.6.0` installed, resolves to repo source

---

## Step 1 — Pre-state

```
> git rev-parse HEAD
3579262416a02dbbbfed812e60243f0a2064b83e

> git status --porcelain
?? .opencode/goals/state.json.sessions/7ca64e9e.../
?? .superpowers/sdd/2026-10-03-school-rebrand/
```

Branch: `main`. Only untracked items: `.opencode/goals` junk (as expected) + the task dir (brief/progress, tracked convention for SDD dirs).

## Step 2 — Enumerate renames

```
> git ls-files "*teacher*"
packaging/chocolatey/teacher.nuspec
packaging/homebrew/teacher.rb
packaging/windows/teacher-installer.nsi
scripts/teacher_bridge.py
teacher.spec
teacher/__init__.py
teacher/__main__.py
teacher/bridge.py
teacher/cli.py
teacher/config.py
teacher/discovery.py
teacher/mcp/__init__.py
teacher/mcp/__main__.py
teacher/mcp/config.py
teacher/mcp/server.py
teacher/plugin_source.py
tests/unit/test_teacher_cli_comprehensive.py
tests/unit/test_teacher_discovery_comprehensive.py
tests/unit/test_teacher_identity_compat.py
tests/unit/test_teacher_learn_persistence.py
tests/unit/test_teacher_packaging.py
tests/unit/test_teacher_plugin_bridge.py
tests/unit/test_teacher_plugin_hooks.py
tests/unit/test_teacher_routing.py
```

24 paths, all lowercase; **no additional unexpected paths** appeared (case-variant check with `git ls-files | Select-String -CaseSensitive` returned the same 24).

## Step 3 — git mv (24 renames)

All 14 `git mv` commands from the brief ran sequentially with `if ($?)` chaining; `git status --porcelain` after showed all 24 as `R  old -> new` (package dir = 11 files, scripts 1, spec 1, packaging 3, tests 8).

## Step 4/5 — Bulk replacement (run ONCE)

Script written to `C:\Users\dex34\AppData\Local\Temp\opencode\rebrand_school.py` (verbatim from brief; ephemeral, NOT committed, executed exactly once).

```
> $env:PYTHONIOENCODING='utf-8'; & ".venv\Scripts\python.exe" C:\Users\dex34\AppData\Local\Temp\opencode\rebrand_school.py
changed=135 excluded=2 skipped=0
```

Exclusion verification:

```
> git diff -- .gitignore
(empty ✓)
> git grep -c "teacher" -- docs/superpowers/specs/2026-10-03-school-rebrand-design.md
docs/superpowers/specs/2026-10-03-school-rebrand-design.md:18   (>0 ✓ — spec untouched)
> git grep -l "teacher_" -- tests
(empty ✓)
```

`.opencode/**`: never staged/committed (verified post-commit, `git show --name-only HEAD | Select-String .opencode` → empty).

## Step 6 — Semantic fallout A: memory-root chain (TDD)

### RED (6b) — `tests/unit/test_school_identity_compat.py`

Replaced whole `class TestMemoryMigration:` block with `class TestMemoryRootChain:` (4 tests, verbatim from brief).

```
> & ".venv\Scripts\python.exe" -m pytest tests\unit\test_school_identity_compat.py -q --no-header -p no:cacheprovider
collected 23 items
tests\unit\test_school_identity_compat.py .................FF....        [100%]
FAILED TestMemoryRootChain::test_existing_teacher_root_read_in_place
  AssertionError: assert .../.school/memory == .../.teacher/memory
FAILED TestMemoryRootChain::test_existing_lerev_root_read_in_place
  AssertionError: assert .../.school/memory == .../.lerev/memory
2 failed, 21 passed in 0.33s
```

(Exactly the predicted failure mode: current code copies legacy → `.school` and has no `.teacher` check.)

### Implement (6c–6e)

- `school/config.py`: replaced the whole `resolve_memory_dir` (copytree body deleted) with the chain version from the brief; removed `import shutil` (was only used by `copytree` — `git grep shutil school/config.py` → only the import line remained before removal).
- `school/bridge.py:58-60`: stale "legacy dirs are copied over non-destructively" comment → brief's chain comment.
- `school/plugin_source.py`: both chain literals (old lines 283 `memoryRoot` and 342 `hasMemoryRoot`) now read `[".school", ".teacher", ".lerev", ".evo"]`; `memoryRoot` fallback verified still `return resolve(worktree, ".school")`. Repo-wide grep confirms no other `(".school", ".lerev"` chain exists in code.

### GREEN (6f)

```
> pytest tests\unit\test_school_identity_compat.py -q --no-header -p no:cacheprovider
23 passed in 0.15s
```

## Step 7 — Semantic fallout B: bridge discovery school-only (TDD)

### RED (7a/7b)

- `tests/unit/test_school_discovery_comprehensive.py`: deleted `test_tier1_evo_home_fallback` and `test_tier1_school_home_takes_precedence` (the bulk-renamed name of the brief's `test_tier1_teacher_home_takes_precedence`); added `test_tier1_legacy_home_envs_not_honoured` (verbatim).
- `tests/unit/test_school_identity_compat.py`: deleted `test_lerev_home_env_honoured` + `test_evo_home_env_honoured`; added `test_legacy_home_envs_not_honoured` (verbatim) in `TestLegacyCompat`.

```
> pytest tests\unit\test_school_identity_compat.py tests\unit\test_school_discovery_comprehensive.py -q --no-header -p no:cacheprovider
FAILED TestLegacyCompat::test_legacy_home_envs_not_honoured
  AssertionError: ... tier='SCHOOL_HOME' bridge_path='...legacy_root\school\bridge.py'
FAILED TestBridgeDiscoveryCascade::test_tier1_legacy_home_envs_not_honoured
  AssertionError: ... tier='SCHOOL_HOME' ...
2 failed, 36 passed in 0.26s
```

### Implement (7c–7e)

- `school/discovery.py`: rewritten to the brief's exact post-state — school-only 4-tier cascade (`SCHOOL_HOME`, `shutil.which("school-bridge")`, `find_spec("school.bridge")`, `scripts/school_bridge.py`); all `_LEGACY_*` constants and alias loops deleted.
- `school/plugin_source.py` `discoverBridge` + doc comment: replaced with the brief's post-state (school-only tiers, single-element `for` loops kept — `where ${command}` / `which ${command}` intact). Left the unrelated helper/comment outside `discoverBridge` untouched.
- `tests/unit/test_school_plugin_bridge.py` `test_cross_platform_bridge_discovery`: docstring → `"""Plugin uses cross-platform PATH detection."""`; `assert "lerev-bridge" in TS_PLUGIN_SOURCE` → `not in`; kept `assert "school-bridge" in ...`.
- Step 7f: `test_plugin_has_legacy_fallbacks_only` allowlist untouched.

### GREEN (7g)

```
> pytest tests\unit\test_school_identity_compat.py tests\unit\test_school_discovery_comprehensive.py tests\unit\test_school_plugin_bridge.py -q --no-header -p no:cacheprovider
74 passed in 0.26s
```

## Step 8 — Editable install refresh

```
> & ".venv\Scripts\python.exe" -m pip uninstall -y ai-learning-engine teacher lerev school
Found existing installation: ai-learning-engine 0.1.0
Uninstalling ai-learning-engine-0.1.0: Successfully uninstalled
WARNING: Skipping teacher/lerev/school as it is not installed.

> & ".venv\Scripts\python.exe" -m pip install -e .
...
Successfully built school
Installing collected packages: school
Successfully installed school-2.6.0
```

Succeeded on first try (no hatchling/network fallback needed). Verification:

```
> python -c "import school; print(school.__version__)"        → 2.6.0
> import school.cli/bridge/mcp/plugin_source/discovery/config → imports ok
> school.__file__ / school.discovery.__file__ / find_spec('school.bridge').origin
  all = C:\Users\dex34\OneDrive\Documents\Teach\school\...   → installed MATCHES source (editable)
> pip show school → Name: school, Version: 2.6.0
> .venv\Scripts\school.exe version → school 2.6.0            (console-script smoke ✓)
> python -c "import lerev; print(lerev.__version__)" → 2.6.0  (legacy shim smoke ✓)
```

Console scripts present in `.venv\Scripts`: `school.exe`, `lerev.exe` (no `teacher.exe`). Task 2's scripts-rewrite tests deliberately NOT run/touched.

## Step 9 — TS syntax check

```
> extract TS_PLUGIN_SOURCE → C:\Users\dex34\AppData\Local\Temp\opencode\school-check.ts
C:\Users\dex34\AppData\Local\Temp\opencode\school-check.ts
> node --check C:\Users\dex34\AppData\Local\Temp\opencode\school-check.ts
exit=0
```

Ran after the final `plugin_source.py` edit (7d); no later edits to it.

## Step 10 — Full suite + fallout + ruff

### Run 1 (before the extra fallout fix)

```
> & ".venv\Scripts\python.exe" -m pytest -q --no-header -p no:cacheprovider
FAILED tests\unit\test_discovery.py::TestBridgeDiscovery::test_tier1_evo_home_env_fallback
  E assert None is not None
1 failed, 2505 passed in 128.32s
```

This is exactly the brief's predicted fallout class: `EVO_HOME` pin outside Step 7's files.

### Fix (per Step 10's prescribed treatment)

`git grep -ln "lerev-bridge\|LEREV_HOME\|EVO_HOME" -- tests` →
`test_discovery.py`, `test_school_discovery_comprehensive.py`, `test_school_identity_compat.py`, `test_school_plugin_bridge.py`.
The last three were already handled in Step 7. In `tests/unit/test_discovery.py` I deleted `test_tier1_evo_home_env_fallback` and added the same-pattern `test_tier1_legacy_home_envs_not_honoured`. Also applied the same greps for `copytree`/`copied` under `tests/` → zero `copytree` hits remain; no other migration-semantics assertions exist.

```
> pytest tests\unit\test_discovery.py tests\unit\test_school_plugin_bridge.py -q ...
41 passed in 0.21s
```

### Final full suite

```
> $env:PYTHONIOENCODING='utf-8'; & ".venv\Scripts\python.exe" -m pytest -q --no-header -p no:cacheprovider
============================= 2506 passed in 150.50s (0:02:30) =======================
```

**Suite totals: 2506 passed, 0 failed** (run twice: 123s and 150s runs, both 2506/0).

Why 2506 and not 2507 (baseline): Step 7 deleted 2 legacy-env pins in `test_school_discovery_comprehensive.py` and added 1 (`-1`); Step 6 replaced 3 migration tests with 4 chain tests (`+1`); Step 7 in identity_compat deleted 2 legacy-env tests and added 1 (`-1`)… net accounting: identity_compat 22 → 22 (+1 chain, −1 legacy-env), discovery_comprehensive −1, `test_discovery.py` 1 → 1 (rewrite in place). Net **−1** → 2507 − 1 = 2506. No test was deleted without a same-class replacement except the two discovery-comprehensive legacy pins, per brief.

### Ruff gate

Brief's command, current tree:

```
> & ".venv\Scripts\python.exe" -m ruff check school tests scripts lerev
Found 224 errors.   (E501 75, F401 63, W293 39, I001 23, F841 18, E731 2, B007 2, F541 1, E401 1)
```

Naive comparison against the same command at BASE gives 211, but that BASE number is **not like-for-like**: at BASE the package dir is `teacher/` (not in the checked paths) and the `school` path did not exist (E902). I created a throwaway worktree at BASE (`git worktree add <temp> 3579262`) and ran `ruff check teacher tests scripts lerev` there:

| | BASE (`teacher tests scripts lerev`) | now (`school tests scripts lerev`) | delta |
|---|---|---|---|
| total | **226** | **224** | **−2** |
| E501 | 75 | 75 | 0 |
| F401 | 63 | 63 | 0 |
| W293 | 39 | 39 | 0 |
| I001 | 23 | 23 | 0 |
| F841 | 18 | 18 | 0 |
| E731/B007/F541/E401 | 2/2/1/1 | 2/2/1/1 | 0 |
| SIM117 | 2 | 0 | −2 |
| E902 | 0 | 0 | 0 |

- **New errors: ZERO.** The −2 SIM117 are the nested-`with` legacy-env tests removed by the brief's Step 7/10 deletions (`test_discovery.py:40`, `test_teacher_discovery_comprehensive.py:72` at BASE).
- `plugin_source.py`: 16 E501 at BASE (`teacher/plugin_source.py`) → **16 E501 now** (`school/plugin_source.py`), same lines (offset by deletions, lengths −1/−2 from the rename). Matches the known pre-existing set exactly.
- Worktree removed afterwards (`git worktree list` no longer lists it).

### Residual `teacher` audit (post-bulk, excluding the 2 exclusion files)

```
> git grep -in "teacher" -- . ':!.gitignore' ':!docs/superpowers/specs/2026-10-03-school-rebrand-design.md'
school/bridge.py:58        # ... .school/.teacher/.lerev/.evo ...
school/config.py:105,111   docstring + for name in (".school", ".teacher", ".lerev", ".evo")
school/plugin_source.py:275,334  [".school", ".teacher", ".lerev", ".evo"]
tests/.../test_school_identity_compat.py:171,172,195  .teacher chain tests
```

All intentional: the legacy `.teacher` memory-root chain + its tests. No `TEACHER_*`, no `teacher-bridge`, no other hits.

## Step 11 — Commit

```
> git add -A -- ':!.opencode'
> git commit -m "refactor(rebrand): rename teacher to school across package, tests, packaging, and docs"
> git rev-parse --short HEAD
5db61c5
```

- 142 files changed, 2533 insertions(+), 2148 deletions(-).
- `git diff 3579262 HEAD -- .gitignore docs/superpowers/specs/2026-10-03-school-rebrand-design.md` → **empty** (both exclusions intact).
- `git show --name-only HEAD | Select-String .opencode` → **empty** (nothing from `.opencode/**` staged).
- Commit emitted the known harmless `failed to delete .git/worktrees/...` warnings (see below); commit succeeded.
- Post-commit `git status --porcelain`: only `?? .opencode/goals/...` remains.

---

## Deviations / notes for the controller

1. **Extra fallout test fixed (authorized by Step 10):** `tests/unit/test_discovery.py::TestBridgeDiscovery::test_tier1_evo_home_env_fallback` failed in the first full run; replaced with `test_tier1_legacy_home_envs_not_honoured` (same treatment the brief prescribes for `EVO_HOME` pins outside Step 7's files). RED observed (1 failed / 2505 passed) → GREEN.
2. **Two comment/docstring accuracy edits (no assertions changed):** removed the stale `# EVO_HOME is allowed as backward-compat` comment in `test_school_plugin_bridge.py::test_no_evo_references` (assertions kept identical), and updated the module docstring of `test_school_identity_compat.py` (legacy-compat list: dropped `LEREV_HOME`/`EVO_HOME` and "non-destructive memory migration" wording, which the brief's Steps 6/7 made false). Flag if you want these reverted.
3. **Ruff baseline caveat:** the brief's "16 pre-existing E501 in plugin_source.py" matches per-file counts exactly (16 → 16). The brief's command at BASE undercounts (211) because `teacher/` wasn't in its paths; true like-for-like baseline is 226 (`teacher tests scripts lerev`), now 224 → 0 new.
4. **Suite total 2506 vs baseline 2507:** explained above — net −1 test from the brief's own Step 6/7 test rewrites (3 migration tests → 4 chain tests = +1; 2 legacy-env pins deleted, 1 added in each of two files = −2). Totals reconcile: 2507 +1 −2 = 2506.
5. **Rename count:** 24 paths git-mv'd (brief said "15 paths" but its own enumeration plus the 11-file `teacher/` package = 24); **zero unexpected extra paths**.
6. **`.superpowers/**` included in the commit** (brief + progress + prior SDD docs bulk-renamed): matches repo convention where SDD artifacts are tracked; the exclusion set was applied exactly as specified (`.gitignore`, spec doc, `.opencode/**` only).
7. **This report file is intentionally left uncommitted** so the commit stays the single rebrand commit `5db61c5`; commit it separately if you want it tracked like prior task reports.
8. **Leftover worktree admin dirs:** `git prune`/`git worktree remove` printed `failed to delete '.git/worktrees/{base-ruff,baseline-wt,teacher-smoke}': Permission denied` (mine + two pre-existing). The temp worktree content is gone and `git worktree list` no longer lists it; the inert admin dirs are the known-harmless warning source the plan header pre-authorizes ignoring.
9. **Ephemeral script** `C:\Users\dex34\AppData\Local\Temp\opencode\rebrand_school.py` exists outside the repo, was run exactly once, and is not committed.

## Commands quick-reference (as run)

- mv: 14× `git mv` (Step 3 list) — all succeeded
- bulk: `& ".venv\Scripts\python.exe" C:\Users\dex34\AppData\Local\Temp\opencode\rebrand_school.py` → `changed=135 excluded=2 skipped=0`
- RED/GREEN runs: see Steps 6/7 sections (pytest outputs quoted verbatim)
- install: `pip uninstall -y ai-learning-engine teacher lerev school` then `pip install -e .` → `school-2.6.0`
- TS: extract `TS_PLUGIN_SOURCE` → `node --check` → `exit=0`
- suite: `pytest -q --no-header -p no:cacheprovider` → `2506 passed`
- ruff: `ruff check school tests scripts lerev` → `Found 224 errors` (BASE like-for-like 226, new = 0)
- commit: `5db61c5`
