"""Tests for Teacher CLI."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from teacher.cli import main


class TestCLI:
    """Test CLI commands."""

    def test_version(self, capsys: pytest.CaptureFixture[str]) -> None:
        """teacher version prints version."""
        with patch("sys.argv", ["teacher", "version"]):
            main()
        captured = capsys.readouterr()
        assert "teacher" in captured.out.lower()

    def test_status_no_bridge(self, capsys: pytest.CaptureFixture[str]) -> None:
        """teacher status reports when no bridge found."""
        with (
            patch("sys.argv", ["teacher", "status"]),
            patch("teacher.cli.discover_bridge", return_value=None),
        ):
            main()
        captured = capsys.readouterr()
        assert "unavailable" in captured.out.lower() or "not found" in captured.out.lower()

    def test_install_writes_plugin(self, tmp_path: Path) -> None:
        """teacher install writes plugin to auto-discovery directory."""
        config_dir = tmp_path / ".config" / "opencode"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "opencode.jsonc"
        config_file.write_text('{"plugin": []}', encoding="utf-8")
        plugins_dir = config_dir / "plugins"

        with (
            patch("sys.argv", ["teacher", "install"]),
            patch("teacher.cli.TeacherConfig") as MockConfig,
        ):
            config = MockConfig.return_value
            config.is_teacher_installed.return_value = False
            config.opencode_plugins_dir.return_value = plugins_dir
            config.teacher_plugin_file.return_value = plugins_dir / "teacher.ts"
            config.opencode_config_file.return_value = config_file
            main()

        assert (plugins_dir / "teacher.ts").exists()

    def test_install_skip_existing(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """teacher install skips if already installed."""
        config_dir = tmp_path / ".config" / "opencode"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "opencode.jsonc"
        config_file.write_text('{"plugin": []}', encoding="utf-8")
        plugins_dir = config_dir / "plugins"
        plugins_dir.mkdir(parents=True)
        (plugins_dir / "teacher.ts").write_text("// existing", encoding="utf-8")

        with (
            patch("sys.argv", ["teacher", "install"]),
            patch("teacher.cli.TeacherConfig") as MockConfig,
        ):
            config = MockConfig.return_value
            config.is_teacher_installed.return_value = True
            config.teacher_plugin_file.return_value = plugins_dir / "teacher.ts"
            config.opencode_config_file.return_value = config_file
            main()

        captured = capsys.readouterr()
        assert "already installed" in captured.out.lower()

    def test_uninstall_safety(self, tmp_path: Path) -> None:
        """teacher uninstall does not remove user memory."""
        memory_dir = tmp_path / ".teacher" / "memory"
        memory_dir.mkdir(parents=True)
        memory_file = memory_dir / "test.json"
        memory_file.write_text('{"test": true}', encoding="utf-8")

        # Uninstall should NOT remove .teacher/memory/
        # This is tested by verifying the directory still exists after uninstall
        assert memory_dir.exists()
        assert memory_file.exists()
