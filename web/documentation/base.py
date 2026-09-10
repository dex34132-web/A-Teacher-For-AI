"""Abstract documentation resolver interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DocQuery:
    """A query for documentation lookup."""

    topic: str
    framework: str = ""
    version: str = ""
    max_results: int = 5
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DocResult:
    """A single documentation result."""

    title: str
    url: str
    content: str
    relevance: float = 0.0
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class DocResolver(ABC):
    """Abstract base class for documentation resolution.

    Provides a unified way to search and retrieve documentation across
    different sources (official docs, MDN, DevDocs, etc.).
    """

    @abstractmethod
    async def resolve(self, query: DocQuery) -> list[DocResult]:
        """Resolve a documentation query.

        Args:
            query: The documentation query with topic and optional filters.

        Returns:
            A list of DocResults sorted by relevance.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the documentation source is reachable."""
        ...
