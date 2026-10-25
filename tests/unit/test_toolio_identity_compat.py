"""Toolio identity + TOOLIO legacy-compatibility tests.

Covers the repository-wide TOOLIO -> Toolio migration:
- canonical Toolio identity (package, CLI, bridge, OpenCode tools)
- Classroom terminology guard (technical ``group`` usages must be untouched)
- legacy compat (``import toolio`` shim, ``toolio`` console script,
  memory-root chain read in place without migration)
- no stale public TOOLIO identity outside the labelled legacy surface
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from toolio.config import ToolioConfig, resolve_memory_dir
from toolio.discovery import discover_bridge
from toolio.plugin_source import TS_PLUGIN_SOURCE

REPO_ROOT = Path(__file__).resolve().parents[2]


class TestToolioIdentity:
    """Canonical Toolio identity is wired end to end."""

    def test_package_version(self) -> None:
        import toolio

        assert toolio.__version__ == "2.6.0"

    def test_legacy_class_aliases(self) -> None:
        from core.routing.integration import (
            ToolioIntegrationBridge,
            ToolioIntegrationBridge,
        )
        from toolio.config import ToolioConfig

        assert ToolioConfig is ToolioConfig
        assert ToolioIntegrationBridge is ToolioIntegrationBridge

    def test_cli_version_reports_toolio(self, capsys) -> None:
        from toolio.cli import main

        with patch("sys.argv", ["toolio", "version"]):
            main()
        assert "toolio 2.6.0" in capsys.readouterr().out

    def test_plugin_exports_toolio(self) -> None:
        # OpenCode 1.18's file-plugin loader requires `default export { server }`.
        # A bare `export default Toolio` is rejected at import time, so the
        # server function must be reachable via the `server` key.
        assert "export default { id: \"toolio\", server: Toolio, setup: toolioV2Setup }" in TS_PLUGIN_SOURCE
        assert "const Toolio: Plugin" in TS_PLUGIN_SOURCE
        assert 'const TOOLIO_VERSION = "' in TS_PLUGIN_SOURCE

    def test_plugin_tools_are_toolio_named(self) -> None:
        for tool in (
            "toolio_status",
            "toolio_learn",
            "toolio_recall",
            "toolio_search",
            "toolio_conflict",
            "toolio_confidence",
            "toolio_deduplicate",
            "toolio_knowledge",
            "toolio_lifecycle",
            "toolio_diagnose",
            "toolio_remember",
        ):
            assert f"{tool}" in TS_PLUGIN_SOURCE, tool

    def test_bridge_dispatches_toolio_commands(self) -> None:
        bridge_src = (REPO_ROOT / "toolio" / "bridge.py").read_text(encoding="utf-8")
        assert '"toolio_remember"' in bridge_src
        assert '"toolio_diagnose"' in bridge_src
        assert "Toolio" not in bridge_src
        assert '"toolio' not in bridge_src
        assert "toolio_" not in bridge_src

    def test_plugin_has_legacy_fallbacks_only(self) -> None:
        allowed = {
            "TOOLIO_HOME",
            "toolio-bridge",
            "toolio.bridge",
            "toolio_bridge.py",
            '"toolio"',
            "'toolio'",
            "toolio.ts",
            # Legacy memory-root fallback: hasMemoryRoot must detect
            # pre-rename .toolio/memory projects so hooks run there too
            # (README: .toolio/memory migrated non-destructively).
            '".toolio"',
        }
        for lineno, line in enumerate(TS_PLUGIN_SOURCE.splitlines(), start=1):
            if "toolio" not in line:
                continue
            assert any(token in line for token in allowed), (
                f"unexpected public TOOLIO identity at plugin line {lineno}: {line!r}"
            )


class TestClassroomTerminologyGuard:
    """``group`` stays a technical term; no Classroom rename was applied."""

    def test_no_classroom_term_in_source(self) -> None:
        hits: list[str] = []
        for base in ("core", "toolio", "scripts"):
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

    def test_import_toolio_shim(self) -> None:
        import toolio
        import toolio

        assert toolio.__version__ == toolio.__version__ == "2.6.0"

    def test_toolio_bridge_shim(self) -> None:
        import toolio.bridge as shim
        from toolio.bridge import main

        assert shim.main is main

    def test_toolio_cli_shim(self) -> None:
        import toolio.cli as shim
        from toolio.cli import main

        assert shim.main is main

    def test_pyproject_console_scripts(self) -> None:
        text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        assert 'name = "toolio"' in text
        assert 'toolio = "toolio.cli:main"' in text
        assert 'toolio-bridge = "toolio.bridge:main"' in text
        assert "teacher =" not in text
        assert "toolio =" not in text

    def test_legacy_plugin_methods(self, tmp_path: Path) -> None:
        with patch.object(Path, "home", return_value=tmp_path):
            config = ToolioConfig()
        assert config.toolio_plugin_file().name == "toolio.ts"
        assert not config.is_toolio_installed()

    def test_legacy_home_envs_not_honoured(self, tmp_path: Path) -> None:
        home = tmp_path / "legacy_root"
        (home / "toolio").mkdir(parents=True)
        (home / "toolio" / "bridge.py").write_text("", encoding="utf-8")

        import os

        with patch.dict(os.environ, {"TOOLIO_HOME": str(home), "EVO_HOME": str(home)}, clear=True):
            discovery = discover_bridge(str(REPO_ROOT))

        assert discovery is None or not discovery.bridge_path.startswith(str(home))


class TestMemoryRootChain:
    """Existing memory roots are read in place; fresh worktrees use ``.toolio``."""

    def test_toolio_root_created_when_nothing_exists(self, tmp_path: Path) -> None:
        out = resolve_memory_dir(tmp_path)
        assert out == tmp_path / ".toolio" / "memory"
        assert out.is_dir()

    def test_existing_teacher_root_read_in_place(self, tmp_path: Path) -> None:
        legacy = tmp_path / ".teacher" / "memory"
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
        assert not (tmp_path / ".teacher").exists()

    def test_toolio_wins_over_legacy_when_both_exist(self, tmp_path: Path) -> None:
        toolio = tmp_path / ".toolio" / "memory"
        toolio.mkdir(parents=True)
        (toolio / "new.json").write_text("{}", encoding="utf-8")
        old = tmp_path / ".teacher" / "memory"
        old.mkdir(parents=True)
        (old / "old.json").write_text("{}", encoding="utf-8")

        out = resolve_memory_dir(tmp_path)

        assert out == toolio
        assert (old / "old.json").exists(), "legacy root untouched"


class TestStatusDoctorMemoryCandidates:
    """status/doctor memory checks see every root ``resolve_memory_dir`` reads."""

    @staticmethod
    def _teacher_only_worktree(tmp_path: Path) -> None:
        legacy = tmp_path / ".teacher" / "memory"
        legacy.mkdir(parents=True)
        (legacy / "m.json").write_text('{"id": "x"}', encoding="utf-8")

    def test_status_and_doctor_find_teacher_only_memory(
        self, tmp_path: Path, monkeypatch, capsys
    ) -> None:
        from argparse import Namespace

        from toolio.cli import _cmd_doctor, _cmd_status

        self._teacher_only_worktree(tmp_path)
        monkeypatch.chdir(tmp_path)

        with patch("toolio.cli.discover_bridge", return_value=None):
            _cmd_status(Namespace())
            status_out = capsys.readouterr().out
            _cmd_doctor(Namespace())
            doctor_out = capsys.readouterr().out

        assert "Memory: available" in status_out, status_out
        assert "Memory: no data" not in status_out, status_out
        assert "Project memory: exists" in doctor_out, doctor_out


class TestNoStalePublicToolioIdentity:
    """Public surfaces say Toolio; ``toolio`` survives only as labelled legacy."""

    def test_core_sources_free_of_toolio_symbols(self) -> None:
        allowed = {"core/routing/integration.py"}
        hits: list[str] = []
        for path in (REPO_ROOT / "core").rglob("*.py"):
            rel = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
            if rel in allowed:
                continue
            if "toolio" in path.read_text(encoding="utf-8"):
                hits.append(rel)
        assert hits == [], f"stale TOOLIO identity in core: {hits}"

    def test_toolio_package_free_of_toolio_symbols(self) -> None:
        # Labelled legacy surfaces are the only files allowed to mention
        # `toolio`: env/discovery fallbacks, stale-plugin cleanup, shim
        # comments, and the memory-migration comment. Everything else must
        # be Toolio-only — new `toolio` mentions must be classified here.
        allowed = {
            "config.py",
            "discovery.py",
            "cli.py",
            "plugin_source.py",
            "bridge.py",
        }
        hits: list[str] = []
        for path in (REPO_ROOT / "toolio").glob("*.py"):
            if path.name in allowed:
                continue
            if "toolio" in path.read_text(encoding="utf-8"):
                hits.append(path.name)
        assert hits == [], f"stale TOOLIO identity in toolio package: {hits}"

    def test_scripts_entrypoint_is_toolio(self) -> None:
        text = (REPO_ROOT / "scripts" / "toolio_bridge.py").read_text(encoding="utf-8")
        assert "toolio.bridge" in text
        assert "toolio" not in text
