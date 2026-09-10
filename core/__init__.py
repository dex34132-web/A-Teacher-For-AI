"""Core interfaces for the AI Learning Engine.

This package defines the abstract base classes and type definitions
for the learning engine system. It is implementation-agnostic and
does not depend on any specific harness (OpenCode, Claude, etc.).
"""

from __future__ import annotations

__version__: str = "0.1.0"
__all__: list[str] = [
    "Learner",
    "MemoryStore",
    "Evaluator",
    "AdaptationEngine",
    "KnowledgeBase",
]
