"""Harness adapter registry.

Provides the central registry for discovering and instantiating
harness adapters that connect the learning engine to various
AI coding assistants.
"""

from adapters.base import HarnessAdapter, AdapterConfig, AdapterCapability

__all__ = [
    "HarnessAdapter",
    "AdapterConfig",
    "AdapterCapability",
]
