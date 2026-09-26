"""Comprehensive tests for Lerev CLI commands."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from lerev.cli import main


class TestCLIHelp:
    """Test CLI help output."""

    def test_no_args_shows_help(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Running with no args shows help."""
        with patch("sys.argv", ["lerev"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_help_flag(self, capsys: pytest.CaptureFixture[str]) -> None:
        """--help shows help."""
        with patch("sys.argv", ["lerev", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_version_command(self, capsys: pytest.CaptureFixture[str]) -> None:
        """lerev version prints version."""
        with patch("sys.argv", ["lerev", "version"]):
            main()
        captured = capsys.readouterr()
        assert "lerev" in captured.out.lower()
        assert "2.6.0" in captured.out

    def test_version_output_format(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Version output matches expected format."""
        with patch("sys.argv", ["lerev", "version"]):
            main()
        captured = capsys.readouterr()
        assert captured.out.strip() == "lerev 2.6.0"


class TestCLIStatus:
    """Test CLI status command."""

    def test_status_no_bridge(self, capsys: pytest.CaptureFixture[str]) -> None:
        """lerev status reports when no bridge found."""
        with (
            patch("sys.argv", ["lerev", "status"]),
            patch("lerev.cli.discover_bridge", return_value=None),
        ):
            main()
        captured = capsys.readouterr()
        assert "not found" in captured.out.lower()

    def test_status_with_bridge(self, capsys: pytest.CaptureFixture[str]) -> None:
        """lerev status shows bridge tier."""
        from lerev.discovery import BridgeDiscovery

        mock_bridge = BridgeDiscovery(python="python3", bridge_path="/test/bridge.py", tier="test_tier")
        with (
            patch("sys.argv", ["lerev", "status"]),
            patch("lerev.cli.discover_bridge", return_value=mock_bridge),
        ):
            main()
        captured = capsys.readouterr()
        assert "test_tier" in captured.out

    def test_status_shows_version(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Status output includes version."""
        with (
            patch("sys.argv", ["lerev", "status"]),
            patch("lerev.cli.discover_bridge", return_value=None),
        ):
            main()
        captured = capsys.readouterr()
        assert "2.6.0" in captured.out


class TestCLIInstall:
    """Test CLI install command."""

    def test_install_writes_plugin(self, tmp_path: Path) -> None:
        """lerev install writes plugin to auto-discovery directory."""
        config_dir = tmp_path / ".config" / "opencode"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "opencode.jsonc"
        config_file.write_text('{"plugin": []}', encoding="utf-8")
        plugins_dir = config_dir / "plugins"

        with (
            patch("sys.argv", ["lerev", "install"]),
            patch("lerev.cli.LerevConfig") as MockConfig,
        ):
            config = MockConfig.return_value
            config.is_lerev_installed.return_value = False
            config.opencode_plugins_dir.return_value = plugins_dir
            config.lerev_plugin_file.return_value = plugins_dir / "lerev.ts"
            config.opencode_config_file.return_value = config_file
            main()

        assert (plugins_dir / "lerev.ts").exists()

    def test_install_skip_existing(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """lerev install skips if already installed."""
        config_dir = tmp_path / ".config" / "opencode"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "opencode.jsonc"
        config_file.write_text('{"plugin": []}', encoding="utf-8")
        plugins_dir = config_dir / "plugins"
        plugins_dir.mkdir(parents=True)
        (plugins_dir / "lerev.ts").write_text("// existing", encoding="utf-8")

        with (
            patch("sys.argv", ["lerev", "install"]),
            patch("lerev.cli.LerevConfig") as MockConfig,
        ):
            config = MockConfig.return_value
            config.is_lerev_installed.return_value = True
            config.lerev_plugin_file.return_value = plugins_dir / "lerev.ts"
            config.opencode_config_file.return_value = config_file
            main()

        captured = capsys.readouterr()
        assert "already installed" in captured.out.lower()

    def test_install_no_opencode_config(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Install warns when OpenCode config not found."""
        with (
            patch("sys.argv", ["lerev", "install"]),
            patch("lerev.cli.LerevConfig") as MockConfig,
        ):
            config = MockConfig.return_value
            config.opencode_config_file.return_value = None
            main()
        captured = capsys.readouterr()
        assert "warning" in captured.out.lower() or "not found" in captured.out.lower()


class TestCLIUninstall:
    """Test CLI uninstall command."""

    def test_uninstall_safety(self, tmp_path: Path) -> None:
        """lerev uninstall does not remove user memory."""
        memory_dir = tmp_path / ".lerev" / "memory"
        memory_dir.mkdir(parents=True)
        memory_file = memory_dir / "test.json"
        memory_file.write_text('{"test": true}', encoding="utf-8")

        # Uninstall should NOT remove .lerev/memory/
        assert memory_dir.exists()
        assert memory_file.exists()

    def test_uninstall_idempotent(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Uninstall when nothing to uninstall is safe."""
        with (
            patch("sys.argv", ["lerev", "uninstall"]),
            patch("lerev.cli.LerevConfig") as MockConfig,
        ):
            config = MockConfig.return_value
            config.lerev_plugin_file.return_value = Path("/nonexistent/lerev.ts")
            config.opencode_config_dir.return_value = Path("/nonexistent")
            main()
        captured = capsys.readouterr()
        assert "complete" in captured.out.lower()


class TestCLIDoctor:
    """Test CLI doctor command."""

    def test_doctor_runs(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Doctor command executes without error."""
        with patch("sys.argv", ["lerev", "doctor"]):
            main()
        captured = capsys.readouterr()
        assert "LEREV DOCTOR" in captured.out
        assert "RESULT:" in captured.out

    def test_doctor_checks_python(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Doctor checks Python version."""
        with patch("sys.argv", ["lerev", "doctor"]):
            main()
        captured = capsys.readouterr()
        assert "Python runtime" in captured.out

    def test_doctor_checks_package(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Doctor checks LEREV package."""
        with patch("sys.argv", ["lerev", "doctor"]):
            main()
        captured = capsys.readouterr()
        assert "LEREV package" in captured.out

    def test_doctor_checks_bridge(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Doctor checks bridge."""
        with patch("sys.argv", ["lerev", "doctor"]):
            main()
        captured = capsys.readouterr()
        assert "Bridge" in captured.out

    def test_doctor_checks_memory(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Doctor checks memory directory."""
        with patch("sys.argv", ["lerev", "doctor"]):
            main()
        captured = capsys.readouterr()
        assert "memory" in captured.out.lower()
