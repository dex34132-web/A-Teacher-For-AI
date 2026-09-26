"""Legacy shim — ``lerev.config`` (alias of teacher.config)."""

from __future__ import annotations

from teacher.config import (
    LerevConfig,
    TeacherConfig,
    get_opencode_config_path,
    get_opencode_node_modules,
    resolve_memory_dir,
)

__all__ = [
    "LerevConfig",
    "TeacherConfig",
    "get_opencode_config_path",
    "get_opencode_node_modules",
    "resolve_memory_dir",
]
