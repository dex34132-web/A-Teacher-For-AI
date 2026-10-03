"""Legacy shim — ``lerev.plugin_source`` (alias of school.plugin_source)."""

from __future__ import annotations

from school.plugin_source import _TS_PLUGIN_TEMPLATE, TS_PLUGIN_SOURCE

__all__ = ["TS_PLUGIN_SOURCE", "_TS_PLUGIN_TEMPLATE"]
