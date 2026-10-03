# Task 3 Report: `school install --force` removes stale previous-brand artifacts

**Status:** COMPLETE
**Commit:** `4c6b7ab` — `feat(cli): school install removes stale previous-brand plugin and skill artifacts`
**Date:** 2026-10-03

## Deviation from brief file (instruction-corrected)

The brief file (`task-3-brief.md`) had been bulk-renamed by Task 1's `teacher→school` rename pass: its code blocks referenced `"school.ts"` / `"school-routing"` as the stale artifacts, which would (a) delete the NEW post-rebrand plugin name and (b) contradict its own assertion `(plugins_dir / "school.ts").exists()`. Its Step 5 also checked the same path `school.ts` for both `False` and `True`.

Per the task directive, the intentional stale-artifact literals are `"teacher.ts"` and `"teacher-routing"`, and the test is named `test_install_removes_stale_teacher_artifacts`. Those corrections were applied to the code and test; everything else (structure, placement, flow) follows the brief verbatim.

## Step 1-2: RED (failing test)

Added `test_install_removes_stale_teacher_artifacts` to `tests/unit/test_cli.py` (class `TestCLI`).

```
& ".venv\Scripts\python.exe" -m pytest "tests\unit\test_cli.py::TestCLI::test_install_removes_stale_teacher_artifacts" -q --no-header -p no:cacheprovider
```

```
tests\unit\test_cli.py F                                                 [100%]
____________ TestCLI.test_install_removes_stale_teacher_artifacts _____________
tests\unit\test_cli.py:103: in test_install_removes_stale_teacher_artifacts
    assert not stale_plugin.exists(), "stale teacher.ts must be deleted"
E   AssertionError: stale teacher.ts must be deleted
E   assert not True
=========================== short test summary info ============================
FAILED tests/unit/test_cli.py::TestCLI::test_install_removes_stale_teacher_artifacts
============================== 1 failed in 0.26s ===============================
```

Expected failure observed: `stale teacher.ts must be deleted`. RED confirmed.

## Step 3: Implementation

In `school/cli.py`:

- Added `_clean_stale_brand(config: SchoolConfig, verbose: bool = True) -> bool` after `_clean_legacy_plugin` (and its legacy alias). It deletes `opencode_plugins_dir() / "teacher.ts"` (if file) and `opencode_plugins_dir().parent / "skills" / "teacher-routing"` (if dir), both wrapped in `try/except OSError`, returning whether anything was removed.
- Called `_clean_stale_brand(config)` in `_cmd_install` immediately after `_clean_legacy_plugin(config)` — i.e. before the already-installed/`--force` check, so cleanup runs on every install regardless of `--force`.

Literals `"teacher.ts"` and `"teacher-routing"` are intentional stale-artifact names (not renamed).

## Step 4: GREEN

```
& ".venv\Scripts\python.exe" -m pytest tests\unit\test_cli.py -q --no-header -p no:cacheprovider
```

```
collected 6 items
tests\unit\test_cli.py ......                                            [100%]
============================== 6 passed in 0.07s ==============================
```

## Step 5: Live reinstall + artifact verification

Pre-state on this machine (checked before the run):

```
Test-Path ~\.config\opencode\plugins\teacher.ts      → True   (stale artifact present)
Test-Path ~\.config\opencode\skills\teacher-routing  → False  (not present)
Test-Path ~\.config\opencode\plugins\school.ts       → True
```

Command and output:

```powershell
$env:PYTHONIOENCODING='utf-8'
& ".venv\Scripts\python.exe" -m school install --force
```

```
School Installer
----------------------------
Python: 3.14 OK
OpenCode config: C:\Users\dex34\.config\opencode\opencode.jsonc
Removed stale previous-brand plugin: C:\Users\dex34\.config\opencode\plugins\teacher.ts
Plugin installed: C:\Users\dex34\.config\opencode\plugins\school.ts
Bridge: installed_module OK

Installation complete!
Restart OpenCode to use School.
```

Post-state (teacher.ts-gone proof):

```
teacher.ts exists: False
school.ts exists: True
teacher-routing exists: False
```

`~/.config/opencode/plugins/teacher.ts` was genuinely present and the live run deleted it (verbose removal line above). `skills/teacher-routing/` did not exist on this machine, so only the plugin removal was exercised live (the skill-directory branch is covered by the unit test fixtures).

### Byte-identity (MATCH) proof

```powershell
& ".venv\Scripts\python.exe" -c "from school.plugin_source import TS_PLUGIN_SOURCE; from pathlib import Path; ip = Path.home() / '.config/opencode/plugins/school.ts'; print('MATCH' if ip.exists() and ip.read_text(encoding='utf-8') == TS_PLUGIN_SOURCE else 'MISMATCH')"
```

```
MATCH
```

## Step 6: TS syntax check

```powershell
node --check $env:USERPROFILE\.config\opencode\plugins\school.ts
```

```
node --check exit: 0
```

Exit code 0, no diagnostics.

## Step 7: Full suite

```
& ".venv\Scripts\python.exe" -m pytest -q --no-header -p no:cacheprovider
```

```
collected 2507 items
...
====================== 2507 passed in 180.59s (0:03:00) =======================
```

**2507 passed** = baseline 2506 + 1 new test. 0 failed, 0 skipped, 0 errors.

## Ruff

| Scope | Baseline | After | Delta |
|---|---|---|---|
| `ruff check school tests` | 224 | **224** | **0** |
| `ruff check school` | 16 (pre-existing E501 in `school/plugin_source.py`) | 16 | 0 |
| `ruff check tests` | 208 | 208 | 0 |
| `ruff check school/cli.py tests/unit/test_cli.py` | 2 (F401 `json`, E501 line 55 — verified pre-existing by `git stash` + re-run at HEAD) | 2 | 0 |

**0 new ruff errors.** The 2 hits in `tests/unit/test_cli.py` are the pre-existing unused `json` import (line 5) and the pre-existing long `def test_install_skip_existing` signature (line 55); both were present at `d868272` and neither was touched by this change. `school/cli.py` itself is clean.

## Commit

```
[main 4c6b7ab] feat(cli): school install removes stale previous-brand plugin and skill artifacts
 2 files changed, 63 insertions(+)
```

- Staged: `school/cli.py`, `tests/unit/test_cli.py` only (`.opencode/**` not staged; `.superpowers/progress.md` and task reports left unstaged as out of scope).
- The `error: failed to delete '.git/worktrees/...'` warnings during commit are the known harmless stale-worktree-prune warnings.

## Files changed

- `school/cli.py` — added `_clean_stale_brand` (26 lines) + one call site in `_cmd_install`
- `tests/unit/test_cli.py` — added `test_install_removes_stale_teacher_artifacts`
