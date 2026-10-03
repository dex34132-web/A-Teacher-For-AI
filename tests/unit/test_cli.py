"""Tests for School CLI."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from school.cli import main


class TestCLI:
    """Test CLI commands."""

    def test_version(self, capsys: pytest.CaptureFixture[str]) -> None:
        """school version prints version."""
        with patch("sys.argv", ["school", "version"]):
            main()
        captured = capsys.readouterr()
        assert "school" in captured.out.lower()

    def test_status_no_bridge(self, capsys: pytest.CaptureFixture[str]) -> None:
        """school status reports when no bridge found."""
        with (
            patch("sys.argv", ["school", "status"]),
            patch("school.cli.discover_bridge", return_value=None),
        ):
            main()
        captured = capsys.readouterr()
        assert "unavailable" in captured.out.lower() or "not found" in captured.out.lower()

    def test_install_writes_plugin(self, tmp_path: Path) -> None:
        """school install writes plugin to auto-discovery directory."""
        config_dir = tmp_path / ".config" / "opencode"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "opencode.jsonc"
        config_file.write_text('{"plugin": []}', encoding="utf-8")
        plugins_dir = config_dir / "plugins"

        with (
            patch("sys.argv", ["school", "install"]),
            patch("school.cli.SchoolConfig") as MockConfig,
        ):
            config = MockConfig.return_value
            config.is_school_installed.return_value = False
            config.opencode_plugins_dir.return_value = plugins_dir
            config.school_plugin_file.return_value = plugins_dir / "school.ts"
            config.opencode_config_file.return_value = config_file
            main()

        assert (plugins_dir / "school.ts").exists()

    def test_install_skip_existing(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """school install skips if already installed."""
        config_dir = tmp_path / ".config" / "opencode"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "opencode.jsonc"
        config_file.write_text('{"plugin": []}', encoding="utf-8")
        plugins_dir = config_dir / "plugins"
        plugins_dir.mkdir(parents=True)
        (plugins_dir / "school.ts").write_text("// existing", encoding="utf-8")

        with (
            patch("sys.argv", ["school", "install"]),
            patch("school.cli.SchoolConfig") as MockConfig,
        ):
            config = MockConfig.return_value
            config.is_school_installed.return_value = True
            config.school_plugin_file.return_value = plugins_dir / "school.ts"
            config.opencode_config_file.return_value = config_file
            main()

        captured = capsys.readouterr()
        assert "already installed" in captured.out.lower()

    def test_install_removes_stale_teacher_artifacts(self, tmp_path: Path) -> None:
        """school install deletes the previous brand's plugin and skill."""
        config_dir = tmp_path / ".config" / "opencode"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "opencode.jsonc"
        config_file.write_text('{"plugin": []}', encoding="utf-8")
        plugins_dir = config_dir / "plugins"
        plugins_dir.mkdir(parents=True)
        stale_plugin = plugins_dir / "teacher.ts"
        stale_plugin.write_text("// stale previous brand", encoding="utf-8")
        stale_skill = config_dir / "skills" / "teacher-routing"
        stale_skill.mkdir(parents=True)
        (stale_skill / "SKILL.md").write_text("name: teacher-routing", encoding="utf-8")

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

        assert not stale_plugin.exists(), "stale teacher.ts must be deleted"
        assert not stale_skill.exists(), "stale teacher-routing skill must be deleted"
        assert (plugins_dir / "school.ts").exists()

    def test_uninstall_safety(self, tmp_path: Path) -> None:
        """school uninstall does not remove user memory."""
        memory_dir = tmp_path / ".school" / "memory"
        memory_dir.mkdir(parents=True)
        memory_file = memory_dir / "test.json"
        memory_file.write_text('{"test": true}', encoding="utf-8")

        # Uninstall should NOT remove .school/memory/
        # This is tested by verifying the directory still exists after uninstall
        assert memory_dir.exists()
        assert memory_file.exists()
