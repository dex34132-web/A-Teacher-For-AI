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

