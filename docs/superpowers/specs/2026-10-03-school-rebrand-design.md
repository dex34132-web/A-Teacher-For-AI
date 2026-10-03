# School Rebrand Design

**Date:** 2026-10-03
**Status:** approved (spec reviewed by user; implemented by docs/superpowers/plans/2026-10-03-school-rebrand.md)

## Goal

Rename the entire product surface from `teacher` to `school`: Python package, CLI,
bridge, all 13 plugin tool names and 11 MCP tool names, plugin file, skill, env vars, packaging
installers, docs, and tests. The GitHub repo is already `A-School-For-AI`.

## Decisions (user-answered)

1. **Full rebrand: teacher → school everywhere.** Breaking change accepted.
   All public names become `school`; legacy aliases (`teacher`, `lerev` console
   scripts) are dropped.
2. **Existing memories stay readable (no migration, no deletion).** Memory-root
   resolution becomes: first existing of `.school`, `.teacher`, `.lerev`,
   `.evo`; if none exists, create `.school`. Old worktrees keep reading and
   writing their existing root; fresh worktrees get `.school`. Memory files on
   disk are never moved, copied, or deleted by this rebrand.
3. **No compatibility fallbacks for code surface.** Bridge discovery searches
   `school-bridge` only (plus the always-working file-path fallback). Env vars
   become `SCHOOL_*` with no `TEACHER_*` fallback.

## Rename surface

- **Package/imports:** `teacher/` → `school/` (`school.cli`, `school.bridge`,
  `school.mcp`, `school.plugin_source`, …); `python -m school.mcp`.
- **Console scripts:** `school = school.cli:main`, `school-bridge =
  school.bridge:main`. Remove `teacher` and `lerev` script aliases. The legacy
  `lerev/` package is removed if no test imports it, otherwise left untouched.
- **Tools (13 in plugin TS + 11 in MCP `_TOOLS`):** `teacher_*` → `school_*`
  (school_status, school_remember, school_recall, school_learn, school_conflict,
  school_confidence, school_search, school_deduplicate, school_knowledge,
  school_lifecycle, school_diagnose, school_route, school_route_stats).
  TS↔MCP description parity tests re-pin automatically (regex-based).
- **Identifiers:** `const Teacher` → `const School`, `export default Teacher`
  → `School`, `TEACHER_VERSION` → `SCHOOL_VERSION`, skill frontmatter name
  `teacher-routing` → `school-routing`.
- **Env vars:** `TEACHER_HOOKS/ROUTE/AGENT/PROJECT/SESSION/WORKTREE` →
  `SCHOOL_*` (grep for stragglers).
- **Memory/routing data:** root chain as in Decision 2; routing files
  (`routing-stats.jsonl`, `routing.json`) live under whichever root resolved.
  `.gitignore`: add `.school/` (old entries stay — stale dirs remain on disk).
- **Installed artifacts:** `school install --force` deletes stale
  `~/.config/opencode/plugins/teacher.ts` and
  `~/.config/opencode/skills/teacher-routing/`, then writes `school.ts` and
  `skills/school-routing/SKILL.md`. Prevents duplicate tool registration.
- **Packaging:** `teacher.nuspec` → `school.nuspec` (+ chocolatey install/
  uninstall scripts), `homebrew/teacher.rb` → `school.rb`, `linux/install.sh`,
  `windows/teacher-installer.nsi` → `school-installer.nsi`, PyInstaller
  `teacher.spec` → `school.spec`, `scripts/teacher_bridge.py` →
  `school_bridge.py`, `scripts/setup_dev.*`.
- **Docs/prose:** README, `docs/mcp.md`, `docs/installation.md`, pending
  `docs/routing.md`, in-flight spec/plan docs (`…adaptive-routing-loop*`),
  "Teacher" brand strings in tool descriptions, `_INSTRUCTIONS`, skill text,
  prompts. Product version numbering (V2.6) unchanged.
- **Tests:** ~140 files, baseline **2507 passed**; ordered mechanical replace
  (`TEACHER_`→`SCHOOL_`, `teacher_`→`school_`, `teacher`→`school`,
  `Teacher`→`School`) with identity legacy-allowance chain re-scoped (the
  historical `lerev`/`evo`/`teacher` allowance tokens may remain only where
  they guard real legacy paths).

## Non-goals

- No change to GitHub repo name/URL, no memory-data migration tool, no
  read of `.teacher` by the old name from new code paths (root chain only),
  no `TEACHER_*` env fallbacks.

## Execution order

1. Spec approved → implementation plan (writing-plans skill).
2. Mechanical rename (scripted, ordered replaces) → full suite green (2507
   baseline; count shifts only where the assertion itself was the literal).
3. `pip install -e .` entry-point refresh; `school install --force` with stale
   artifact cleanup; `node --check` extracted TS; install-parity MATCH.
4. Commit + push to `school` remote.
5. Rewrite in-flight plan/spec/task-3-brief paths to `school/`; resume Phase 1
   at Task 3 under new names.

## Risks

- **Duplicate plugins** if stale `teacher.ts` not deleted (handled in install).
- **Identity/parity tests** are literal-heavy — the replace must be reviewed
  test-by-test where assertions name the brand, not just grepped.
- **Bridge binary name** change must land together with TS discovery rewrite
  and console-script refresh, or hooks silently fail (they never throw, so
  failure is invisible — verify with a live hook-path call).
- **Scope drift into Phase 1 T3–T6**: rebrand is its own milestone; routing
  tasks resume only after suite is green and pushed.
