"""School identity + LEREV legacy-compatibility tests.

Covers the repository-wide LEREV -> School migration:
- canonical School identity (package, CLI, bridge, OpenCode tools)
- Classroom terminology guard (technical ``group`` usages must be untouched)
- legacy compat (``import lerev`` shim, ``lerev`` console script,
  memory-root chain read in place without migration)
- no stale public LEREV identity outside the labelled legacy surface
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from school.config import SchoolConfig, resolve_memory_dir
from school.discovery import discover_bridge
from school.plugin_source import TS_PLUGIN_SOURCE

REPO_ROOT = Path(__file__).resolve().parents[2]


class TestSchoolIdentity:
    """Canonical School identity is wired end to end."""

    def test_package_version(self) -> None:
        import school

        assert school.__version__ == "2.6.0"

    def test_legacy_class_aliases(self) -> None:
        from core.routing.integration import (
            LerevIntegrationBridge,
            SchoolIntegrationBridge,
        )
        from school.config import LerevConfig

        assert LerevConfig is SchoolConfig
        assert LerevIntegrationBridge is SchoolIntegrationBridge

    def test_cli_version_reports_school(self, capsys) -> None:
        from school.cli import main

        with patch("sys.argv", ["school", "version"]):
            main()
        assert "school 2.6.0" in capsys.readouterr().out

    def test_plugin_exports_school(self) -> None:
        assert "export default School" in TS_PLUGIN_SOURCE
        assert "const School: Plugin" in TS_PLUGIN_SOURCE
        assert 'const SCHOOL_VERSION = "' in TS_PLUGIN_SOURCE

    def test_plugin_tools_are_school_named(self) -> None:
        for tool in (
            "school_status",
            "school_learn",
            "school_recall",
            "school_search",
            "school_conflict",
            "school_confidence",
            "school_deduplicate",
            "school_knowledge",
            "school_lifecycle",
            "school_diagnose",
            "school_remember",
        ):
            assert f"{tool}" in TS_PLUGIN_SOURCE, tool

    def test_bridge_dispatches_school_commands(self) -> None:
        bridge_src = (REPO_ROOT / "school" / "bridge.py").read_text(encoding="utf-8")
        assert '"school_remember"' in bridge_src
        assert '"school_diagnose"' in bridge_src
        assert "Lerev" not in bridge_src
        assert '"lerev' not in bridge_src
        assert "lerev_" not in bridge_src

    def test_plugin_has_legacy_fallbacks_only(self) -> None:
        allowed = {
            "LEREV_HOME",
            "lerev-bridge",
            "lerev.bridge",
            "lerev_bridge.py",
            '"lerev"',
            "'lerev'",
            "lerev.ts",
            # Legacy memory-root fallback: hasMemoryRoot must detect
            # pre-rename .lerev/memory projects so hooks run there too
            # (README: .lerev/memory migrated non-destructively).
            '".lerev"',
        }
        for lineno, line in enumerate(TS_PLUGIN_SOURCE.splitlines(), start=1):
            if "lerev" not in line:
                continue
            assert any(token in line for token in allowed), (
                f"unexpected public LEREV identity at plugin line {lineno}: {line!r}"
            )


class TestClassroomTerminologyGuard:
    """``group`` stays a technical term; no Classroom rename was applied."""

    def test_no_classroom_term_in_source(self) -> None:
        hits: list[str] = []
        for base in ("core", "school", "scripts"):
            for path in (REPO_ROOT / base).rglob("*.py"):
                if "classroom" in path.read_text(encoding="utf-8").lower():
                    hits.append(str(path.relative_to(REPO_ROOT)))
        assert hits == [], f"classroom leaked into source: {hits}"

    def test_technical_group_terms_preserved(self) -> None:
        total = 0
        for path in (REPO_ROOT / "core").rglob("*.py"):
            total += path.read_text(encoding="utf-8").count("group")
        assert total > 0, "technical group terminology was rewritten away"


class TestLegacyCompat:
    """Pre-rename integrations keep working through labelled aliases."""

    def test_import_lerev_shim(self) -> None:
        import lerev
        import school

        assert lerev.__version__ == school.__version__ == "2.6.0"

    def test_lerev_bridge_shim(self) -> None:
        import lerev.bridge as shim
        from school.bridge import main

        assert shim.main is main

    def test_lerev_cli_shim(self) -> None:
        import lerev.cli as shim
        from school.cli import main

        assert shim.main is main

    def test_pyproject_keeps_legacy_console_script(self) -> None:
        text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        assert 'name = "school"' in text
        assert 'name = "lerev"' not in text
        assert 'lerev = "school.cli:main"' in text

    def test_legacy_plugin_methods(self, tmp_path: Path) -> None:
        with patch.object(Path, "home", return_value=tmp_path):
            config = SchoolConfig()
        assert config.lerev_plugin_file().name == "lerev.ts"
        assert not config.is_lerev_installed()

    def test_legacy_home_envs_not_honoured(self, tmp_path: Path) -> None:
        home = tmp_path / "legacy_root"
        (home / "school").mkdir(parents=True)
        (home / "school" / "bridge.py").write_text("", encoding="utf-8")

        import os

        with patch.dict(os.environ, {"LEREV_HOME": str(home), "EVO_HOME": str(home)}, clear=True):
            discovery = discover_bridge(str(REPO_ROOT))

        assert discovery is None or not discovery.bridge_path.startswith(str(home))


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


class TestNoStalePublicLerevIdentity:
    """Public surfaces say School; ``lerev`` survives only as labelled legacy."""

    def test_core_sources_free_of_lerev_symbols(self) -> None:
        allowed = {"core/routing/integration.py"}
        hits: list[str] = []
        for path in (REPO_ROOT / "core").rglob("*.py"):
            rel = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
            if rel in allowed:
                continue
            if "lerev" in path.read_text(encoding="utf-8"):
                hits.append(rel)
        assert hits == [], f"stale LEREV identity in core: {hits}"

    def test_school_package_free_of_lerev_symbols(self) -> None:
        # Labelled legacy surfaces are the only files allowed to mention
        # `lerev`: env/discovery fallbacks, stale-plugin cleanup, shim
        # comments, and the memory-migration comment. Everything else must
        # be School-only — new `lerev` mentions must be classified here.
        allowed = {
            "config.py",
            "discovery.py",
            "cli.py",
            "plugin_source.py",
            "bridge.py",
        }
        hits: list[str] = []
        for path in (REPO_ROOT / "school").glob("*.py"):
            if path.name in allowed:
                continue
            if "lerev" in path.read_text(encoding="utf-8"):
                hits.append(path.name)
        assert hits == [], f"stale LEREV identity in school package: {hits}"

    def test_scripts_entrypoint_is_school(self) -> None:
        text = (REPO_ROOT / "scripts" / "school_bridge.py").read_text(encoding="utf-8")
        assert "school.bridge" in text
        assert "lerev" not in text
