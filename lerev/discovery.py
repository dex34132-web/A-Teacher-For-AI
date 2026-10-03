"""Legacy shim — ``lerev.discovery`` (alias of school.discovery)."""

from __future__ import annotations

from school.discovery import (
    BridgeDiscovery,
    _find_python,
    discover_bridge,
)

__all__ = ["BridgeDiscovery", "_find_python", "discover_bridge"]
