"""Lerev CLI - command-line interface for Lerev."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from lerev import __version__
from lerev.config import LerevConfig
from lerev.discovery import discover_bridge
from lerev.plugin_source import TS_PLUGIN_SOURCE


def _cmd_version(args: argparse.Namespace) -> None:
    """Print Lerev version."""
    print(f"lerev {__version__}")


def _cmd_status(args: argparse.Namespace) -> None:
    """Print Lerev status."""
    config = LerevConfig()
    bridge = discover_bridge(".")

    print("Lerev")
    print("----------------")
    print(f"Version: {__version__}")

    # Plugin status
    if config.is_lerev_registered():
        print("Plugin: installed")
    else:
        print("Plugin: not installed")

    # OpenCode status
    config_path = config.opencode_config_file()
    if config_path and config_path.exists():
        print("OpenCode: detected")
    else:
        print("OpenCode: not found")

    # Bridge status
    if bridge:
        print(f"Bridge: healthy (tier: {bridge.tier})")
    else:
        print("Bridge: not found")

    # Memory status
    memory_dir = Path(".lerev") / "memory"
    legacy_dir = Path(".evo") / "memory"
    if memory_dir.exists() or legacy_dir.exists():
        print("Memory: available")
    else:
        print("Memory: no data")


def _cmd_install(args: argparse.Namespace) -> None:
    """Install Lerev globally for OpenCode."""
    config = LerevConfig()

    print("Lerev Installer")
    print("----------------------------")

    print(f"Python: {sys.version_info.major}.{sys.version_info.minor} OK")

    # Check OpenCode config
    config_file = config.opencode_config_file()
    if config_file is None:
        print("WARNING: OpenCode config not found")
        print(f"  Expected at: {config.opencode_config_file()}")
        print("  Lerev will work in development mode only.")
        return

    print(f"OpenCode config: {config_file}")

    # Check if already registered
    if config.is_lerev_registered():
        print("Lerev is already registered. Nothing to do.")
        return

    # Install plugin
    plugin_dir = config.lerev_plugin_dir()
    plugin_dir.mkdir(parents=True, exist_ok=True)

    # Write TypeScript plugin
    plugin_file = plugin_dir / "lerev.ts"
    plugin_file.write_text(TS_PLUGIN_SOURCE, encoding="utf-8")
    print(f"Plugin installed: {plugin_file}")

    # Write package.json for the plugin
    pkg_json = plugin_dir / "package.json"
    pkg_json.write_text(
        json.dumps({"dependencies": {"@opencode-ai/plugin": "1.18.30"}}, indent=2),
        encoding="utf-8",
    )

    # Register in OpenCode config
    opencode_config = config.read_opencode_config()
    if opencode_config is None:
        opencode_config = {"plugin": []}

    plugins = opencode_config.get("plugin", [])
    entry = config.plugin_entry_path()
    if entry not in plugins:
        plugins.append(entry)
        opencode_config["plugin"] = plugins
        config.write_opencode_config(opencode_config)
        print(f"Registered in OpenCode config: {entry}")

    # Verify bridge
    bridge = discover_bridge(".")
    if bridge:
        print(f"Bridge: {bridge.tier} OK")
    else:
        print("WARNING: Bridge not found. Run `lerev doctor` for diagnostics.")

    print("")
    print("Installation complete!")
    print("Restart OpenCode to use Lerev.")


def _cmd_doctor(args: argparse.Namespace) -> None:
    """Run Lerev diagnostics."""
    config = LerevConfig()
    bridge = discover_bridge(".")

    print("Lerev Doctor")
    print("----------------------------")

    checks = []

    # Lerev runtime
    try:
        from core.routing.v26.memory_manager import MemoryManager  # noqa: F401

        print("Lerev runtime          PASS")
        checks.append(True)
    except Exception:
        print("Lerev runtime          FAIL - core.routing.v26 not importable")
        checks.append(False)

    # Python
    print(f"Python/runtime         {sys.version_info.major}.{sys.version_info.minor} OK")
    checks.append(True)

    # Bridge
    if bridge:
        print(f"Bridge                 PASS (tier: {bridge.tier})")
        checks.append(True)
    else:
        print("Bridge                 FAIL - no bridge found")
        checks.append(False)

    # OpenCode
    config_file = config.opencode_config_file()
    if config_file and config_file.exists():
        print("OpenCode               PASS")
        checks.append(True)
    else:
        print("OpenCode               FAIL - config not found")
        checks.append(False)

    # Plugin registration
    if config.is_lerev_registered():
        print("Plugin registration   PASS")
        checks.append(True)
    else:
        print("Plugin registration   FAIL - not registered")
        checks.append(False)

    # Plugin resolution
    plugin_dir = config.lerev_plugin_dir()
    if plugin_dir.exists():
        print("Plugin resolution     PASS")
        checks.append(True)
    else:
        print("Plugin resolution     FAIL - plugin directory not found")
        checks.append(False)

    # Memory storage
    memory_dir = Path(".lerev") / "memory"
    legacy_dir = Path(".evo") / "memory"
    if memory_dir.exists() or legacy_dir.exists():
        print("Memory storage         PASS")
        checks.append(True)
    else:
        print("Memory storage         SKIP - no memory data yet")
        checks.append(True)

    print("")
    if all(checks):
        print("Result: READY")
    else:
        print("Result: NOT READY - fix issues above")


def _cmd_uninstall(args: argparse.Namespace) -> None:
    """Uninstall Lerev from OpenCode."""
    config = LerevConfig()

    print("Lerev Uninstaller")
    print("----------------------------")

    # Remove plugin directory
    plugin_dir = config.lerev_plugin_dir()
    if plugin_dir.exists():
        import shutil

        shutil.rmtree(plugin_dir)
        print(f"Removed plugin: {plugin_dir}")

    # Remove from OpenCode config
    config_file = config.opencode_config_file()
    if config_file and config_file.exists():
        opencode_config = config.read_opencode_config()
        if opencode_config:
            plugins = opencode_config.get("plugin", [])
            entry = config.plugin_entry_path()
            new_plugins = [p for p in plugins if entry not in str(p)]
            if len(new_plugins) < len(plugins):
                opencode_config["plugin"] = new_plugins
                config.write_opencode_config(opencode_config)
                print(f"Removed from OpenCode config: {entry}")
            else:
                print("Lerev not found in OpenCode config.")

    print("")
    print("Uninstall complete.")
    print("Note: .lerev/memory/ was NOT removed (use explicit action to delete).")
    print("Restart OpenCode to apply changes.")


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="lerev",
        description="Lerev - Universal agent learning and memory system",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    subparsers.add_parser("version", help="Print Lerev version")
    subparsers.add_parser("status", help="Show Lerev status")
    subparsers.add_parser("install", help="Install Lerev globally for OpenCode")
    subparsers.add_parser("doctor", help="Run Lerev diagnostics")
    subparsers.add_parser("uninstall", help="Uninstall Lerev from OpenCode")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    commands = {
        "version": _cmd_version,
        "status": _cmd_status,
        "install": _cmd_install,
        "doctor": _cmd_doctor,
        "uninstall": _cmd_uninstall,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        cmd_func(args)
    else:
        parser.print_help()
        sys.exit(1)
