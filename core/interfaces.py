"""Centralized exports for all core interfaces.

Re-exports every abstract base class and data model so consumers can
do ``from core.interfaces import Learner, Evaluator, ...``.
"""

from __future__ import annotations

from core.adaptation.base import AdaptationEngine
from core.evaluator.base import Evaluator
from core.knowledge.base import KnowledgeBase
from core.learner.base import Learner
from core.memory.base import MemoryStore

__all__: list[str] = [
    "Learner",
    "MemoryStore",
    "Evaluator",
    "AdaptationEngine",
    "KnowledgeBase",
]
