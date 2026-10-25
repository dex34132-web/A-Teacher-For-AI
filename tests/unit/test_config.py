"""Tests for Toolio config."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from toolio.config import ToolioConfig, get_opencode_config_path, get_opencode_node_modules


class TestToolioConfig:
    """Test Toolio configuration."""

    def test_config_paths(self) -> None:
        """Config provides correct default paths."""
        config = ToolioConfig()
        assert config.package_name == "toolio"
        assert config.plugin_dir_name == "toolio"

    def test_get_opencode_config_path_linux(self, tmp_path: Path) -> None:
        """Finds OpenCode config on Linux/macOS."""
        config_dir = tmp_path / ".config" / "opencode"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "opencode.jsonc"
        config_file.write_text('{"plugin": []}', encoding="utf-8")

        with patch("toolio.config.Path.home", return_value=tmp_path):
            result = get_opencode_config_path()

        assert result == config_file

    def test_get_opencode_config_path_windows(self, tmp_path: Path) -> None:
        """Finds OpenCode config on Windows."""
        config_dir = tmp_path / ".config" / "opencode"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "opencode.jsonc"
        config_file.write_text('{"plugin": []}', encoding="utf-8")

        with patch("toolio.config.Path.home", return_value=tmp_path):
            result = get_opencode_config_path()

        assert result == config_file

    def test_get_opencode_config_path_not_found(self, tmp_path: Path) -> None:
        """Returns None when config not found."""
        with patch("toolio.config.Path.home", return_value=tmp_path):
            result = get_opencode_config_path()
        assert result is None

    def test_get_opencode_node_modules(self, tmp_path: Path) -> None:
        """Finds OpenCode node_modules directory."""
        nm_dir = tmp_path / ".config" / "opencode" / "node_modules"
        nm_dir.mkdir(parents=True)

        with patch("toolio.config.Path.home", return_value=tmp_path):
            result = get_opencode_node_modules()

        assert result == nm_dir

    def test_read_opencode_config(self, tmp_path: Path) -> None:
        """Reads OpenCode config JSON."""
        config_dir = tmp_path / ".config" / "opencode"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "opencode.jsonc"
        config_file.write_text('{"plugin": ["test-plugin"]}', encoding="utf-8")

        with patch("toolio.config.Path.home", return_value=tmp_path):
            config = ToolioConfig()
            result = config.read_opencode_config()

        assert result is not None
        assert result["plugin"] == ["test-plugin"]

    def test_is_toolio_installed(self, tmp_path: Path) -> None:
        """Checks if Toolio plugin file exists."""
        plugins_dir = tmp_path / ".config" / "opencode" / "plugins"
        plugins_dir.mkdir(parents=True)
        plugin_file = plugins_dir / "toolio.ts"
        plugin_file.write_text("// test", encoding="utf-8")

        with patch("toolio.config.Path.home", return_value=tmp_path):
            config = ToolioConfig()
            assert config.is_toolio_installed() is True

    def test_is_toolio_not_installed(self, tmp_path: Path) -> None:
        """Returns False when Toolio plugin file does not exist."""
        with patch("toolio.config.Path.home", return_value=tmp_path):
            config = ToolioConfig()
            assert config.is_toolio_installed() is False
