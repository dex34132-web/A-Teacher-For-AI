"""Abstract source evaluator interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SourceRating(Enum):
    """Rating for a source's reliability."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


@dataclass
class SourceAssessment:
    """Evaluation of a web source's quality and relevance."""

    url: str
    rating: SourceRating
    confidence: float = 0.0
    reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class SourceEvaluator(ABC):
    """Abstract base class for source quality evaluation.

    Assesses the reliability, authority, and relevance of web sources
    to help the engine decide which information to trust.
    """

    @abstractmethod
    async def evaluate(self, url: str, content: str = "") -> SourceAssessment:
        """Evaluate the quality of a source.

        Args:
            url: The URL to evaluate.
            content: Optional page content for deeper analysis.

        Returns:
            A SourceAssessment with rating and confidence.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the evaluator is operational."""
        ...
