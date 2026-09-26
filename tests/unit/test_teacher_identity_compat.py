"""Teacher identity + LEREV legacy-compatibility tests.

Covers the repository-wide LEREV -> Teacher migration:
- canonical Teacher identity (package, CLI, bridge, OpenCode tools)
- Classroom terminology guard (technical ``group`` usages must be untouched)
- legacy compat (``import lerev`` shim, ``LEREV_HOME``/``EVO_HOME``,
  ``lerev`` console script, non-destructive memory migration)
- no stale public LEREV identity outside the labelled legacy surface
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from teacher.config import TeacherConfig, resolve_memory_dir
from teacher.discovery import discover_bridge
from teacher.plugin_source import TS_PLUGIN_SOURCE

REPO_ROOT = Path(__file__).resolve().parents[2]


class TestTeacherIdentity:
    """Canonical Teacher identity is wired end to end."""

    def test_package_version(self) -> None:
        import teacher

        assert teacher.__version__ == "2.6.0"

    def test_legacy_class_aliases(self) -> None:
        from core.routing.integration import (
            LerevIntegrationBridge,
            TeacherIntegrationBridge,
        )
        from teacher.config import LerevConfig

        assert LerevConfig is TeacherConfig
        assert LerevIntegrationBridge is TeacherIntegrationBridge

    def test_cli_version_reports_teacher(self, capsys) -> None:
        from teacher.cli import main

        with patch("sys.argv", ["teacher", "version"]):
            main()
        assert "teacher 2.6.0" in capsys.readouterr().out

    def test_plugin_exports_teacher(self) -> None:
        assert "export default Teacher" in TS_PLUGIN_SOURCE
        assert "const Teacher: Plugin" in TS_PLUGIN_SOURCE
        assert 'const TEACHER_VERSION = "' in TS_PLUGIN_SOURCE

    def test_plugin_tools_are_teacher_named(self) -> None:
        for tool in (
            "teacher_status",
            "teacher_learn",
            "teacher_recall",
            "teacher_search",
            "teacher_conflict",
            "teacher_confidence",
            "teacher_deduplicate",
            "teacher_knowledge",
            "teacher_lifecycle",
            "teacher_diagnose",
            "teacher_remember",
        ):
            assert f"{tool}" in TS_PLUGIN_SOURCE, tool

    def test_bridge_dispatches_teacher_commands(self) -> None:
        bridge_src = (REPO_ROOT / "teacher" / "bridge.py").read_text(encoding="utf-8")
        assert '"teacher_remember"' in bridge_src
        assert '"teacher_diagnose"' in bridge_src
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
        for base in ("core", "teacher", "scripts"):
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
        import teacher

        assert lerev.__version__ == teacher.__version__ == "2.6.0"

    def test_lerev_bridge_shim(self) -> None:
        import lerev.bridge as shim
        from teacher.bridge import main

        assert shim.main is main

    def test_lerev_cli_shim(self) -> None:
        import lerev.cli as shim
        from teacher.cli import main

        assert shim.main is main

    def test_pyproject_keeps_legacy_console_script(self) -> None:
        text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        assert 'name = "teacher"' in text
        assert 'name = "lerev"' not in text
        assert 'lerev = "teacher.cli:main"' in text

    def test_legacy_plugin_methods(self, tmp_path: Path) -> None:
        with patch.object(Path, "home", return_value=tmp_path):
            config = TeacherConfig()
        assert config.lerev_plugin_file().name == "lerev.ts"
        assert not config.is_lerev_installed()

    def test_lerev_home_env_honoured(self, tmp_path: Path) -> None:
        home = tmp_path / "legacy_root"
        (home / "teacher").mkdir(parents=True)
        (home / "teacher" / "bridge.py").write_text("", encoding="utf-8")

        import os

        old = os.environ.pop("TEACHER_HOME", None)
        try:
            os.environ["LEREV_HOME"] = str(home)
            discovery = discover_bridge(str(REPO_ROOT))
        finally:
            os.environ.pop("LEREV_HOME", None)
            if old is not None:
                os.environ["TEACHER_HOME"] = old

        assert discovery is not None
        assert discovery.tier == "TEACHER_HOME"
        assert discovery.bridge_path.startswith(str(home))

    def test_evo_home_env_honoured(self, tmp_path: Path) -> None:
        home = tmp_path / "evo_root"
        (home / "teacher").mkdir(parents=True)
        (home / "teacher" / "bridge.py").write_text("", encoding="utf-8")

        import os

        old = os.environ.pop("TEACHER_HOME", None)
        old_lerev = os.environ.pop("LEREV_HOME", None)
        try:
            os.environ["EVO_HOME"] = str(home)
            discovery = discover_bridge(str(REPO_ROOT))
        finally:
            os.environ.pop("EVO_HOME", None)
            if old is not None:
                os.environ["TEACHER_HOME"] = old
            if old_lerev is not None:
                os.environ["LEREV_HOME"] = old_lerev

        assert discovery is not None
        assert discovery.tier == "TEACHER_HOME"


class TestMemoryMigration:
    """``.lerev`` / ``.evo`` memories migrate into ``.teacher`` safely."""

    def test_legacy_memory_migrated_non_destructively(self, tmp_path: Path) -> None:
        legacy = tmp_path / ".lerev" / "memory"
        legacy.mkdir(parents=True)
        (legacy / "m.json").write_text('{"id": "x"}', encoding="utf-8")

        out = resolve_memory_dir(tmp_path)

        assert out == tmp_path / ".teacher" / "memory"
        assert (out / "m.json").read_text(encoding="utf-8") == '{"id": "x"}'
        assert (legacy / "m.json").exists(), "source legacy memory must not be deleted"

    def test_existing_canonical_memory_wins(self, tmp_path: Path) -> None:
        canonical = tmp_path / ".teacher" / "memory"
        canonical.mkdir(parents=True)
        (canonical / "keep.json").write_text("{}", encoding="utf-8")
        legacy = tmp_path / ".lerev" / "memory"
        legacy.mkdir(parents=True)
        (legacy / "old.json").write_text("{}", encoding="utf-8")

        out = resolve_memory_dir(tmp_path)

        assert out == canonical
        assert not (canonical / "old.json").exists()

    def test_no_legacy_memory_creates_empty_dir(self, tmp_path: Path) -> None:
        out = resolve_memory_dir(tmp_path)
        assert out == tmp_path / ".teacher" / "memory"
        assert out.is_dir()


class TestNoStalePublicLerevIdentity:
    """Public surfaces say Teacher; ``lerev`` survives only as labelled legacy."""

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

    def test_teacher_package_free_of_lerev_symbols(self) -> None:
        # Labelled legacy surfaces are the only files allowed to mention
        # `lerev`: env/discovery fallbacks, stale-plugin cleanup, shim
        # comments, and the memory-migration comment. Everything else must
        # be Teacher-only — new `lerev` mentions must be classified here.
        allowed = {
            "config.py",
            "discovery.py",
            "cli.py",
            "plugin_source.py",
            "bridge.py",
        }
        hits: list[str] = []
        for path in (REPO_ROOT / "teacher").glob("*.py"):
            if path.name in allowed:
                continue
            if "lerev" in path.read_text(encoding="utf-8"):
                hits.append(path.name)
        assert hits == [], f"stale LEREV identity in teacher package: {hits}"

    def test_scripts_entrypoint_is_teacher(self) -> None:
        text = (REPO_ROOT / "scripts" / "teacher_bridge.py").read_text(encoding="utf-8")
        assert "teacher.bridge" in text
        assert "lerev" not in text
