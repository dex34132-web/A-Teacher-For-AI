"""Tests for Lerev config."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from lerev.config import LerevConfig, get_opencode_config_path, get_opencode_node_modules


class TestLerevConfig:
    """Test Lerev configuration."""

    def test_config_paths(self) -> None:
        """Config provides correct default paths."""
        config = LerevConfig()
        assert config.package_name == "lerev"
        assert config.plugin_dir_name == "lerev"

    def test_get_opencode_config_path_linux(self, tmp_path: Path) -> None:
        """Finds OpenCode config on Linux/macOS."""
        config_dir = tmp_path / ".config" / "opencode"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "opencode.jsonc"
        config_file.write_text('{"plugin": []}', encoding="utf-8")

        with patch("lerev.config.Path.home", return_value=tmp_path):
            result = get_opencode_config_path()

        assert result == config_file

    def test_get_opencode_config_path_windows(self, tmp_path: Path) -> None:
        """Finds OpenCode config on Windows."""
        config_dir = tmp_path / ".config" / "opencode"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "opencode.jsonc"
        config_file.write_text('{"plugin": []}', encoding="utf-8")

        with patch("lerev.config.Path.home", return_value=tmp_path):
            result = get_opencode_config_path()

        assert result == config_file

    def test_get_opencode_config_path_not_found(self, tmp_path: Path) -> None:
        """Returns None when config not found."""
        with patch("lerev.config.Path.home", return_value=tmp_path):
            result = get_opencode_config_path()
        assert result is None

    def test_get_opencode_node_modules(self, tmp_path: Path) -> None:
        """Finds OpenCode node_modules directory."""
        nm_dir = tmp_path / ".config" / "opencode" / "node_modules"
        nm_dir.mkdir(parents=True)

        with patch("lerev.config.Path.home", return_value=tmp_path):
            result = get_opencode_node_modules()

        assert result == nm_dir

    def test_read_opencode_config(self, tmp_path: Path) -> None:
        """Reads OpenCode config JSON."""
        config_dir = tmp_path / ".config" / "opencode"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "opencode.jsonc"
        config_file.write_text('{"plugin": ["test-plugin"]}', encoding="utf-8")

        with patch("lerev.config.Path.home", return_value=tmp_path):
            config = LerevConfig()
            result = config.read_opencode_config()

        assert result is not None
        assert result["plugin"] == ["test-plugin"]

    def test_is_lerev_registered(self, tmp_path: Path) -> None:
        """Checks if Lerev is already registered."""
        config_dir = tmp_path / ".config" / "opencode"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "opencode.jsonc"
        config_file.write_text(
            json.dumps({"plugin": ["~/.config/opencode/node_modules/lerev"]}),
            encoding="utf-8",
        )

        with patch("lerev.config.Path.home", return_value=tmp_path):
            config = LerevConfig()
            assert config.is_lerev_registered() is True

    def test_is_lerev_not_registered(self, tmp_path: Path) -> None:
        """Returns False when Lerev not registered."""
        config_dir = tmp_path / ".config" / "opencode"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "opencode.jsonc"
        config_file.write_text('{"plugin": ["other-plugin"]}', encoding="utf-8")

        with patch("lerev.config.Path.home", return_value=tmp_path):
            config = LerevConfig()
            assert config.is_lerev_registered() is False
