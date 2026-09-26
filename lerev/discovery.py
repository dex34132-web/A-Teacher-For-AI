"""Legacy shim — ``lerev.discovery`` (alias of teacher.discovery)."""

from __future__ import annotations

from teacher.discovery import (
    BridgeDiscovery,
    _find_python,
    discover_bridge,
)

__all__ = ["BridgeDiscovery", "_find_python", "discover_bridge"]
