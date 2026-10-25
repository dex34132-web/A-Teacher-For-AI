# Toolio Rebrand Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename the entire product surface from `toolio` to `toolio` (Python package, CLI, bridge, all 13+13 tools, plugin file, env vars, packaging, docs, tests) while every existing memory root stays readable in place.

**Architecture:** One scripted, ordered, byte-exact text replacement over all tracked files (with two deliberate exclusions), plus git-mv file/dir renames, followed by a short list of hand-written semantic edits where a blind replace would be wrong: the memory-root chain (must keep reading `.toolio`), bridge discovery (legacy aliases removed, not renamed), and the tests that pin those two behaviors. Then console entry points, install-time stale-artifact cleanup, and a repo-wide audit before pushing to the `toolio` remote.

**Tech Stack:** Python 3.14 (`C:\Users\dex34\OneDrive\Documents\Teach\.venv`), pytest (baseline **2507 passed**), ruff, hatchling editable install, TypeScript plugin source embedded as a Python string (`toolio/plugin_source.py` after rename), PowerShell 5.1 shell (no `&&`; chain with `; if ($?) { ... }`).

**Spec:** `docs/superpowers/specs/2026-10-03-toolio-rebrand-design.md` (the spec's own file is EXCLUDED from the rename — it documents the mapping and must stay readable).

## Global Constraints

- Brand: all public names become `toolio`. Breaking change accepted. Console aliases `toolio` and `toolio` are dropped. GitHub repo name/URL are NOT changed (pyproject `project.urls` keep their current pre-rename values — intentional, pre-existing comment says so).
- Memory root (spec Decision 2): first existing of `.toolio`, `.toolio`, `.toolio`, `.evo` (checked as `<root>/memory`); if none exists, create `.toolio/memory`. Existing roots are read **in place** — never copied, moved, or deleted. No migration code may remain.
- No code-surface compatibility (spec Decision 3): bridge discovery = `SCHOOL_HOME` env, `toolio-bridge` on PATH, `toolio.bridge` module, `scripts/toolio_bridge.py` dev fallback — no `SCHOOL_*`/`LEREV_HOME`/`EVO_HOME`/`toolio-bridge` aliases anywhere in discovery (TS or Python). Env vars are `SCHOOL_HOOKS`, `SCHOOL_ROUTE`, `SCHOOL_AGENT`, `SCHOOL_PROJECT`, `SCHOOL_SESSION`, `SCHOOL_WORKTREE`, `SCHOOL_HOME`.
- Tools: all 13 plugin + 13 MCP tools are `toolio_*` (`toolio_status`, `toolio_remember`, `toolio_recall`, `toolio_learn`, `toolio_conflict`, `toolio_confidence`, `toolio_search`, `toolio_deduplicate`, `toolio_knowledge`, `toolio_lifecycle`, `toolio_diagnose`, `toolio_route`, `toolio_route_stats`). `const Toolio`, `export default Toolio`, `SCHOOL_VERSION`, `__SCHOOL_VERSION__`. TS↔MCP description parity is asserted by existing regex tests — keep descriptions byte-identical on both surfaces (mechanical replace guarantees this; do not hand-edit one side only).
- The `toolio/` Python package stays (tests import it as a shim); its `toolio` references are mechanically renamed to `toolio`.
- Full suite green at the end of every task (baseline 2507; a count shift is acceptable only where the test itself was brand-literal). ruff: **no NEW errors** on changed files. Never stage `.opencode/**` (excluded from rename; leave untouched).
- The rebrand script is ephemeral: lives in `C:\Users\dex34\AppData\Local\Temp\opencode\`, never committed, never run twice.
- Exclusions from the text replacement (exactly these): `.gitignore`, `docs/superpowers/specs/2026-10-03-toolio-rebrand-design.md`, and everything under `.opencode/`.
- Scope: Phase 1 Tasks 3–6 of the adaptive-routing plan are OUT of scope (their files get mechanically renamed in this plan; execution resumes after this plan). No skill is created here (skill install belongs to Phase 1 Task 5, which will create `toolio-routing` directly).
- Shell: `PYTHONIOENCODING=utf-8` before python commands that print to console; PowerShell chaining via `; if ($?) { }`.
- Push to remote `toolio` (https://github.com/dex34132-web/A-Toolio-For-AI) happens ONLY in Task 4, explicitly authorized by spec Execution order step 4.

---

### Task 1: Atomic rename — package, tests, packaging content, in-flight docs (suite green)

**Files:**
- Create (ephemeral, NOT committed): `C:\Users\dex34\AppData\Local\Temp\opencode\rebrand_toolio.py`
- Rename (git mv): `toolio/` → `toolio/`, `scripts/toolio_bridge.py` → `scripts/toolio_bridge.py`, `toolio.spec` → `toolio.spec`, `packaging/chocolatey/toolio.nuspec` → `toolio.nuspec`, `packaging/homebrew/toolio.rb` → `toolio.rb`, `packaging/windows/toolio-installer.nsi` → `toolio-installer.nsi`, 8 test files `tests/unit/test_toolio_*.py` → `test_toolio_*.py`
- Modify (semantic hand-edits): `toolio/config.py`, `toolio/plugin_source.py`, `toolio/discovery.py`, `toolio/bridge.py`, `tests/unit/test_toolio_identity_compat.py`, `tests/unit/test_toolio_discovery_comprehensive.py`, `tests/unit/test_toolio_plugin_bridge.py`
- Every other tracked text file: mechanical replace only

**Interfaces:**
- Produces: package `toolio` importable (`toolio.cli`, `toolio.bridge`, `toolio.mcp`, `toolio.plugin_source`, `toolio.discovery`, `toolio.config`); tools `toolio_*`; `resolve_memory_dir(worktree) -> Path` with chain semantics; `discover_bridge(worktree) -> BridgeDiscovery | None` toolio-only; TS `discoverBridge` toolio-only; `SCHOOL_*` → `SCHOOL_*` everywhere.
- Consumes: nothing (first task).

- [ ] **Step 1: Capture pre-state**

```powershell
Set-Location C:\Users\dex34\OneDrive\Documents\Teach
git rev-parse HEAD          # record as BASE for review package
git status --porcelain      # only .opencode/goals junk expected untracked
```

- [ ] **Step 2: Enumerate the file renames (authoritative check)**

```powershell
git ls-files "*toolio*"
```

Expected (15 paths): `toolio/` package (many files), `scripts/toolio_bridge.py`, `toolio.spec`, `packaging/chocolatey/toolio.nuspec`, `packaging/homebrew/toolio.rb`, `packaging/windows/toolio-installer.nsi`, and the 8 test files:

```
tests/unit/test_toolio_cli_comprehensive.py
tests/unit/test_toolio_discovery_comprehensive.py
tests/unit/test_toolio_identity_compat.py
tests/unit/test_toolio_learn_persistence.py
tests/unit/test_toolio_packaging.py
tests/unit/test_toolio_plugin_bridge.py
tests/unit/test_toolio_plugin_hooks.py
tests/unit/test_toolio_routing.py
```

If any additional path appears, git-mv it to the obvious `toolio` name as well (report it in the task report).

- [ ] **Step 3: git mv everything**

```powershell
git mv toolio toolio
git mv scripts/toolio_bridge.py scripts/toolio_bridge.py
git mv toolio.spec toolio.spec
git mv packaging/chocolatey/toolio.nuspec packaging/chocolatey/toolio.nuspec
git mv packaging/homebrew/toolio.rb packaging/homebrew/toolio.rb
git mv packaging/windows/toolio-installer.nsi packaging/windows/toolio-installer.nsi
git mv tests/unit/test_toolio_cli_comprehensive.py tests/unit/test_toolio_cli_comprehensive.py
git mv tests/unit/test_toolio_discovery_comprehensive.py tests/unit/test_toolio_discovery_comprehensive.py
git mv tests/unit/test_toolio_identity_compat.py tests/unit/test_toolio_identity_compat.py
git mv tests/unit/test_toolio_learn_persistence.py tests/unit/test_toolio_learn_persistence.py
git mv tests/unit/test_toolio_packaging.py tests/unit/test_toolio_packaging.py
git mv tests/unit/test_toolio_plugin_bridge.py tests/unit/test_toolio_plugin_bridge.py
git mv tests/unit/test_toolio_plugin_hooks.py tests/unit/test_toolio_plugin_hooks.py
git mv tests/unit/test_toolio_routing.py tests/unit/test_toolio_routing.py
```

- [ ] **Step 4: Write the ephemeral rebrand script** (byte-exact, ordered, excludes; save to `C:\Users\dex34\AppData\Local\Temp\opencode\rebrand_toolio.py`):

```python
import pathlib
import subprocess
import sys

EXCLUDE = {
    ".gitignore",
    "docs/superpowers/specs/2026-10-03-toolio-rebrand-design.md",
}
# Order matters: uppercase first, then capitalized, then lowercase.
REPLACEMENTS = [("SCHOOL", "SCHOOL"), ("Toolio", "Toolio"), ("toolio", "toolio")]

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
$env:PYTHONIOENCODING='utf-8'; & ".venv\Scripts\python.exe" C:\Users\dex34\AppData\Local\Temp\opencode\rebrand_toolio.py
```

Expected: `changed=<~130> excluded=2 skipped=0`. Verify exclusions survived:

```powershell
git diff -- .gitignore   # must be EMPTY (excluded)
git grep -c "toolio" -- docs/superpowers/specs/2026-10-03-toolio-rebrand-design.md   # still > 0 (excluded)
git grep -l "toolio_" -- tests | Select-Object -First 5   # expect empty
```

- [ ] **Step 6: Semantic fallout A — memory-root chain (TDD, RED first)**

The bulk replace turned `.toolio` into `.toolio` everywhere, which silently DELETED the legacy `.toolio` read. Restore it as a chain.

6a. In `tests/unit/test_toolio_identity_compat.py` replace the whole `class TestMemoryMigration:` block (docstring says "``.toolio`` / ``.evo`` memories migrate into ``.toolio`` safely.") with:

```python
class TestMemoryRootChain:
    """Existing memory roots are read in place; fresh worktrees use ``.toolio``."""

    def test_toolio_root_created_when_nothing_exists(self, tmp_path: Path) -> None:
        out = resolve_memory_dir(tmp_path)
        assert out == tmp_path / ".toolio" / "memory"
        assert out.is_dir()

    def test_existing_toolio_root_read_in_place(self, tmp_path: Path) -> None:
        legacy = tmp_path / ".toolio" / "memory"
        legacy.mkdir(parents=True)
        (legacy / "m.json").write_text('{"id": "x"}', encoding="utf-8")

        out = resolve_memory_dir(tmp_path)

        assert out == legacy
        assert (out / "m.json").read_text(encoding="utf-8") == '{"id": "x"}'
        assert not (tmp_path / ".toolio").exists(), "no migration: .toolio must not be created"

    def test_existing_toolio_root_read_in_place(self, tmp_path: Path) -> None:
        legacy = tmp_path / ".toolio" / "memory"
        legacy.mkdir(parents=True)

        out = resolve_memory_dir(tmp_path)

        assert out == legacy
        assert not (tmp_path / ".toolio").exists()

    def test_toolio_wins_over_legacy_when_both_exist(self, tmp_path: Path) -> None:
        toolio = tmp_path / ".toolio" / "memory"
        toolio.mkdir(parents=True)
        (toolio / "new.json").write_text("{}", encoding="utf-8")
        old = tmp_path / ".toolio" / "memory"
        old.mkdir(parents=True)
        (old / "old.json").write_text("{}", encoding="utf-8")

        out = resolve_memory_dir(tmp_path)

        assert out == toolio
        assert (old / "old.json").exists(), "legacy root untouched"
```

6b. Run — expect RED (current code copies `.toolio` into `.toolio` and has no `.toolio` check):

```powershell
& ".venv\Scripts\python.exe" -m pytest tests\unit\test_toolio_identity_compat.py -q --no-header -p no:cacheprovider
```

6c. In `toolio/config.py` replace the entire `resolve_memory_dir` function (current post-bulk state copies legacy dirs — delete that whole body) with:

```python
def resolve_memory_dir(worktree: str | Path) -> Path:
    """Return the memory directory for a worktree.

    Resolution takes the first existing of ``.toolio``, ``.toolio``,
    ``.toolio``, ``.evo`` (checked as ``<root>/memory``); if none exists,
    ``.toolio/memory`` is created. Existing roots are used in place —
    memory is never copied, moved, or deleted.
    """
    root = Path(worktree)
    for name in (".toolio", ".toolio", ".toolio", ".evo"):
        candidate = root / name / "memory"
        if candidate.exists():
            return candidate
    canonical = root / ".toolio" / "memory"
    canonical.mkdir(parents=True, exist_ok=True)
    return canonical
```

Then remove `import shutil` from `toolio/config.py` if ruff reports it unused (it was only used by the old `copytree`).

6d. In `toolio/bridge.py` (~line 58) replace the stale comment:

```python
        # Memory root: first existing of .toolio/.toolio/.toolio/.evo,
        # else .toolio — read in place, never migrated (see resolve_memory_dir).
        storage_dir = resolve_memory_dir(worktree)
```

6e. In `toolio/plugin_source.py` the two chain literals were bulk-renamed to `[".toolio", ".toolio", ".evo"]` — reinsert the legacy entry so both read exactly:

```ts
  for (const dir of [".toolio", ".toolio", ".toolio", ".evo"]) {
```

(There is one at the old line 283 inside `memoryRoot` — whose fallback line `return resolve(worktree, ".toolio")` is already correct post-bulk — and one at the old line 342 inside `hasMemoryRoot`. Change ONLY the two array literals; verify the fallback returns `.toolio`.)

6f. GREEN check: run `tests\unit\test_toolio_identity_compat.py` again → all pass.

- [ ] **Step 7: Semantic fallout B — bridge discovery toolio-only (TDD, RED first)**

7a. Rewrite the legacy-env tests. In `tests/unit/test_toolio_discovery_comprehensive.py`: DELETE `test_tier1_evo_home_fallback` and `test_tier1_toolio_home_takes_precedence` (they pin removed behavior), and ADD:

```python
    def test_tier1_legacy_home_envs_not_honoured(self, tmp_path: Path) -> None:
        """LEREV_HOME / EVO_HOME are no longer honoured (no compat fallbacks)."""
        home = tmp_path / "legacy_home"
        (home / "toolio").mkdir(parents=True)
        (home / "toolio" / "bridge.py").write_text("", encoding="utf-8")

        with patch.dict(os.environ, {"LEREV_HOME": str(home), "EVO_HOME": str(home)}, clear=True):
            result = discover_bridge(str(tmp_path))

        assert result is None or not result.bridge_path.startswith(str(home))
```

(The remaining `test_tier1_toolio_home` and its `home/"toolio"` fixture are already correct after the bulk replace.)

In `tests/unit/test_toolio_identity_compat.py`: DELETE `test_toolio_home_env_honoured` and `test_evo_home_env_honoured`, and ADD (inside the same class):

```python
    def test_legacy_home_envs_not_honoured(self, tmp_path: Path) -> None:
        home = tmp_path / "legacy_root"
        (home / "toolio").mkdir(parents=True)
        (home / "toolio" / "bridge.py").write_text("", encoding="utf-8")

        import os

        with patch.dict(os.environ, {"LEREV_HOME": str(home), "EVO_HOME": str(home)}, clear=True):
            discovery = discover_bridge(str(REPO_ROOT))

        assert discovery is None or not discovery.bridge_path.startswith(str(home))
```

7b. Run both test files → RED (discovery still honours the legacy envs).

7c. In `toolio/discovery.py` replace legacy alias handling — the post-state of the whole file is:

```python
"""Toolio bridge discovery — 4-tier cascade."""

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
    """Discover the Toolio bridge using a 4-tier cascade.

    Tier 1: SCHOOL_HOME env var
    Tier 2: toolio-bridge on PATH
    Tier 3: python -m toolio.bridge
    Tier 4: Dev fallback ({worktree}/scripts/toolio_bridge.py)
    """
    python = _find_python()

    # Tier 1: env-configured install root
    home = os.environ.get("SCHOOL_HOME")
    if home:
        bridge_path = str(Path(home) / "toolio" / "bridge.py")
        if _file_exists(bridge_path):
            return BridgeDiscovery(
                python=python or "python3",
                bridge_path=bridge_path,
                tier="SCHOOL_HOME",
            )

    # Tier 2: bridge launcher on PATH
    bridge_cmd = shutil.which("toolio-bridge")
    if bridge_cmd:
        return BridgeDiscovery(python="", bridge_path=bridge_cmd, tier="PATH")

    # Tier 3: installed module (only if python is available). The actual
    # module invocation happens in the plugin; we probe importability here.
    if python:
        try:
            import importlib.util

            spec = importlib.util.find_spec("toolio.bridge")
            if spec is not None and spec.origin is not None:
                return BridgeDiscovery(
                    python=python,
                    bridge_path="-m toolio.bridge",
                    tier="installed_module",
                )
        except (ImportError, ValueError):
            pass

    # Tier 4: Dev fallback
    dev_bridge = str(Path(worktree) / "scripts" / "toolio_bridge.py")
    if _file_exists(dev_bridge):
        return BridgeDiscovery(
            python=python or "python3",
            bridge_path=dev_bridge,
            tier="dev_fallback",
        )

    return None
```

7d. In `toolio/plugin_source.py`, the bulk replace already renamed `SCHOOL_HOME`→`SCHOOL_HOME`, `toolioHome`→`toolioHome`, `toolio-bridge`→`toolio-bridge`, `toolio.bridge`→`toolio.bridge`, `toolio_bridge.py`→`toolio_bridge.py`. What remains is stripping the legacy aliases. Post-state of `discoverBridge` and its doc comment (keep the surrounding helpers and the single-element `for` loops — tests pin the `where ${command}` / `which ${command}` strings):

```ts
/**
 * Discover the Toolio bridge using a 4-tier cascade.
 */
async function discoverBridge(worktree: string): Promise<BridgeInfo | null> {
  const python = await findPython()

  // Tier 1: SCHOOL_HOME env var
  const toolioHome = process.env.SCHOOL_HOME
  if (toolioHome) {
    const bridgePath = resolve(toolioHome, "toolio", "bridge.py")
    if (fileExists(bridgePath)) {
      return { python: python ?? "python3", bridgePath, tier: "SCHOOL_HOME" }
    }
  }

  // Tier 2: bridge launcher on PATH
  for (const command of ["toolio-bridge"]) {
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
    for (const module of ["toolio.bridge"]) {
      const available = await testModule(python, module)
      if (available) {
        return { python, bridgePath: `-m ${module}`, tier: "installed_module" }
      }
    }
  }

  // Tier 4: Dev fallback
  for (const script of ["toolio_bridge.py"]) {
    const devBridge = resolve(worktree, "scripts", script)
    if (fileExists(devBridge)) {
      return { python: python ?? "python3", bridgePath: devBridge, tier: "dev_fallback" }
    }
  }

  return null
}
```

Delete the old doc-comment lines mentioning `LEREV_HOME / EVO_HOME / toolio-bridge / toolio.bridge / toolio_bridge.py` and the `// Legacy aliases ...` comments.

7e. In `tests/unit/test_toolio_plugin_bridge.py` (`test_cross_platform_bridge_discovery`, ~line 67-73):
- docstring → `"""Plugin uses cross-platform PATH detection."""`
- change `assert "toolio-bridge" in TS_PLUGIN_SOURCE` → `assert "toolio-bridge" not in TS_PLUGIN_SOURCE`
- keep `assert "toolio-bridge" in TS_PLUGIN_SOURCE` (bulk already renamed it).

7f. Leave `test_plugin_has_legacy_fallbacks_only`'s allowlist in `test_toolio_identity_compat.py` untouched — it is a whitelist of tolerable tokens (`.toolio` is still a real legacy path); entries that no longer occur are harmless.

7g. GREEN: run both test files + `tests\unit\test_toolio_plugin_bridge.py`.

- [ ] **Step 8: Refresh the editable install (required for import resolution)**

The venv currently carries a stale editable dist `ai-learning-engine` (old brand) whose finder predates the rename.

```powershell
& ".venv\Scripts\python.exe" -m pip uninstall -y ai-learning-engine toolio toolio toolio
```

Ignore "not installed" warnings. Then:

```powershell
& ".venv\Scripts\python.exe" -m pip install -e .
```

If hatchling is missing and the build-isolation download fails, retry:

```powershell
& ".venv\Scripts\python.exe" -m pip install hatchling; if ($?) { & ".venv\Scripts\python.exe" -m pip install -e . --no-build-isolation }
```

Verify: `& ".venv\Scripts\python.exe" -c "import toolio; print(toolio.__version__)"` → `2.6.0`.

- [ ] **Step 9: TS syntax check**

```powershell
$env:PYTHONIOENCODING='utf-8'; & ".venv\Scripts\python.exe" -c "from toolio.plugin_source import TS_PLUGIN_SOURCE; from pathlib import Path; p = Path(r'C:\Users\dex34\AppData\Local\Temp\opencode\toolio-check.ts'); p.write_text(TS_PLUGIN_SOURCE, encoding='utf-8'); print(p)"; if ($?) { node --check C:\Users\dex34\AppData\Local\Temp\opencode\toolio-check.ts }
```

Expected: exit 0.

- [ ] **Step 10: Full suite → fix fallout until green**

```powershell
& ".venv\Scripts\python.exe" -m pytest -q --no-header -p no:cacheprovider
```

Expected failure classes if anything remains (fix in place, do not weaken assertions):
- `ModuleNotFoundError: toolio` in subprocess/integration tests → Step 8 was skipped or failed; rerun it.
- Tests asserting copy/migration semantics elsewhere (search `copytree`/`copied` under `tests/`) → rewrite to chain semantics (same rules as Step 6).
- `toolio-bridge` / `LEREV_HOME` / `EVO_HOME` pins outside Step 7's files → grep: `git grep -ln "toolio-bridge\|LEREV_HOME\|EVO_HOME" -- tests` and apply the same not-honoured treatment.
- Literal-brand pins (`"toolio ..."` assertions) that bulk-rename should have caught but did not (odd casing/split strings) → fix the literal on both sides of the assertion.

Ruff gate (no NEW errors):

```powershell
& ".venv\Scripts\python.exe" -m ruff check toolio tests scripts toolio 2>&1 | Select-Object -Last 10
```

Compare against pre-task baseline (16 pre-existing E501 in `plugin_source` were the known set; any other pre-existing counts: run the same command at BASE if in doubt). New errors must be zero.

- [ ] **Step 11: Commit**

```powershell
git add -A -- ':!.opencode'
git commit -m "refactor(rebrand): rename toolio to toolio across package, tests, packaging, and docs"
git rev-parse --short HEAD
```

Do not stage `.opencode/**` (must show no changes anyway).

---

### Task 2: Console entry points + CLI/bridge smoke

**Files:**
- Modify: `pyproject.toml` (`[project.scripts]`)
- Modify: `tests/unit/test_toolio_identity_compat.py` (`test_pyproject_keeps_legacy_console_script` → rewritten)

**Interfaces:**
- Consumes: Task 1's `toolio` package (`toolio.cli:main`, `toolio.bridge:main` both exist — `main` in `toolio/bridge.py` is imported by the identity shim test already).
- Produces: console scripts `toolio` and `toolio-bridge` in `.venv\Scripts`; no `toolio`/`toolio`/`ai-learning-engine` scripts. Later tasks smoke-test `toolio doctor` and `toolio install --force`.

- [ ] **Step 1: Rewrite the pyproject test (RED first)**

In `tests/unit/test_toolio_identity_compat.py`, replace `test_pyproject_keeps_legacy_console_script` with:

```python
    def test_pyproject_console_scripts(self) -> None:
        text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        assert 'name = "toolio"' in text
        assert 'toolio = "toolio.cli:main"' in text
        assert 'toolio-bridge = "toolio.bridge:main"' in text
        assert "toolio =" not in text
        assert "toolio =" not in text
```

Run:

```powershell
& ".venv\Scripts\python.exe" -m pytest tests\unit\test_toolio_identity_compat.py::TestLegacyCompat::test_pyproject_console_scripts -q --no-header -p no:cacheprovider
```

Expected: FAIL (toolio alias present, toolio-bridge missing).

- [ ] **Step 2: Edit `pyproject.toml`**

Replace the whole scripts block (post-bulk state contains `toolio = ...` plus the surviving `toolio = ...` alias and its comment) with exactly:

```toml
[project.scripts]
toolio = "toolio.cli:main"
toolio-bridge = "toolio.bridge:main"
```

(Delete the `# Legacy alias ...` comment lines along with the `toolio` entry.)

- [ ] **Step 3: GREEN + refresh install**

```powershell
& ".venv\Scripts\python.exe" -m pytest tests\unit\test_toolio_identity_compat.py -q --no-header -p no:cacheprovider
& ".venv\Scripts\python.exe" -m pip install -e .
```

- [ ] **Step 4: Verify entry points**

```powershell
Test-Path .venv\Scripts\toolio.exe            # True
Test-Path .venv\Scripts\toolio-bridge.exe     # True
Test-Path .venv\Scripts\toolio.exe           # False
Test-Path .venv\Scripts\toolio.exe             # False
```

- [ ] **Step 5: Live smoke (bridge path — the silent-failure risk from the spec)**

```powershell
$env:PYTHONIOENCODING='utf-8'
& ".venv\Scripts\toolio.exe" version
'{\"command\": \"status\"}' | & ".venv\Scripts\toolio-bridge.exe"
& ".venv\Scripts\python.exe" -m toolio.bridge
```

(The first two must print `toolio 2.6.0` and a JSON `ok` payload; the module call reads its payload from stdin — pipe the same JSON if it waits.) Then:

```powershell
& ".venv\Scripts\toolio.exe" doctor
```

Expected: doctor checks PASS (bridge tier found — `PATH` or `installed_module` or `dev_fallback`).

- [ ] **Step 6: Full suite + ruff on changed files (expect 0 new) + commit**

```powershell
& ".venv\Scripts\python.exe" -m pytest -q --no-header -p no:cacheprovider
& ".venv\Scripts\python.exe" -m ruff check pyproject.toml tests\unit\test_toolio_identity_compat.py
git add pyproject.toml tests/unit/test_toolio_identity_compat.py
git commit -m "feat(cli): add toolio and toolio-bridge console scripts; drop toolio/toolio aliases"
```

---

### Task 3: `toolio install --force` removes stale previous-brand artifacts

**Files:**
- Modify: `toolio/cli.py` (`_cmd_install`, ~line 117)
- Modify: `tests/unit/test_cli.py` (new test)

**Interfaces:**
- Consumes: Task 1's `toolio.ts` plugin file name (`config.toolio_plugin_file()`), `config.opencode_plugins_dir()` (returns `~/.config/opencode/plugins`).
- Produces: `_clean_stale_brand(config, verbose=True) -> bool` called from `_cmd_install` before the write; guarantees `plugins/toolio.ts` and `skills/toolio-routing/` are deleted on every install (with or without `--force`) so OpenCode never registers duplicate `toolio_*` + `toolio_*` tools.

- [ ] **Step 1: Failing test** (add to `tests/unit/test_cli.py`, class `TestCLI`):

```python
    def test_install_removes_stale_toolio_artifacts(self, tmp_path: Path) -> None:
        """toolio install deletes the previous brand's plugin and skill."""
        config_dir = tmp_path / ".config" / "opencode"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "opencode.jsonc"
        config_file.write_text('{"plugin": []}', encoding="utf-8")
        plugins_dir = config_dir / "plugins"
        plugins_dir.mkdir(parents=True)
        stale_plugin = plugins_dir / "toolio.ts"
        stale_plugin.write_text("// stale previous brand", encoding="utf-8")
        stale_skill = config_dir / "skills" / "toolio-routing"
        stale_skill.mkdir(parents=True)
        (stale_skill / "SKILL.md").write_text("name: toolio-routing", encoding="utf-8")

        with (
            patch("sys.argv", ["toolio", "install", "--force"]),
            patch("toolio.cli.ToolioConfig") as MockConfig,
        ):
            config = MockConfig.return_value
            config.is_toolio_installed.return_value = False
            config.opencode_plugins_dir.return_value = plugins_dir
            config.toolio_plugin_file.return_value = plugins_dir / "toolio.ts"
            config.opencode_config_file.return_value = config_file
            main()

        assert not stale_plugin.exists(), "stale toolio.ts must be deleted"
        assert not stale_skill.exists(), "stale toolio-routing skill must be deleted"
        assert (plugins_dir / "toolio.ts").exists()
```

- [ ] **Step 2: Run to verify it fails**

```powershell
& ".venv\Scripts\python.exe" -m pytest tests\unit\test_cli.py::TestCLI::test_install_removes_stale_toolio_artifacts -q --no-header -p no:cacheprovider
```

Expected: FAIL — `stale toolio.ts must be deleted`.

- [ ] **Step 3: Implement** — in `toolio/cli.py`, add after the `_clean_legacy_plugin` function definition (make sure `shutil` is already imported — it is):

```python
def _clean_stale_brand(config: ToolioConfig, verbose: bool = True) -> bool:
    """Remove previous-brand artefacts so OpenCode never loads duplicates.

    Deletes ``plugins/toolio.ts`` and ``skills/toolio-routing/`` written
    by pre-rebrand installs of this product.
    """
    removed = False

    stale_plugin = config.opencode_plugins_dir() / "toolio.ts"
    if stale_plugin.is_file():
        try:
            stale_plugin.unlink()
            removed = True
            if verbose:
                print(f"Removed stale previous-brand plugin: {stale_plugin}")
        except OSError:
            pass

    stale_skill = config.opencode_plugins_dir().parent / "skills" / "toolio-routing"
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

(Annotation is `ToolioConfig` — the class name after Task 1's bulk rename.) Then in `_cmd_install`, immediately after `_clean_legacy_plugin(config)`:

```python
    # Remove stale previous-brand artefacts (rebrand cleanup)
    _clean_stale_brand(config)
```

The literal `"toolio.ts"` and `"toolio-routing"` strings are INTENTIONAL — they name the stale artifacts; never re-rename them.

- [ ] **Step 4: GREEN**

```powershell
& ".venv\Scripts\python.exe" -m pytest tests\unit\test_cli.py -q --no-header -p no:cacheprovider
```

- [ ] **Step 5: Live reinstall + artifact verification**

```powershell
$env:PYTHONIOENCODING='utf-8'
& ".venv\Scripts\toolio.exe" install --force
Test-Path $env:USERPROFILE\.config\opencode\plugins\toolio.ts    # must be False
Test-Path $env:USERPROFILE\.config\opencode\plugins\toolio.ts     # must be True
& ".venv\Scripts\python.exe" -c "from toolio.plugin_source import TS_PLUGIN_SOURCE; from pathlib import Path; ip = Path.home() / '.config/opencode/plugins/toolio.ts'; print('MATCH' if ip.exists() and ip.read_text(encoding='utf-8') == TS_PLUGIN_SOURCE else 'MISMATCH')"
```

Expected: install output shows the stale removal (if the file existed) and `MATCH`.

- [ ] **Step 6: TS syntax check on the installed file**

```powershell
node --check $env:USERPROFILE\.config\opencode\plugins\toolio.ts
```

Expected: exit 0.

- [ ] **Step 7: Full suite + commit**

```powershell
& ".venv\Scripts\python.exe" -m pytest -q --no-header -p no:cacheprovider
& ".venv\Scripts\python.exe" -m ruff check toolio\cli.py tests\unit\test_cli.py
git add toolio/cli.py tests/unit/test_cli.py
git commit -m "feat(cli): toolio install removes stale previous-brand plugin and skill artifacts"
```

---

### Task 4: Audit, docs polish, full battery, push

**Files:**
- Modify: `.gitignore` (memory block)
- Modify: `docs/superpowers/specs/2026-10-03-toolio-rebrand-design.md` (status line only — file is excluded from bulk)
- Modify (as audit finds): any doc with a stale/incorrect `toolio` reference
- Verify-only: everything else

**Interfaces:**
- Consumes: Tasks 1–3 (renamed world, entry points, install cleanup).
- Produces: greppy-clean repo, pushed `toolio` remote, ledger note for Phase 1 resume.

- [ ] **Step 1: `.gitignore` memory block**

Replace the block (post-Task-1 state is unchanged because the file was excluded) so it reads:

```gitignore
# Toolio runtime memory (legacy .teacher/ and .toolio/ kept for existing projects)
.toolio/
.teacher/
.toolio/
```

(This replaces the old block that had only the comment + `.teacher/` + `.toolio/`. Keep `.teacher/` and `.toolio/` — stale dirs remain on disk per spec. Note: `.gitignore` was EXCLUDED from Task 1's bulk rename, so this edit must use the literal `.teacher/` text.)

- [ ] **Step 2: Spec status line**

In `docs/superpowers/specs/2026-10-03-toolio-rebrand-design.md` line 4, replace:

```
**Status:** approved design (scope + data decisions answered by user; spec pending user review)
```

with:

```
**Status:** approved (spec reviewed by user; implemented by docs/superpowers/plans/2026-10-03-toolio-rebrand.md)
```

- [ ] **Step 3: Repo-wide `toolio` audit**

```powershell
git grep -in "teacher" -- ':!.gitignore' ':!docs/superpowers/specs/2026-10-03-toolio-rebrand-design.md'
```

Every hit must fall into one of these allowlisted classes — anything else is a bug to fix in this step:
1. `.teacher` memory-root chain literals (in `toolio/config.py`, `toolio/plugin_source.py`, the chain tests, and comments naming the legacy root).
2. Stale-artifact names: `"teacher.ts"`, `"teacher-routing"` in `toolio/cli.py` + `tests/unit/test_cli.py` (intentional — they name the previous brand's files).
3. Intentional legacy prose that documents the chain (e.g. docstrings saying "legacy `.teacher` roots are read in place").

Fix all other hits (this includes `tests/conftest.py`'s docstring only if it mentions teacher — it does not; and any README/docs leftovers). Also run:

```powershell
git grep -in "teacher" -- README.md docs packaging scripts toolio.spec toolio
```

twice-verified clean (or down to allowlist items only). Check the in-flight adaptive-routing docs are fully rebranded:

```powershell
git grep -c "toolio_" -- docs/superpowers/plans/2026-10-02-adaptive-routing-loop.md .superpowers/sdd/2026-10-02-adaptive-routing-loop/task-3-brief.md
git grep -in "teacher" -- docs/superpowers/plans/2026-10-02-adaptive-routing-loop.md .superpowers/sdd
```

(Second command: only allowlist hits 1-3 may appear.)

- [ ] **Step 4: Append ledger note** (append to `.superpowers/sdd/2026-10-02-adaptive-routing-loop/progress.md` — the Phase 1 ledger — as a new line):

```
Note (rebrand): teacher→toolio rebrand completed; all plan/brief paths now toolio/. plugin_source.py line numbers shifted (discovery/memory-chain edits) — re-locate symbols by grep when resuming Task 3. Description strings bulk-renamed identically on TS and MCP; parity tests hold.
```

- [ ] **Step 5: Full verification battery**

```powershell
$env:PYTHONIOENCODING='utf-8'
& ".venv\Scripts\python.exe" -m pytest -q --no-header -p no:cacheprovider
```

Expected: all green; record the count (baseline 2507 — Task 3 added 1 test; report the exact delta and its cause if any).

```powershell
& ".venv\Scripts\python.exe" -m ruff check toolio tests scripts toolio 2>&1 | Select-Object -Last 10   # 0 NEW vs baseline
$env:PYTHONIOENCODING='utf-8'; & ".venv\Scripts\python.exe" -c "from toolio.plugin_source import TS_PLUGIN_SOURCE; from pathlib import Path; p = Path(r'C:\Users\dex34\AppData\Local\Temp\opencode\toolio-check.ts'); p.write_text(TS_PLUGIN_SOURCE, encoding='utf-8'); print(p)"; if ($?) { node --check C:\Users\dex34\AppData\Local\Temp\opencode\toolio-check.ts }
& ".venv\Scripts\python.exe" -c "from toolio.plugin_source import TS_PLUGIN_SOURCE; from pathlib import Path; ip = Path.home() / '.config/opencode/plugins/toolio.ts'; print('MATCH' if ip.exists() and ip.read_text(encoding='utf-8') == TS_PLUGIN_SOURCE else 'MISMATCH')"
& ".venv\Scripts\toolio.exe" doctor
& ".venv\Scripts\python.exe" -m pytest tests\integration\test_mcp_stdio.py tests\unit\test_mcp_server.py -q --no-header -p no:cacheprovider
& ".venv\Scripts\toolio.exe" mcp config opencode
```

All must pass/report sane output (`MATCH`, doctor PASS, mcp config prints `python -m toolio.mcp`).

- [ ] **Step 6: Commit**

```powershell
git add .gitignore docs/superpowers/specs/2026-10-03-toolio-rebrand-design.md README.md docs .superpowers
git commit -m "docs(rebrand): toolio memory gitignore entry, audit fixes, spec status"
git status --porcelain   # only .opencode junk may remain untracked/unstaged
```

- [ ] **Step 7: Push to the toolio remote**

```powershell
git remote -v                 # toolio -> https://github.com/dex34132-web/A-Toolio-For-AI.git
git push toolio main
```

Verify: `git log toolio/main --oneline -3` matches local HEAD.

- [ ] **Step 8: Handoff note (report only)**

In the task report state: (a) restart OpenCode to load `toolio.ts` (the running session still has the old `teacher.ts` loaded); (b) Phase 1 resumes at adaptive-routing Task 3 using the rebranded brief — re-locate `plugin_source.py` line anchors by symbol.
