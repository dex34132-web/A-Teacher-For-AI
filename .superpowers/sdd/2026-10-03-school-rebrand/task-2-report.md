# Task 2 Report: Console entry points + CLI/bridge smoke

**Status:** DONE_WITH_CONCERNS
**Commit:** `d868272` — `feat(cli): add school and school-bridge console scripts; drop teacher/lerev aliases`
**Files changed (exactly 2):** `pyproject.toml`, `tests/unit/test_school_identity_compat.py`
**Suite:** 2506 passed in 188.37s — matches Task 1 baseline exactly, 0 new failures.
**Ruff:** 0 errors on changed files; baseline scope `school tests scripts lerev` = 224 errors = exact baseline, 0 new.

---

## Concern #1 (deviation from brief, verbatim code was impossible)

The brief's Step 1 test contained a self-contradiction:

```python
assert 'school = "school.cli:main"' in text   # requires substring "school ="
assert "school =" not in text                  # forbids substring "school ="
```

Both cannot pass. I implemented the test verbatim first and captured proof (below), then
applied a one-word correction `assert "school =" not in text` → `assert "teacher =" not in text`.

Why `teacher`: the controller's own instructions state RED reasons are "lerev alias present,
school-bridge missing" (only two — not three) and expected final state is "no teacher/lerev
keys". With the verbatim `school =` assertion the test could never go GREEN. The corrected
assertion matches the stated final state exactly. Flagged for review.

