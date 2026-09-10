"""Abstract base class for the Learner component.

A Learner processes experiences and produces updated knowledge or
policy adjustments. Concrete implementations may wrap reinforcement-learning
agents, LLM-based learners, or any other learning strategy.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class LearningMode(Enum):
    """Operating mode of a Learner."""

    ONLINE = auto()
    OFFLINE = auto()
    HYBRID = auto()


class LearningStatus(Enum):
    """Current status returned after a learning step."""

    UPDATED = auto()
    UNCHANGED = auto()
    ERROR = auto()


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class LearningInput:
    """An experience to be processed by a Learner."""

    observation: dict[str, Any]
    reward: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True, slots=True)
class LearningOutput:
    """Result produced by a Learner after processing an input."""

    status: LearningStatus
    delta: dict[str, Any] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------

class Learner(ABC):
    """Interface that every learning algorithm must implement."""

    @abstractmethod
    def learn(self, inp: LearningInput) -> LearningOutput:
        """Process a single experience and return the learning result.

        Args:
            inp: The experience to learn from.

        Returns:
            A ``LearningOutput`` describing what changed.
        """

    @abstractmethod
    def reset(self) -> None:
        """Reset the learner to its initial state."""

    @property
    @abstractmethod
    def mode(self) -> LearningMode:
        """Return the current operating mode of the learner."""

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """Return a serialisable snapshot of the learner's parameters."""
