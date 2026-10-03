### Task 4: Audit, docs polish, full battery, push

**Files:**
- Modify: `.gitignore` (memory block)
- Modify: `docs/superpowers/specs/2026-10-03-school-rebrand-design.md` (status line only — file is excluded from bulk)
- Modify (as audit finds): any doc with a stale/incorrect `school` reference
- Verify-only: everything else

**Interfaces:**
- Consumes: Tasks 1–3 (renamed world, entry points, install cleanup).
- Produces: greppy-clean repo, pushed `school` remote, ledger note for Phase 1 resume.

- [ ] **Step 1: `.gitignore` memory block**

Replace the block (post-Task-1 state is unchanged because the file was excluded) so it reads:

```gitignore
# School runtime memory (legacy .teacher/ and .lerev/ kept for existing projects)
.school/
.teacher/
.lerev/
```

(This replaces the old block that had only the comment + `.teacher/` + `.lerev/`. Keep `.teacher/` and `.lerev/` — stale dirs remain on disk per spec. Note: `.gitignore` was EXCLUDED from Task 1's bulk rename, so this edit must use the literal `.teacher/` text.)

- [ ] **Step 2: Spec status line**

In `docs/superpowers/specs/2026-10-03-school-rebrand-design.md` line 4, replace:

```
**Status:** approved design (scope + data decisions answered by user; spec pending user review)
```

with:

```
**Status:** approved (spec reviewed by user; implemented by docs/superpowers/plans/2026-10-03-school-rebrand.md)
```

- [ ] **Step 3: Repo-wide `school` audit**

```powershell
git grep -in "teacher" -- ':!.gitignore' ':!docs/superpowers/specs/2026-10-03-school-rebrand-design.md'
```

Every hit must fall into one of these allowlisted classes — anything else is a bug to fix in this step:
1. `.teacher` memory-root chain literals (in `school/config.py`, `school/plugin_source.py`, the chain tests, and comments naming the legacy root).
2. Stale-artifact names: `"teacher.ts"`, `"teacher-routing"` in `school/cli.py` + `tests/unit/test_cli.py` (intentional — they name the previous brand's files).
3. Intentional legacy prose that documents the chain (e.g. docstrings saying "legacy `.teacher` roots are read in place").

Fix all other hits (this includes `tests/conftest.py`'s docstring only if it mentions teacher — it does not; and any README/docs leftovers). Also run:

```powershell
git grep -in "teacher" -- README.md docs packaging scripts school.spec school
```

twice-verified clean (or down to allowlist items only). Check the in-flight adaptive-routing docs are fully rebranded:

```powershell
git grep -c "school_" -- docs/superpowers/plans/2026-10-02-adaptive-routing-loop.md .superpowers/sdd/2026-10-02-adaptive-routing-loop/task-3-brief.md
git grep -in "teacher" -- docs/superpowers/plans/2026-10-02-adaptive-routing-loop.md .superpowers/sdd
```

(Second command: only allowlist hits 1-3 may appear.)

- [ ] **Step 4: Append ledger note** (append to `.superpowers/sdd/2026-10-02-adaptive-routing-loop/progress.md` — the Phase 1 ledger — as a new line):

```
Note (rebrand): teacher→school rebrand completed; all plan/brief paths now school/. plugin_source.py line numbers shifted (discovery/memory-chain edits) — re-locate symbols by grep when resuming Task 3. Description strings bulk-renamed identically on TS and MCP; parity tests hold.
```

- [ ] **Step 5: Full verification battery**

```powershell
$env:PYTHONIOENCODING='utf-8'
& ".venv\Scripts\python.exe" -m pytest -q --no-header -p no:cacheprovider
```

Expected: all green; record the count (baseline 2507 — Task 3 added 1 test; report the exact delta and its cause if any).

```powershell
& ".venv\Scripts\python.exe" -m ruff check school tests scripts lerev 2>&1 | Select-Object -Last 10   # 0 NEW vs baseline
$env:PYTHONIOENCODING='utf-8'; & ".venv\Scripts\python.exe" -c "from school.plugin_source import TS_PLUGIN_SOURCE; from pathlib import Path; p = Path(r'C:\Users\dex34\AppData\Local\Temp\opencode\school-check.ts'); p.write_text(TS_PLUGIN_SOURCE, encoding='utf-8'); print(p)"; if ($?) { node --check C:\Users\dex34\AppData\Local\Temp\opencode\school-check.ts }
& ".venv\Scripts\python.exe" -c "from school.plugin_source import TS_PLUGIN_SOURCE; from pathlib import Path; ip = Path.home() / '.config/opencode/plugins/school.ts'; print('MATCH' if ip.exists() and ip.read_text(encoding='utf-8') == TS_PLUGIN_SOURCE else 'MISMATCH')"
& ".venv\Scripts\school.exe" doctor
& ".venv\Scripts\python.exe" -m pytest tests\integration\test_mcp_stdio.py tests\unit\test_mcp_server.py -q --no-header -p no:cacheprovider
& ".venv\Scripts\school.exe" mcp config opencode
```

All must pass/report sane output (`MATCH`, doctor PASS, mcp config prints `python -m school.mcp`).

- [ ] **Step 6: Commit**

```powershell
git add .gitignore docs/superpowers/specs/2026-10-03-school-rebrand-design.md README.md docs .superpowers
git commit -m "docs(rebrand): school memory gitignore entry, audit fixes, spec status"
git status --porcelain   # only .opencode junk may remain untracked/unstaged
```

- [ ] **Step 7: Push to the school remote**

```powershell
git remote -v                 # school -> https://github.com/dex34132-web/A-School-For-AI.git
git push school main
```

Verify: `git log school/main --oneline -3` matches local HEAD.

- [ ] **Step 8: Handoff note (report only)**

In the task report state: (a) restart OpenCode to load `school.ts` (the running session still has the old `teacher.ts` loaded); (b) Phase 1 resumes at adaptive-routing Task 3 using the rebranded brief — re-locate `plugin_source.py` line anchors by symbol.
