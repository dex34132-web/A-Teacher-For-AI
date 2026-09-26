"""Teacher bridge discovery — 4-tier cascade (with legacy aliases)."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

# Legacy aliases retained for pre-rename installations. These are
# deliberately supported fallbacks, not the primary identity.
_LEGACY_ENV_VARS = ("LEREV_HOME", "EVO_HOME")
_LEGACY_BRIDGE_COMMANDS = ("lerev-bridge",)
_LEGACY_MODULES = ("lerev.bridge",)
_LEGACY_DEV_BRIDGE = "lerev_bridge.py"


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
    """Discover the Teacher bridge using a 4-tier cascade.

    Tier 1: TEACHER_HOME env var (legacy: LEREV_HOME / EVO_HOME)
    Tier 2: teacher-bridge on PATH (legacy: lerev-bridge)
    Tier 3: python -m teacher.bridge (legacy: lerev.bridge)
    Tier 4: Dev fallback ({worktree}/scripts/teacher_bridge.py)
    """
    python = _find_python()

    # Tier 1: env-configured install root (legacy aliases still honoured)
    env_vars = ("TEACHER_HOME", *_LEGACY_ENV_VARS)
    env_home = next((v for v in env_vars if os.environ.get(v)), None)
    if env_home is not None:
        home = os.environ[env_home]
        for pkg in ("teacher", "lerev"):
            bridge_path = str(Path(home) / pkg / "bridge.py")
            if _file_exists(bridge_path):
                return BridgeDiscovery(
                    python=python or "python3",
                    bridge_path=bridge_path,
                    tier="TEACHER_HOME",
                )

    # Tier 2: bridge launcher on PATH (legacy alias still honoured)
    for command in ("teacher-bridge", *_LEGACY_BRIDGE_COMMANDS):
        bridge_cmd = shutil.which(command)
        if bridge_cmd:
            return BridgeDiscovery(
                python="",
                bridge_path=bridge_cmd,
                tier="PATH",
            )

    # Tier 3: installed module (only if python is available). The actual
    # module invocation happens in the plugin; we probe importability here.
    if python:
        try:
            import importlib.util

            for module in ("teacher.bridge", *_LEGACY_MODULES):
                spec = importlib.util.find_spec(module)
                if spec is not None and spec.origin is not None:
                    return BridgeDiscovery(
                        python=python,
                        bridge_path=f"-m {module}",
                        tier="installed_module",
                    )
        except (ImportError, ValueError):
            pass

    # Tier 4: Dev fallback (canonical script, then legacy name)
    for script in ("teacher_bridge.py", _LEGACY_DEV_BRIDGE):
        dev_bridge = str(Path(worktree) / "scripts" / script)
        if _file_exists(dev_bridge):
            return BridgeDiscovery(
                python=python or "python3",
                bridge_path=dev_bridge,
                tier="dev_fallback",
            )

    return None
