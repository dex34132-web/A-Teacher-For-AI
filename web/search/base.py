"""Abstract search provider interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SearchQuery:
    """A structured search query."""

    text: str
    max_results: int = 10
    language: str = "en"
    domain_filter: list[str] = field(default_factory=list)


@dataclass
class SearchResult:
    """A single search result."""

    title: str
    url: str
    snippet: str
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class SearchProvider(ABC):
    """Abstract base class for web search providers.

    Implementations wrap a specific search API (e.g. Bing, Google, Tavily)
    behind this common interface so the rest of the engine stays provider-agnostic.
    """

    @abstractmethod
    async def search(self, query: SearchQuery) -> list[SearchResult]:
        """Execute a search and return ranked results.

        Args:
            query: The search query with optional filters.

        Returns:
            A list of search results sorted by relevance.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the underlying provider is reachable."""
        ...
