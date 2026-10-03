"""School bridge discovery — 4-tier cascade."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BridgeDiscovery:
    """Result of bridge discovery."""

    python: str
    bridge_path: str
    tier: str


def _find_python() -> str | None:
    """Find a usable Python interpreter."""
    for cmd in ("python3", "python"):
        if shutil.which(cmd):
            return cmd
    return None


def _file_exists(path: str) -> bool:
    """Check if a file exists."""
    return Path(path).is_file()


def discover_bridge(worktree: str) -> BridgeDiscovery | None:
    """Discover the School bridge using a 4-tier cascade.

    Tier 1: SCHOOL_HOME env var
    Tier 2: school-bridge on PATH
    Tier 3: python -m school.bridge
    Tier 4: Dev fallback ({worktree}/scripts/school_bridge.py)
    """
    python = _find_python()

    # Tier 1: env-configured install root
    home = os.environ.get("SCHOOL_HOME")
    if home:
        bridge_path = str(Path(home) / "school" / "bridge.py")
        if _file_exists(bridge_path):
            return BridgeDiscovery(
                python=python or "python3",
                bridge_path=bridge_path,
                tier="SCHOOL_HOME",
            )

    # Tier 2: bridge launcher on PATH
    bridge_cmd = shutil.which("school-bridge")
    if bridge_cmd:
        return BridgeDiscovery(python="", bridge_path=bridge_cmd, tier="PATH")

    # Tier 3: installed module (only if python is available). The actual
    # module invocation happens in the plugin; we probe importability here.
    if python:
        try:
            import importlib.util

            spec = importlib.util.find_spec("school.bridge")
            if spec is not None and spec.origin is not None:
                return BridgeDiscovery(
                    python=python,
                    bridge_path="-m school.bridge",
                    tier="installed_module",
                )
        except (ImportError, ValueError):
            pass

    # Tier 4: Dev fallback
    dev_bridge = str(Path(worktree) / "scripts" / "school_bridge.py")
    if _file_exists(dev_bridge):
        return BridgeDiscovery(
            python=python or "python3",
            bridge_path=dev_bridge,
            tier="dev_fallback",
        )

    return None
