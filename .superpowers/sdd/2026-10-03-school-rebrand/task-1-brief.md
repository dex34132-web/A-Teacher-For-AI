### Task 1: Atomic rename — package, tests, packaging content, in-flight docs (suite green)

**Files:**
- Create (ephemeral, NOT committed): `C:\Users\dex34\AppData\Local\Temp\opencode\rebrand_school.py`
- Rename (git mv): `teacher/` → `school/`, `scripts/teacher_bridge.py` → `scripts/school_bridge.py`, `teacher.spec` → `school.spec`, `packaging/chocolatey/teacher.nuspec` → `school.nuspec`, `packaging/homebrew/teacher.rb` → `school.rb`, `packaging/windows/teacher-installer.nsi` → `school-installer.nsi`, 8 test files `tests/unit/test_teacher_*.py` → `test_school_*.py`
- Modify (semantic hand-edits): `school/config.py`, `school/plugin_source.py`, `school/discovery.py`, `school/bridge.py`, `tests/unit/test_school_identity_compat.py`, `tests/unit/test_school_discovery_comprehensive.py`, `tests/unit/test_school_plugin_bridge.py`
- Every other tracked text file: mechanical replace only

**Interfaces:**
- Produces: package `school` importable (`school.cli`, `school.bridge`, `school.mcp`, `school.plugin_source`, `school.discovery`, `school.config`); tools `school_*`; `resolve_memory_dir(worktree) -> Path` with chain semantics; `discover_bridge(worktree) -> BridgeDiscovery | None` school-only; TS `discoverBridge` school-only; `TEACHER_*` → `SCHOOL_*` everywhere.
- Consumes: nothing (first task).

- [ ] **Step 1: Capture pre-state**

```powershell
Set-Location C:\Users\dex34\OneDrive\Documents\Teach
git rev-parse HEAD          # record as BASE for review package
git status --porcelain      # only .opencode/goals junk expected untracked
```

- [ ] **Step 2: Enumerate the file renames (authoritative check)**

```powershell
git ls-files "*teacher*"
```

Expected (15 paths): `teacher/` package (many files), `scripts/teacher_bridge.py`, `teacher.spec`, `packaging/chocolatey/teacher.nuspec`, `packaging/homebrew/teacher.rb`, `packaging/windows/teacher-installer.nsi`, and the 8 test files:

```
tests/unit/test_teacher_cli_comprehensive.py
tests/unit/test_teacher_discovery_comprehensive.py
tests/unit/test_teacher_identity_compat.py
tests/unit/test_teacher_learn_persistence.py
tests/unit/test_teacher_packaging.py
tests/unit/test_teacher_plugin_bridge.py
tests/unit/test_teacher_plugin_hooks.py
tests/unit/test_teacher_routing.py
```

If any additional path appears, git-mv it to the obvious `school` name as well (report it in the task report).

- [ ] **Step 3: git mv everything**

```powershell
git mv teacher school
git mv scripts/teacher_bridge.py scripts/school_bridge.py
git mv teacher.spec school.spec
git mv packaging/chocolatey/teacher.nuspec packaging/chocolatey/school.nuspec
git mv packaging/homebrew/teacher.rb packaging/homebrew/school.rb
git mv packaging/windows/teacher-installer.nsi packaging/windows/school-installer.nsi
git mv tests/unit/test_teacher_cli_comprehensive.py tests/unit/test_school_cli_comprehensive.py
git mv tests/unit/test_teacher_discovery_comprehensive.py tests/unit/test_school_discovery_comprehensive.py
git mv tests/unit/test_teacher_identity_compat.py tests/unit/test_school_identity_compat.py
git mv tests/unit/test_teacher_learn_persistence.py tests/unit/test_school_learn_persistence.py
git mv tests/unit/test_teacher_packaging.py tests/unit/test_school_packaging.py
git mv tests/unit/test_teacher_plugin_bridge.py tests/unit/test_school_plugin_bridge.py
git mv tests/unit/test_teacher_plugin_hooks.py tests/unit/test_school_plugin_hooks.py
git mv tests/unit/test_teacher_routing.py tests/unit/test_school_routing.py
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
REPLACEMENTS = [("TEACHER", "SCHOOL"), ("Teacher", "School"), ("teacher", "school")]

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
git grep -c "teacher" -- docs/superpowers/specs/2026-10-03-school-rebrand-design.md   # still > 0 (excluded)
git grep -l "teacher_" -- tests | Select-Object -First 5   # expect empty
```

- [ ] **Step 6: Semantic fallout A — memory-root chain (TDD, RED first)**

