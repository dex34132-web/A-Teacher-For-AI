"""Lerev configuration — paths and OpenCode config discovery."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class LerevConfig:
    """Lerev configuration and path management."""

    package_name: str = "lerev"
    plugin_dir_name: str = "lerev"
    memory_dir: str = ".lerev"
    legacy_memory_dir: str = ".evo"

    def __init__(self) -> None:
        self._home = Path.home()

    def opencode_config_dir(self) -> Path:
        """Return the OpenCode global config directory."""
        return self._home / ".config" / "opencode"

    def opencode_config_file(self) -> Path:
        """Return the OpenCode global config file path."""
        return self.opencode_config_dir() / "opencode.jsonc"

    def opencode_plugins_dir(self) -> Path:
        """Return the OpenCode auto-discovery plugins directory."""
        return self.opencode_config_dir() / "plugins"

    def lerev_plugin_file(self) -> Path:
        """Return the path to the Lerev TypeScript plugin file."""
        return self.opencode_plugins_dir() / f"{self.plugin_dir_name}.ts"

    def read_opencode_config(self) -> dict[str, Any] | None:
        """Read the OpenCode global config file."""
        config_file = self.opencode_config_file()
        if not config_file.is_file():
            return None
        try:
            return json.loads(config_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def write_opencode_config(self, config: dict[str, Any]) -> None:
        """Write the OpenCode global config file."""
        config_file = self.opencode_config_file()
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(
            json.dumps(config, indent=2) + "\n",
            encoding="utf-8",
        )

    def is_lerev_installed(self) -> bool:
        """Check if Lerev plugin file exists in the auto-discovery directory."""
        return self.lerev_plugin_file().is_file()


def get_opencode_config_path() -> Path | None:
    """Find the OpenCode global config file."""
    home = Path.home()
    candidates = [
        home / ".config" / "opencode" / "opencode.jsonc",
        home / ".config" / "opencode" / "opencode.json",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def get_opencode_node_modules() -> Path | None:
    """Find the OpenCode global node_modules directory."""
    nm_dir = Path.home() / ".config" / "opencode" / "node_modules"
    return nm_dir if nm_dir.is_dir() else None
