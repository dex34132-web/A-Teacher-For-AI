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

