# School Rebrand Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename the entire product surface from `school` to `school` (Python package, CLI, bridge, all 13+13 tools, plugin file, env vars, packaging, docs, tests) while every existing memory root stays readable in place.

**Architecture:** One scripted, ordered, byte-exact text replacement over all tracked files (with two deliberate exclusions), plus git-mv file/dir renames, followed by a short list of hand-written semantic edits where a blind replace would be wrong: the memory-root chain (must keep reading `.school`), bridge discovery (legacy aliases removed, not renamed), and the tests that pin those two behaviors. Then console entry points, install-time stale-artifact cleanup, and a repo-wide audit before pushing to the `school` remote.

**Tech Stack:** Python 3.14 (`C:\Users\dex34\OneDrive\Documents\Teach\.venv`), pytest (baseline **2507 passed**), ruff, hatchling editable install, TypeScript plugin source embedded as a Python string (`school/plugin_source.py` after rename), PowerShell 5.1 shell (no `&&`; chain with `; if ($?) { ... }`).

**Spec:** `docs/superpowers/specs/2026-10-03-school-rebrand-design.md` (the spec's own file is EXCLUDED from the rename — it documents the mapping and must stay readable).

## Global Constraints

- Brand: all public names become `school`. Breaking change accepted. Console aliases `school` and `lerev` are dropped. GitHub repo name/URL are NOT changed (pyproject `project.urls` keep their current pre-rename values — intentional, pre-existing comment says so).
- Memory root (spec Decision 2): first existing of `.school`, `.school`, `.lerev`, `.evo` (checked as `<root>/memory`); if none exists, create `.school/memory`. Existing roots are read **in place** — never copied, moved, or deleted. No migration code may remain.
- No code-surface compatibility (spec Decision 3): bridge discovery = `SCHOOL_HOME` env, `school-bridge` on PATH, `school.bridge` module, `scripts/school_bridge.py` dev fallback — no `SCHOOL_*`/`LEREV_HOME`/`EVO_HOME`/`lerev-bridge` aliases anywhere in discovery (TS or Python). Env vars are `SCHOOL_HOOKS`, `SCHOOL_ROUTE`, `SCHOOL_AGENT`, `SCHOOL_PROJECT`, `SCHOOL_SESSION`, `SCHOOL_WORKTREE`, `SCHOOL_HOME`.
- Tools: all 13 plugin + 13 MCP tools are `school_*` (`school_status`, `school_remember`, `school_recall`, `school_learn`, `school_conflict`, `school_confidence`, `school_search`, `school_deduplicate`, `school_knowledge`, `school_lifecycle`, `school_diagnose`, `school_route`, `school_route_stats`). `const School`, `export default School`, `SCHOOL_VERSION`, `__SCHOOL_VERSION__`. TS↔MCP description parity is asserted by existing regex tests — keep descriptions byte-identical on both surfaces (mechanical replace guarantees this; do not hand-edit one side only).
- The `lerev/` Python package stays (tests import it as a shim); its `school` references are mechanically renamed to `school`.
- Full suite green at the end of every task (baseline 2507; a count shift is acceptable only where the test itself was brand-literal). ruff: **no NEW errors** on changed files. Never stage `.opencode/**` (excluded from rename; leave untouched).
- The rebrand script is ephemeral: lives in `C:\Users\dex34\AppData\Local\Temp\opencode\`, never committed, never run twice.
- Exclusions from the text replacement (exactly these): `.gitignore`, `docs/superpowers/specs/2026-10-03-school-rebrand-design.md`, and everything under `.opencode/`.
- Scope: Phase 1 Tasks 3–6 of the adaptive-routing plan are OUT of scope (their files get mechanically renamed in this plan; execution resumes after this plan). No skill is created here (skill install belongs to Phase 1 Task 5, which will create `school-routing` directly).
- Shell: `PYTHONIOENCODING=utf-8` before python commands that print to console; PowerShell chaining via `; if ($?) { }`.
- Push to remote `school` (https://github.com/dex34132-web/A-School-For-AI) happens ONLY in Task 4, explicitly authorized by spec Execution order step 4.

---

### Task 1: Atomic rename — package, tests, packaging content, in-flight docs (suite green)

**Files:**
- Create (ephemeral, NOT committed): `C:\Users\dex34\AppData\Local\Temp\opencode\rebrand_school.py`
- Rename (git mv): `school/` → `school/`, `scripts/school_bridge.py` → `scripts/school_bridge.py`, `school.spec` → `school.spec`, `packaging/chocolatey/school.nuspec` → `school.nuspec`, `packaging/homebrew/school.rb` → `school.rb`, `packaging/windows/school-installer.nsi` → `school-installer.nsi`, 8 test files `tests/unit/test_school_*.py` → `test_school_*.py`
- Modify (semantic hand-edits): `school/config.py`, `school/plugin_source.py`, `school/discovery.py`, `school/bridge.py`, `tests/unit/test_school_identity_compat.py`, `tests/unit/test_school_discovery_comprehensive.py`, `tests/unit/test_school_plugin_bridge.py`
- Every other tracked text file: mechanical replace only

**Interfaces:**
- Produces: package `school` importable (`school.cli`, `school.bridge`, `school.mcp`, `school.plugin_source`, `school.discovery`, `school.config`); tools `school_*`; `resolve_memory_dir(worktree) -> Path` with chain semantics; `discover_bridge(worktree) -> BridgeDiscovery | None` school-only; TS `discoverBridge` school-only; `SCHOOL_*` → `SCHOOL_*` everywhere.
- Consumes: nothing (first task).

- [ ] **Step 1: Capture pre-state**

```powershell
Set-Location C:\Users\dex34\OneDrive\Documents\Teach
git rev-parse HEAD          # record as BASE for review package
git status --porcelain      # only .opencode/goals junk expected untracked
```

- [ ] **Step 2: Enumerate the file renames (authoritative check)**

```powershell
git ls-files "*school*"
```

Expected (15 paths): `school/` package (many files), `scripts/school_bridge.py`, `school.spec`, `packaging/chocolatey/school.nuspec`, `packaging/homebrew/school.rb`, `packaging/windows/school-installer.nsi`, and the 8 test files:

```
tests/unit/test_school_cli_comprehensive.py
tests/unit/test_school_discovery_comprehensive.py
tests/unit/test_school_identity_compat.py
tests/unit/test_school_learn_persistence.py
tests/unit/test_school_packaging.py
tests/unit/test_school_plugin_bridge.py
tests/unit/test_school_plugin_hooks.py
tests/unit/test_school_routing.py
```

If any additional path appears, git-mv it to the obvious `school` name as well (report it in the task report).

- [ ] **Step 3: git mv everything**

```powershell
git mv school school
git mv scripts/school_bridge.py scripts/school_bridge.py
git mv school.spec school.spec
git mv packaging/chocolatey/school.nuspec packaging/chocolatey/school.nuspec
git mv packaging/homebrew/school.rb packaging/homebrew/school.rb
git mv packaging/windows/school-installer.nsi packaging/windows/school-installer.nsi
git mv tests/unit/test_school_cli_comprehensive.py tests/unit/test_school_cli_comprehensive.py
git mv tests/unit/test_school_discovery_comprehensive.py tests/unit/test_school_discovery_comprehensive.py
git mv tests/unit/test_school_identity_compat.py tests/unit/test_school_identity_compat.py
git mv tests/unit/test_school_learn_persistence.py tests/unit/test_school_learn_persistence.py
git mv tests/unit/test_school_packaging.py tests/unit/test_school_packaging.py
git mv tests/unit/test_school_plugin_bridge.py tests/unit/test_school_plugin_bridge.py
git mv tests/unit/test_school_plugin_hooks.py tests/unit/test_school_plugin_hooks.py
git mv tests/unit/test_school_routing.py tests/unit/test_school_routing.py
```

- [ ] **Step 4: Write the ephemeral rebrand script** (byte-exact, ordered, excludes; save to `C:\Users\dex34\AppData\Local\Temp\opencode\rebrand_school.py`):

```python
import pathlib
import subprocess
import sys

EXCLUDE = {
    ".gitignore",
    "docs/superpowers/specs/2026-10-03-school-rebrand-design.md",
}
# Order matters: uppercase first, then capitalized, then lowercase.
REPLACEMENTS = [("SCHOOL", "SCHOOL"), ("School", "School"), ("school", "school")]

out = subprocess.run(["git", "ls-files", "-z"], capture_output=True, check=True)
changed = excluded = skipped_non_utf8 = 0
for rel in out.stdout.decode().split("\0"):
    if not rel or rel.startswith(".opencode/"):
        continue
    if rel in EXCLUDE:
        excluded += 1
        continue
    path = pathlib.Path(rel)
    try:
        data = path.read_bytes()
        text = data.decode("utf-8")
    except (FileNotFoundError, UnicodeDecodeError):
        skipped_non_utf8 += 1
        continue
    for old, new in REPLACEMENTS:
        text = text.replace(old, new)
    new_data = text.encode("utf-8")
    if new_data != data:
        path.write_bytes(new_data)  # byte-exact: preserves every line ending
        changed += 1
print(f"changed={changed} excluded={excluded} skipped={skipped_non_utf8}")
```

- [ ] **Step 5: Run it once**

```powershell
$env:PYTHONIOENCODING='utf-8'; & ".venv\Scripts\python.exe" C:\Users\dex34\AppData\Local\Temp\opencode\rebrand_school.py
```

Expected: `changed=<~130> excluded=2 skipped=0`. Verify exclusions survived:

```powershell
git diff -- .gitignore   # must be EMPTY (excluded)
git grep -c "school" -- docs/superpowers/specs/2026-10-03-school-rebrand-design.md   # still > 0 (excluded)
git grep -l "school_" -- tests | Select-Object -First 5   # expect empty
```

- [ ] **Step 6: Semantic fallout A — memory-root chain (TDD, RED first)**

The bulk replace turned `.school` into `.school` everywhere, which silently DELETED the legacy `.school` read. Restore it as a chain.

6a. In `tests/unit/test_school_identity_compat.py` replace the whole `class TestMemoryMigration:` block (docstring says "``.lerev`` / ``.evo`` memories migrate into ``.school`` safely.") with:

```python
class TestMemoryRootChain:
    """Existing memory roots are read in place; fresh worktrees use ``.school``."""

    def test_school_root_created_when_nothing_exists(self, tmp_path: Path) -> None:
        out = resolve_memory_dir(tmp_path)
        assert out == tmp_path / ".school" / "memory"
        assert out.is_dir()

    def test_existing_school_root_read_in_place(self, tmp_path: Path) -> None:
        legacy = tmp_path / ".school" / "memory"
        legacy.mkdir(parents=True)
        (legacy / "m.json").write_text('{"id": "x"}', encoding="utf-8")

        out = resolve_memory_dir(tmp_path)

        assert out == legacy
        assert (out / "m.json").read_text(encoding="utf-8") == '{"id": "x"}'
        assert not (tmp_path / ".school").exists(), "no migration: .school must not be created"

    def test_existing_lerev_root_read_in_place(self, tmp_path: Path) -> None:
        legacy = tmp_path / ".lerev" / "memory"
        legacy.mkdir(parents=True)

        out = resolve_memory_dir(tmp_path)

        assert out == legacy
        assert not (tmp_path / ".school").exists()

    def test_school_wins_over_legacy_when_both_exist(self, tmp_path: Path) -> None:
        school = tmp_path / ".school" / "memory"
        school.mkdir(parents=True)
        (school / "new.json").write_text("{}", encoding="utf-8")
        old = tmp_path / ".school" / "memory"
        old.mkdir(parents=True)
        (old / "old.json").write_text("{}", encoding="utf-8")

        out = resolve_memory_dir(tmp_path)

        assert out == school
        assert (old / "old.json").exists(), "legacy root untouched"
```

6b. Run — expect RED (current code copies `.lerev` into `.school` and has no `.school` check):

```powershell
& ".venv\Scripts\python.exe" -m pytest tests\unit\test_school_identity_compat.py -q --no-header -p no:cacheprovider
```

6c. In `school/config.py` replace the entire `resolve_memory_dir` function (current post-bulk state copies legacy dirs — delete that whole body) with:

```python
def resolve_memory_dir(worktree: str | Path) -> Path:
    """Return the memory directory for a worktree.

    Resolution takes the first existing of ``.school``, ``.school``,
    ``.lerev``, ``.evo`` (checked as ``<root>/memory``); if none exists,
    ``.school/memory`` is created. Existing roots are used in place —
    memory is never copied, moved, or deleted.
    """
    root = Path(worktree)
    for name in (".school", ".school", ".lerev", ".evo"):
        candidate = root / name / "memory"
        if candidate.exists():
            return candidate
    canonical = root / ".school" / "memory"
    canonical.mkdir(parents=True, exist_ok=True)
    return canonical
```

Then remove `import shutil` from `school/config.py` if ruff reports it unused (it was only used by the old `copytree`).

6d. In `school/bridge.py` (~line 58) replace the stale comment:

```python
        # Memory root: first existing of .school/.school/.lerev/.evo,
        # else .school — read in place, never migrated (see resolve_memory_dir).
        storage_dir = resolve_memory_dir(worktree)
```

6e. In `school/plugin_source.py` the two chain literals were bulk-renamed to `[".school", ".lerev", ".evo"]` — reinsert the legacy entry so both read exactly:

```ts
  for (const dir of [".school", ".school", ".lerev", ".evo"]) {
```

(There is one at the old line 283 inside `memoryRoot` — whose fallback line `return resolve(worktree, ".school")` is already correct post-bulk — and one at the old line 342 inside `hasMemoryRoot`. Change ONLY the two array literals; verify the fallback returns `.school`.)

6f. GREEN check: run `tests\unit\test_school_identity_compat.py` again → all pass.

- [ ] **Step 7: Semantic fallout B — bridge discovery school-only (TDD, RED first)**

7a. Rewrite the legacy-env tests. In `tests/unit/test_school_discovery_comprehensive.py`: DELETE `test_tier1_evo_home_fallback` and `test_tier1_school_home_takes_precedence` (they pin removed behavior), and ADD:

```python
    def test_tier1_legacy_home_envs_not_honoured(self, tmp_path: Path) -> None:
        """LEREV_HOME / EVO_HOME are no longer honoured (no compat fallbacks)."""
        home = tmp_path / "legacy_home"
        (home / "school").mkdir(parents=True)
        (home / "school" / "bridge.py").write_text("", encoding="utf-8")

        with patch.dict(os.environ, {"LEREV_HOME": str(home), "EVO_HOME": str(home)}, clear=True):
            result = discover_bridge(str(tmp_path))

        assert result is None or not result.bridge_path.startswith(str(home))
```

(The remaining `test_tier1_school_home` and its `home/"school"` fixture are already correct after the bulk replace.)

In `tests/unit/test_school_identity_compat.py`: DELETE `test_lerev_home_env_honoured` and `test_evo_home_env_honoured`, and ADD (inside the same class):

```python
    def test_legacy_home_envs_not_honoured(self, tmp_path: Path) -> None:
        home = tmp_path / "legacy_root"
        (home / "school").mkdir(parents=True)
        (home / "school" / "bridge.py").write_text("", encoding="utf-8")

        import os

        with patch.dict(os.environ, {"LEREV_HOME": str(home), "EVO_HOME": str(home)}, clear=True):
            discovery = discover_bridge(str(REPO_ROOT))

        assert discovery is None or not discovery.bridge_path.startswith(str(home))
```

7b. Run both test files → RED (discovery still honours the legacy envs).

7c. In `school/discovery.py` replace legacy alias handling — the post-state of the whole file is:

```python
"""School bridge discovery — 4-tier cascade."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BridgeDiscovery:
    """Result of bridge discovery."""

    python: str
    bridge_path: str
    tier: str


def _find_python() -> str | None:
    """Find a usable Python interpreter."""
    for cmd in ("python3", "python"):
        if shutil.which(cmd):
            return cmd
    return None


def _file_exists(path: str) -> bool:
    """Check if a file exists."""
    return Path(path).is_file()


def discover_bridge(worktree: str) -> BridgeDiscovery | None:
    """Discover the School bridge using a 4-tier cascade.

    Tier 1: SCHOOL_HOME env var
    Tier 2: school-bridge on PATH
    Tier 3: python -m school.bridge
    Tier 4: Dev fallback ({worktree}/scripts/school_bridge.py)
    """
    python = _find_python()

    # Tier 1: env-configured install root
    home = os.environ.get("SCHOOL_HOME")
    if home:
        bridge_path = str(Path(home) / "school" / "bridge.py")
        if _file_exists(bridge_path):
            return BridgeDiscovery(
                python=python or "python3",
                bridge_path=bridge_path,
                tier="SCHOOL_HOME",
            )

    # Tier 2: bridge launcher on PATH
    bridge_cmd = shutil.which("school-bridge")
    if bridge_cmd:
        return BridgeDiscovery(python="", bridge_path=bridge_cmd, tier="PATH")

    # Tier 3: installed module (only if python is available). The actual
    # module invocation happens in the plugin; we probe importability here.
    if python:
        try:
            import importlib.util

            spec = importlib.util.find_spec("school.bridge")
            if spec is not None and spec.origin is not None:
                return BridgeDiscovery(
                    python=python,
                    bridge_path="-m school.bridge",
                    tier="installed_module",
                )
        except (ImportError, ValueError):
            pass

    # Tier 4: Dev fallback
    dev_bridge = str(Path(worktree) / "scripts" / "school_bridge.py")
    if _file_exists(dev_bridge):
        return BridgeDiscovery(
            python=python or "python3",
            bridge_path=dev_bridge,
            tier="dev_fallback",
        )

    return None
```

7d. In `school/plugin_source.py`, the bulk replace already renamed `SCHOOL_HOME`→`SCHOOL_HOME`, `schoolHome`→`schoolHome`, `school-bridge`→`school-bridge`, `school.bridge`→`school.bridge`, `school_bridge.py`→`school_bridge.py`. What remains is stripping the legacy aliases. Post-state of `discoverBridge` and its doc comment (keep the surrounding helpers and the single-element `for` loops — tests pin the `where ${command}` / `which ${command}` strings):

```ts
/**
 * Discover the School bridge using a 4-tier cascade.
 */
async function discoverBridge(worktree: string): Promise<BridgeInfo | null> {
  const python = await findPython()

  // Tier 1: SCHOOL_HOME env var
  const schoolHome = process.env.SCHOOL_HOME
  if (schoolHome) {
    const bridgePath = resolve(schoolHome, "school", "bridge.py")
    if (fileExists(bridgePath)) {
      return { python: python ?? "python3", bridgePath, tier: "SCHOOL_HOME" }
    }
  }

  // Tier 2: bridge launcher on PATH
  for (const command of ["school-bridge"]) {
    try {
      const isWin = process.platform === "win32"
      const whereCmd = isWin ? `where ${command}` : `which ${command}`
      const bridgeCmd = execSync(whereCmd, { windowsHide: true, timeout: 3000 })
        .toString().trim()
      if (bridgeCmd) {
        return { python: "", bridgePath: bridgeCmd, tier: "PATH" }
      }
    } catch {
      // Not on PATH — next tier
    }
  }

  // Tier 3: installed module
  if (python) {
    for (const module of ["school.bridge"]) {
      const available = await testModule(python, module)
      if (available) {
        return { python, bridgePath: `-m ${module}`, tier: "installed_module" }
      }
    }
  }

  // Tier 4: Dev fallback
  for (const script of ["school_bridge.py"]) {
    const devBridge = resolve(worktree, "scripts", script)
    if (fileExists(devBridge)) {
      return { python: python ?? "python3", bridgePath: devBridge, tier: "dev_fallback" }
    }
  }

  return null
}
```

Delete the old doc-comment lines mentioning `LEREV_HOME / EVO_HOME / lerev-bridge / lerev.bridge / lerev_bridge.py` and the `// Legacy aliases ...` comments.

7e. In `tests/unit/test_school_plugin_bridge.py` (`test_cross_platform_bridge_discovery`, ~line 67-73):
- docstring → `"""Plugin uses cross-platform PATH detection."""`
- change `assert "lerev-bridge" in TS_PLUGIN_SOURCE` → `assert "lerev-bridge" not in TS_PLUGIN_SOURCE`
- keep `assert "school-bridge" in TS_PLUGIN_SOURCE` (bulk already renamed it).

7f. Leave `test_plugin_has_legacy_fallbacks_only`'s allowlist in `test_school_identity_compat.py` untouched — it is a whitelist of tolerable tokens (`.lerev` is still a real legacy path); entries that no longer occur are harmless.

7g. GREEN: run both test files + `tests\unit\test_school_plugin_bridge.py`.

- [ ] **Step 8: Refresh the editable install (required for import resolution)**

The venv currently carries a stale editable dist `ai-learning-engine` (old brand) whose finder predates the rename.

```powershell
& ".venv\Scripts\python.exe" -m pip uninstall -y ai-learning-engine school lerev school
```

Ignore "not installed" warnings. Then:

```powershell
& ".venv\Scripts\python.exe" -m pip install -e .
```

If hatchling is missing and the build-isolation download fails, retry:

```powershell
& ".venv\Scripts\python.exe" -m pip install hatchling; if ($?) { & ".venv\Scripts\python.exe" -m pip install -e . --no-build-isolation }
```

Verify: `& ".venv\Scripts\python.exe" -c "import school; print(school.__version__)"` → `2.6.0`.

- [ ] **Step 9: TS syntax check**

```powershell
$env:PYTHONIOENCODING='utf-8'; & ".venv\Scripts\python.exe" -c "from school.plugin_source import TS_PLUGIN_SOURCE; from pathlib import Path; p = Path(r'C:\Users\dex34\AppData\Local\Temp\opencode\school-check.ts'); p.write_text(TS_PLUGIN_SOURCE, encoding='utf-8'); print(p)"; if ($?) { node --check C:\Users\dex34\AppData\Local\Temp\opencode\school-check.ts }
```

Expected: exit 0.

- [ ] **Step 10: Full suite → fix fallout until green**

```powershell
& ".venv\Scripts\python.exe" -m pytest -q --no-header -p no:cacheprovider
```

Expected failure classes if anything remains (fix in place, do not weaken assertions):
- `ModuleNotFoundError: school` in subprocess/integration tests → Step 8 was skipped or failed; rerun it.
- Tests asserting copy/migration semantics elsewhere (search `copytree`/`copied` under `tests/`) → rewrite to chain semantics (same rules as Step 6).
- `lerev-bridge` / `LEREV_HOME` / `EVO_HOME` pins outside Step 7's files → grep: `git grep -ln "lerev-bridge\|LEREV_HOME\|EVO_HOME" -- tests` and apply the same not-honoured treatment.
- Literal-brand pins (`"school ..."` assertions) that bulk-rename should have caught but did not (odd casing/split strings) → fix the literal on both sides of the assertion.

Ruff gate (no NEW errors):

```powershell
& ".venv\Scripts\python.exe" -m ruff check school tests scripts lerev 2>&1 | Select-Object -Last 10
```

Compare against pre-task baseline (16 pre-existing E501 in `plugin_source` were the known set; any other pre-existing counts: run the same command at BASE if in doubt). New errors must be zero.

- [ ] **Step 11: Commit**

```powershell
git add -A -- ':!.opencode'
git commit -m "refactor(rebrand): rename school to school across package, tests, packaging, and docs"
git rev-parse --short HEAD
```

Do not stage `.opencode/**` (must show no changes anyway).

---

### Task 2: Console entry points + CLI/bridge smoke

**Files:**
- Modify: `pyproject.toml` (`[project.scripts]`)
- Modify: `tests/unit/test_school_identity_compat.py` (`test_pyproject_keeps_legacy_console_script` → rewritten)

**Interfaces:**
- Consumes: Task 1's `school` package (`school.cli:main`, `school.bridge:main` both exist — `main` in `school/bridge.py` is imported by the identity shim test already).
- Produces: console scripts `school` and `school-bridge` in `.venv\Scripts`; no `school`/`lerev`/`ai-learning-engine` scripts. Later tasks smoke-test `school doctor` and `school install --force`.

- [ ] **Step 1: Rewrite the pyproject test (RED first)**

In `tests/unit/test_school_identity_compat.py`, replace `test_pyproject_keeps_legacy_console_script` with:

```python
    def test_pyproject_console_scripts(self) -> None:
        text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        assert 'name = "school"' in text
        assert 'school = "school.cli:main"' in text
        assert 'school-bridge = "school.bridge:main"' in text
        assert "school =" not in text
        assert "lerev =" not in text
```

Run:

```powershell
& ".venv\Scripts\python.exe" -m pytest tests\unit\test_school_identity_compat.py::TestLegacyCompat::test_pyproject_console_scripts -q --no-header -p no:cacheprovider
```

Expected: FAIL (lerev alias present, school-bridge missing).

- [ ] **Step 2: Edit `pyproject.toml`**

Replace the whole scripts block (post-bulk state contains `school = ...` plus the surviving `lerev = ...` alias and its comment) with exactly:

```toml
[project.scripts]
school = "school.cli:main"
school-bridge = "school.bridge:main"
```

(Delete the `# Legacy alias ...` comment lines along with the `lerev` entry.)

- [ ] **Step 3: GREEN + refresh install**

```powershell
& ".venv\Scripts\python.exe" -m pytest tests\unit\test_school_identity_compat.py -q --no-header -p no:cacheprovider
& ".venv\Scripts\python.exe" -m pip install -e .
```

- [ ] **Step 4: Verify entry points**

```powershell
Test-Path .venv\Scripts\school.exe            # True
Test-Path .venv\Scripts\school-bridge.exe     # True
Test-Path .venv\Scripts\school.exe           # False
Test-Path .venv\Scripts\lerev.exe             # False
```

- [ ] **Step 5: Live smoke (bridge path — the silent-failure risk from the spec)**

```powershell
$env:PYTHONIOENCODING='utf-8'
& ".venv\Scripts\school.exe" version
'{\"command\": \"status\"}' | & ".venv\Scripts\school-bridge.exe"
& ".venv\Scripts\python.exe" -m school.bridge
```

(The first two must print `school 2.6.0` and a JSON `ok` payload; the module call reads its payload from stdin — pipe the same JSON if it waits.) Then:

```powershell
& ".venv\Scripts\school.exe" doctor
```

Expected: doctor checks PASS (bridge tier found — `PATH` or `installed_module` or `dev_fallback`).

- [ ] **Step 6: Full suite + ruff on changed files (expect 0 new) + commit**

```powershell
& ".venv\Scripts\python.exe" -m pytest -q --no-header -p no:cacheprovider
& ".venv\Scripts\python.exe" -m ruff check pyproject.toml tests\unit\test_school_identity_compat.py
git add pyproject.toml tests/unit/test_school_identity_compat.py
git commit -m "feat(cli): add school and school-bridge console scripts; drop school/lerev aliases"
```

---

### Task 3: `school install --force` removes stale previous-brand artifacts

**Files:**
- Modify: `school/cli.py` (`_cmd_install`, ~line 117)
- Modify: `tests/unit/test_cli.py` (new test)

**Interfaces:**
- Consumes: Task 1's `school.ts` plugin file name (`config.school_plugin_file()`), `config.opencode_plugins_dir()` (returns `~/.config/opencode/plugins`).
- Produces: `_clean_stale_brand(config, verbose=True) -> bool` called from `_cmd_install` before the write; guarantees `plugins/school.ts` and `skills/school-routing/` are deleted on every install (with or without `--force`) so OpenCode never registers duplicate `school_*` + `school_*` tools.

- [ ] **Step 1: Failing test** (add to `tests/unit/test_cli.py`, class `TestCLI`):

```python
    def test_install_removes_stale_school_artifacts(self, tmp_path: Path) -> None:
        """school install deletes the previous brand's plugin and skill."""
        config_dir = tmp_path / ".config" / "opencode"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "opencode.jsonc"
        config_file.write_text('{"plugin": []}', encoding="utf-8")
        plugins_dir = config_dir / "plugins"
        plugins_dir.mkdir(parents=True)
        stale_plugin = plugins_dir / "school.ts"
        stale_plugin.write_text("// stale previous brand", encoding="utf-8")
        stale_skill = config_dir / "skills" / "school-routing"
        stale_skill.mkdir(parents=True)
        (stale_skill / "SKILL.md").write_text("name: school-routing", encoding="utf-8")

        with (
            patch("sys.argv", ["school", "install", "--force"]),
            patch("school.cli.SchoolConfig") as MockConfig,
        ):
            config = MockConfig.return_value
            config.is_school_installed.return_value = False
            config.opencode_plugins_dir.return_value = plugins_dir
            config.school_plugin_file.return_value = plugins_dir / "school.ts"
            config.opencode_config_file.return_value = config_file
            main()

        assert not stale_plugin.exists(), "stale school.ts must be deleted"
        assert not stale_skill.exists(), "stale school-routing skill must be deleted"
        assert (plugins_dir / "school.ts").exists()
```

- [ ] **Step 2: Run to verify it fails**

```powershell
& ".venv\Scripts\python.exe" -m pytest tests\unit\test_cli.py::TestCLI::test_install_removes_stale_school_artifacts -q --no-header -p no:cacheprovider
```

Expected: FAIL — `stale school.ts must be deleted`.

- [ ] **Step 3: Implement** — in `school/cli.py`, add after the `_clean_legacy_plugin` function definition (make sure `shutil` is already imported — it is):

```python
def _clean_stale_brand(config: SchoolConfig, verbose: bool = True) -> bool:
    """Remove previous-brand artefacts so OpenCode never loads duplicates.

    Deletes ``plugins/school.ts`` and ``skills/school-routing/`` written
    by pre-rebrand installs of this product.
    """
    removed = False

    stale_plugin = config.opencode_plugins_dir() / "school.ts"
    if stale_plugin.is_file():
        try:
            stale_plugin.unlink()
            removed = True
            if verbose:
                print(f"Removed stale previous-brand plugin: {stale_plugin}")
        except OSError:
            pass

    stale_skill = config.opencode_plugins_dir().parent / "skills" / "school-routing"
    if stale_skill.is_dir():
        try:
            shutil.rmtree(stale_skill)
            removed = True
            if verbose:
                print(f"Removed stale previous-brand skill: {stale_skill}")
        except OSError:
            pass

    return removed
```

(Annotation is `SchoolConfig` — the class name after Task 1's bulk rename.) Then in `_cmd_install`, immediately after `_clean_legacy_plugin(config)`:

```python
    # Remove stale previous-brand artefacts (rebrand cleanup)
    _clean_stale_brand(config)
```

The literal `"school.ts"` and `"school-routing"` strings are INTENTIONAL — they name the stale artifacts; never re-rename them.

- [ ] **Step 4: GREEN**

```powershell
& ".venv\Scripts\python.exe" -m pytest tests\unit\test_cli.py -q --no-header -p no:cacheprovider
```

- [ ] **Step 5: Live reinstall + artifact verification**

```powershell
$env:PYTHONIOENCODING='utf-8'
& ".venv\Scripts\school.exe" install --force
Test-Path $env:USERPROFILE\.config\opencode\plugins\school.ts    # must be False
Test-Path $env:USERPROFILE\.config\opencode\plugins\school.ts     # must be True
& ".venv\Scripts\python.exe" -c "from school.plugin_source import TS_PLUGIN_SOURCE; from pathlib import Path; ip = Path.home() / '.config/opencode/plugins/school.ts'; print('MATCH' if ip.exists() and ip.read_text(encoding='utf-8') == TS_PLUGIN_SOURCE else 'MISMATCH')"
```

Expected: install output shows the stale removal (if the file existed) and `MATCH`.

- [ ] **Step 6: TS syntax check on the installed file**

```powershell
node --check $env:USERPROFILE\.config\opencode\plugins\school.ts
```

Expected: exit 0.

- [ ] **Step 7: Full suite + commit**

```powershell
& ".venv\Scripts\python.exe" -m pytest -q --no-header -p no:cacheprovider
& ".venv\Scripts\python.exe" -m ruff check school\cli.py tests\unit\test_cli.py
git add school/cli.py tests/unit/test_cli.py
git commit -m "feat(cli): school install removes stale previous-brand plugin and skill artifacts"
```

---

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