The bulk replace turned `.teacher` into `.school` everywhere, which silently DELETED the legacy `.teacher` read. Restore it as a chain.

6a. In `tests/unit/test_school_identity_compat.py` replace the whole `class TestMemoryMigration:` block (docstring says "``.lerev`` / ``.evo`` memories migrate into ``.teacher`` safely.") with:

```python
class TestMemoryRootChain:
    """Existing memory roots are read in place; fresh worktrees use ``.school``."""

    def test_school_root_created_when_nothing_exists(self, tmp_path: Path) -> None:
        out = resolve_memory_dir(tmp_path)
        assert out == tmp_path / ".school" / "memory"
        assert out.is_dir()

    def test_existing_teacher_root_read_in_place(self, tmp_path: Path) -> None:
        legacy = tmp_path / ".teacher" / "memory"
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
        old = tmp_path / ".teacher" / "memory"
        old.mkdir(parents=True)
        (old / "old.json").write_text("{}", encoding="utf-8")

        out = resolve_memory_dir(tmp_path)

        assert out == school
        assert (old / "old.json").exists(), "legacy root untouched"
```

6b. Run — expect RED (current code copies `.lerev` into `.school` and has no `.teacher` check):

```powershell
& ".venv\Scripts\python.exe" -m pytest tests\unit\test_school_identity_compat.py -q --no-header -p no:cacheprovider
```

6c. In `school/config.py` replace the entire `resolve_memory_dir` function (current post-bulk state copies legacy dirs — delete that whole body) with:

```python
def resolve_memory_dir(worktree: str | Path) -> Path:
    """Return the memory directory for a worktree.

    Resolution takes the first existing of ``.school``, ``.teacher``,
    ``.lerev``, ``.evo`` (checked as ``<root>/memory``); if none exists,
    ``.school/memory`` is created. Existing roots are used in place —
    memory is never copied, moved, or deleted.
    """
    root = Path(worktree)
    for name in (".school", ".teacher", ".lerev", ".evo"):
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
        # Memory root: first existing of .school/.teacher/.lerev/.evo,
        # else .school — read in place, never migrated (see resolve_memory_dir).
        storage_dir = resolve_memory_dir(worktree)
```

6e. In `school/plugin_source.py` the two chain literals were bulk-renamed to `[".school", ".lerev", ".evo"]` — reinsert the legacy entry so both read exactly:

```ts
  for (const dir of [".school", ".teacher", ".lerev", ".evo"]) {
```

(There is one at the old line 283 inside `memoryRoot` — whose fallback line `return resolve(worktree, ".school")` is already correct post-bulk — and one at the old line 342 inside `hasMemoryRoot`. Change ONLY the two array literals; verify the fallback returns `.school`.)

6f. GREEN check: run `tests\unit\test_school_identity_compat.py` again → all pass.

- [ ] **Step 7: Semantic fallout B — bridge discovery school-only (TDD, RED first)**

7a. Rewrite the legacy-env tests. In `tests/unit/test_school_discovery_comprehensive.py`: DELETE `test_tier1_evo_home_fallback` and `test_tier1_teacher_home_takes_precedence` (they pin removed behavior), and ADD:

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

7d. In `school/plugin_source.py`, the bulk replace already renamed `TEACHER_HOME`→`SCHOOL_HOME`, `teacherHome`→`schoolHome`, `teacher-bridge`→`school-bridge`, `teacher.bridge`→`school.bridge`, `teacher_bridge.py`→`school_bridge.py`. What remains is stripping the legacy aliases. Post-state of `discoverBridge` and its doc comment (keep the surrounding helpers and the single-element `for` loops — tests pin the `where ${command}` / `which ${command}` strings):

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
& ".venv\Scripts\python.exe" -m pip uninstall -y ai-learning-engine teacher lerev school
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
- Literal-brand pins (`"teacher ..."` assertions) that bulk-rename should have caught but did not (odd casing/split strings) → fix the literal on both sides of the assertion.

Ruff gate (no NEW errors):

```powershell
& ".venv\Scripts\python.exe" -m ruff check school tests scripts lerev 2>&1 | Select-Object -Last 10
```

Compare against pre-task baseline (16 pre-existing E501 in `plugin_source` were the known set; any other pre-existing counts: run the same command at BASE if in doubt). New errors must be zero.

- [ ] **Step 11: Commit**

```powershell
git add -A -- ':!.opencode'
git commit -m "refactor(rebrand): rename teacher to school across package, tests, packaging, and docs"
git rev-parse --short HEAD
```

Do not stage `.opencode/**` (must show no changes anyway).

---