Secondary note: the brief's bridge pipe `'{\"command\": \"status\"}'` uses backslash escapes
inside PowerShell single quotes (passed through literally → invalid JSON). Piped the
PowerShell-correct `'{"command": "status"}'` instead; JSON round-trip verified below.

---

## Step 1 — RED (test rewritten verbatim, before pyproject edit)

Command:
```powershell
& ".venv\Scripts\python.exe" -m pytest "tests\unit\test_school_identity_compat.py::TestLegacyCompat::test_pyproject_console_scripts" -q --no-header -p no:cacheprovider
```
Result:
```
tests\unit\test_school_identity_compat.py:142: in test_pyproject_console_scripts
    assert 'school-bridge = "school.bridge:main"' in text
E   assert 'school-bridge = "school.bridge:main"' in '[build-system]\n...[project]\nname = "school"\n...'
FAILED tests/unit/test_school_identity_compat.py::TestLegacyCompat::test_pyproject_console_scripts
============================== 1 failed in 0.08s ==============================
```
RED as specified: school-bridge missing (next in order: `lerev =` present).

## Step 2 — pyproject edit

Before:
```toml
[project.scripts]
school = "school.cli:main"
# Legacy alias (pre-rename installs used `lerev`); kept for compatibility.
lerev = "school.cli:main"
```
After (verified by reading final file, `git show d868272`):
```toml
[project.scripts]
school = "school.cli:main"
school-bridge = "school.bridge:main"
```
Legacy comment lines deleted with the `lerev` entry. No `teacher`/`lerev` keys remain.

## Step 3 — contradiction proof, then GREEN + reinstall

Verbatim test after the pyproject fix still failed (proof of brief bug):
```
tests\unit\test_school_identity_compat.py:143: in test_pyproject_console_scripts
    assert "school =" not in text
E   assert 'school =' not in '[build-syst...'
E     'school =' is contained here:
E       school = "school.cli:main"
E   ...Full output truncated (57 lines hidden), use '-vv' to show
============================== 1 failed, 21 passed in 0.25s =========================
```

After correction (`teacher =`), identity file:
```
============================= 22 passed in 0.15s ==============================
```

Uninstall (controller-specified):
```
> .venv\Scripts\python.exe -m pip uninstall -y school teacher lerev ai-learning-engine
Found existing installation: school 2.6.0
Uninstalling school-2.6.0:
  Successfully uninstalled school-2.6.0
WARNING: Skipping teacher as it is not installed.
WARNING: Skipping lerev as it is not installed.
WARNING: Skipping ai-learning-engine as it is not installed.
```

Reinstall — exact pip output (hatchling fetched fine, no network failure):
```
> .venv\Scripts\python.exe -m pip install -e .
Obtaining file:///C:/Users/dex34/OneDrive/Documents/Teach
  Installing build dependencies: started
  Installing build dependencies: finished with status 'done'
  Checking if build backend supports build_editable: started
  Checking if build backend supports build_editable: finished with status 'done'
  Getting requirements to build editable: started
  Getting requirements to build editable: finished with status 'done'
  Installing backend dependencies: started
  Installing backend dependencies: finished with status 'done'
  Preparing editable metadata (pyproject.toml): started
  Preparing editable metadata (pyproject.toml): finished with status 'done'
Requirement already satisfied: pydantic<3.0,>=2.0 in .\.venv\Lib\site-packages (from school==2.6.0) (2.13.5)
Requirement already satisfied: annotated-types>=0.7.0 in ... (from pydantic->school==2.6.0) (0.8.0)
Requirement already satisfied: pydantic-core==2.46.5 in ... (from pydantic->school==2.6.0) (2.46.5)
Requirement already satisfied: typing-extensions>=4.14.1 in ... (2.13.5 / 4.16.0)
Requirement already satisfied: typing-inspection>=0.4.0 in ... (0.4.2)
Building wheels for collected packages: school
  Building editable for school (pyproject.toml): started
  Building editable for school (pyproject.toml): finished with status 'done'
  Created wheel for school: filename=school-2.6.0-py3-none-any.whl size=4164 sha256=5cb4662e2f10e04ad9a456ec55680c65b78cefd7c67dd124b8c3fbd244fc2000
  Stored in directory: C:\Users\dex34\AppData\Local\Temp\pip-ephem-wheel-cache-8puhmigj\wheels\9a\18\46\78dd19233622de3841c2e612c30aac02fd7e7918f9db3b0aba
Successfully built school
Installing collected packages: school
Successfully installed school-2.6.0
```
(Note: some "Requirement already satisfied" lines abbreviated above; full run completed with `Successfully installed school-2.6.0`, exit 0.)

## Step 4 — entry point verification

```
school.exe: True
school-bridge.exe: True
teacher.exe: False
lerev.exe: False
ai-learning-engine.exe: False
```

## Step 5 — live smoke

```
== school version ==
school 2.6.0

== school-bridge status ('{"command": "status"}' | school-bridge.exe) ==
{"ok": true, "components": {"school": "available", "v2_5": "available", "v2_6": "available", "persistence": "available", "security": "available"}, "version": "2.6.0"}

== python -m school.bridge (same JSON piped to stdin) ==
{"ok": true, "components": {"school": "available", "v2_5": "available", "v2_6": "available", "persistence": "available", "security": "available"}, "version": "2.6.0"}

== school doctor ==
SCHOOL DOCTOR
========================================

  [PASS] Python runtime: 3.14.7
  [PASS] SCHOOL package: v2.6.0
  [PASS] V2.6 memory system: available
  [PASS] V2.5 routing: available
  [PASS] Bridge: tier=installed_module
  [PASS] OpenCode config: C:\Users\dex34\.config\opencode\opencode.jsonc
  [PASS] Plugin file: C:\Users\dex34\.config\opencode\plugins\school.ts
  [PASS] Project memory: exists

RESULT: SCHOOL IS READY

doctor exit: 0
```
Bridge tier = `installed_module` (spec's accepted tiers: PATH / installed_module / dev_fallback).

## Step 6 — full suite + ruff + commit

Full suite:
```
> .venv\Scripts\python.exe -m pytest -q --no-header -p no:cacheprovider
collected 2506 items
...
====================== 2506 passed in 188.37s (0:03:08) =======================
```

Ruff, changed files:
```
> .venv\Scripts\python.exe -m ruff check pyproject.toml tests\unit\test_school_identity_compat.py
All checks passed!
```

Ruff, baseline scope:
```
> .venv\Scripts\python.exe -m ruff check school tests scripts lerev --statistics
75 E501, 63 F401, 39 W293, 23 I001, 18 F841, 2 E731, 2 B007, 1 F541, 1 E401
Found 224 errors.
```
224 = exact Task 1 baseline → 0 new ruff errors.

Commit:
```
[main d868272] feat(cli): add school and school-bridge console scripts; drop teacher/lerev aliases
 2 files changed, 6 insertions(+), 5 deletions(-)
```
Staged files: `pyproject.toml`, `tests/unit/test_school_identity_compat.py` only.
`.opencode/**` not staged. `progress.md` modification and `.superpowers` untracked files left
untouched. `failed to delete .git/worktrees/...` warnings on commit = known harmless noise.

## Expected-final-state checklist

- `[project.scripts]` = exactly `school = "school.cli:main"` + `school-bridge = "school.bridge:main"` ✅
- `.venv\Scripts\school.exe` + `school-bridge.exe` present ✅
- `teacher.exe` / `lerev.exe` / `ai-learning-engine.exe` absent ✅
- Suite green: 2506 passed (= baseline) ✅
- Ruff: 0 new (224 = baseline; changed files clean) ✅
- One commit with controller-specified message ✅
- **Deviation:** test asserts `"teacher =" not in text` instead of brief's unsatisfiable `"school =" not in text` ⚠️ (see Concern #1)
