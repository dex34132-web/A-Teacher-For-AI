"""Lerev bridge discovery — 4-tier cascade."""

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
    """Discover the Lerev bridge using a 4-tier cascade.

    Tier 1: LEREV_HOME / EVO_HOME env var
    Tier 2: lerev-bridge on PATH
    Tier 3: python -m lerev.bridge
    Tier 4: Dev fallback ({worktree}/scripts/evo_bridge.py)
    """
    python = _find_python()

    # Tier 1: LEREV_HOME / EVO_HOME env var
    lerev_home = os.environ.get("LEREV_HOME") or os.environ.get("EVO_HOME")
    if lerev_home:
        bridge_path = str(Path(lerev_home) / "lerev" / "bridge.py")
        if _file_exists(bridge_path):
            return BridgeDiscovery(
                python=python or "python3",
                bridge_path=bridge_path,
                tier="LEREV_HOME",
            )

    # Tier 2: lerev-bridge on PATH
    lerev_bridge = shutil.which("lerev-bridge")
    if lerev_bridge:
        return BridgeDiscovery(
            python="",
            bridge_path=lerev_bridge,
            tier="PATH",
        )

    # Tier 3: python -m lerev.bridge (only if python is available)
    if python:
        # We can't easily test this without running python, so we check
        # if the lerev package is importable by checking if lerev/bridge.py exists
        # in a known location. The actual module invocation happens in the plugin.
        try:
            import importlib.util

            spec = importlib.util.find_spec("lerev.bridge")
            if spec is not None and spec.origin is not None:
                return BridgeDiscovery(
                    python=python,
                    bridge_path="-m lerev.bridge",
                    tier="installed_module",
                )
        except (ImportError, ValueError):
            pass

    # Tier 4: Dev fallback
    dev_bridge = str(Path(worktree) / "scripts" / "evo_bridge.py")
    if _file_exists(dev_bridge):
        return BridgeDiscovery(
            python=python or "python3",
            bridge_path=dev_bridge,
            tier="dev_fallback",
        )

    return None
