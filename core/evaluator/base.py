"""Abstract base class for the Evaluator component.

An Evaluator assesses the quality of learner outputs, policies, or
behaviours against one or more metrics. Concrete implementations may
wrap statistical tests, LLM-as-judge scoring, or domain-specific
benchmarks.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class EvalScale(Enum):
    """Scale used by an evaluation metric."""

    BINARY = auto()
    CONTINUOUS = auto()
    ORDINAL = auto()


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class EvalMetric:
    """Definition of a single evaluation metric."""

    name: str
    scale: EvalScale = EvalScale.CONTINUOUS
    range_min: float = 0.0
    range_max: float = 1.0
    higher_is_better: bool = True


@dataclass(frozen=True, slots=True)
class EvalResult:
    """Outcome of evaluating a single sample against a set of metrics."""

    scores: dict[str, float]
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EvalReport:
    """Aggregated results across many samples."""

    results: list[EvalResult]
    summary: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------

class Evaluator(ABC):
    """Interface that every evaluator must implement."""

    @abstractmethod
    def evaluate(self, sample: dict[str, Any]) -> EvalResult:
        """Evaluate a single sample.

        Args:
            sample: The data to evaluate.

        Returns:
            An ``EvalResult`` with per-metric scores.
        """

    @abstractmethod
    def aggregate(self, results: list[EvalResult]) -> EvalReport:
        """Aggregate multiple evaluation results.

        Args:
            results: Individual results to aggregate.

        Returns:
            A summary ``EvalReport``.
        """

    @property
    @abstractmethod
    def metrics(self) -> list[EvalMetric]:
        """Return the list of metrics this evaluator uses."""
