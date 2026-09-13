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

    print("LEREV DOCTOR")
    print("=" * 40)
    print("")

    results: list[tuple[str, bool, str]] = []

    # 1. Python version
    py_ok = sys.version_info >= (3, 11)
    py_msg = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if not py_ok:
        py_msg += " (requires 3.11+)"
    results.append(("Python runtime", py_ok, py_msg))

    # 2. Lerev package importable
    try:
        from lerev import __version__ as lerev_ver  # noqa: F401
        results.append(("LEREV package", True, f"v{lerev_ver}"))
    except Exception as exc:
        results.append(("LEREV package", False, str(exc)))

    # 3. V2.6 memory system
    try:
        from core.routing.v26.memory_manager import MemoryManager  # noqa: F401
        from core.routing.v26.persistence import ScopeIsolatedStorage  # noqa: F401
        from core.routing.v26.security import V26SecurityPolicy  # noqa: F401
        results.append(("V2.6 memory system", True, "available"))
    except Exception as exc:
        results.append(("V2.6 memory system", False, str(exc)))

    # 4. V2.5 routing
    try:
        from core.routing.integration import LerevIntegrationBridge  # noqa: F401
        results.append(("V2.5 routing", True, "available"))
    except Exception as exc:
        results.append(("V2.5 routing", False, str(exc)))

    # 5. Bridge discovery
    if bridge:
        results.append(("Bridge", True, f"tier={bridge.tier}"))
    else:
        results.append(("Bridge", False, "no bridge found"))

    # 6. OpenCode config
    config_file = config.opencode_config_file()
    opencode_found = config_file is not None and config_file.exists()
    results.append(("OpenCode config", opencode_found,
                     str(config_file) if opencode_found else "not found"))

    # 7. Plugin registration
    registered = config.is_lerev_registered()
    results.append(("Plugin registered", registered,
                     "yes" if registered else "not in opencode.jsonc"))

    # 8. Plugin file
    plugin_dir = config.lerev_plugin_dir()
    plugin_exists = plugin_dir.exists()
    results.append(("Plugin file", plugin_exists,
                     str(plugin_dir) if plugin_exists else "not found"))

    # 9. Memory directory
    memory_dir = Path(".lerev") / "memory"
    legacy_dir = Path(".evo") / "memory"
    mem_exists = memory_dir.exists() or legacy_dir.exists()
    results.append(("Project memory", True,
                     "exists" if mem_exists else "no data yet (will be created)"))

    # Print results
    for name, ok, detail in results:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}: {detail}")

    print("")
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    if passed == total:
        print("RESULT: LEREV IS READY")
    else:
        failed = total - passed
        print(f"RESULT: {failed} issue(s) found — fix them above")
    print("")


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
