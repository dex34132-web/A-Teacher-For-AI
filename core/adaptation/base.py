"""Abstract base class for the AdaptationEngine component.

An AdaptationEngine modifies learner behaviour based on evaluation
feedback. It bridges evaluation results and parameter updates,
enabling curriculum adjustments, hyperparameter tuning, or
meta-learning strategies.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AdaptationStrategy(Enum):
    """High-level adaptation strategy."""

    GRADIENT = auto()
    EVOLUTIONARY = auto()
    META_LEARNING = auto()
    HEURISTIC = auto()


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class AdaptationSignal:
    """Feedback signal fed into an AdaptationEngine."""

    metric_name: str
    current_value: float
    target_value: float | None = None
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AdaptationAction:
    """An action that the AdaptationEngine recommends."""

    parameter: str
    old_value: Any
    new_value: Any
    reason: str = ""


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------

class AdaptationEngine(ABC):
    """Interface that every adaptation strategy must implement."""

    @abstractmethod
    def propose(self, signals: list[AdaptationSignal]) -> list[AdaptationAction]:
        """Analyse signals and propose parameter changes.

        Args:
            signals: Current feedback signals.

        Returns:
            A list of recommended actions.
        """

    @abstractmethod
    def apply(self, actions: list[AdaptationAction]) -> dict[str, Any]:
        """Apply a set of actions and return the outcome.

        Args:
            actions: Actions to execute.

        Returns:
            A dict describing what was actually applied.
        """

    @property
    @abstractmethod
    def strategy(self) -> AdaptationStrategy:
        """Return the underlying adaptation strategy."""
