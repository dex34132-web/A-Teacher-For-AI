"""Legacy shim — ``lerev.config`` (alias of school.config)."""

from __future__ import annotations

from school.config import (
    LerevConfig,
    SchoolConfig,
    get_opencode_config_path,
    get_opencode_node_modules,
    resolve_memory_dir,
)

__all__ = [
    "LerevConfig",
    "SchoolConfig",
    "get_opencode_config_path",
    "get_opencode_node_modules",
    "resolve_memory_dir",
]
