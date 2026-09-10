"""Abstract content fetcher interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FetchRequest:
    """Parameters for a content fetch."""

    url: str
    timeout: float = 30.0
    headers: dict[str, str] = field(default_factory=dict)
    extract_text: bool = True


@dataclass
class FetchResponse:
    """Response from a content fetch."""

    url: str
    status_code: int
    content: str
    content_type: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class ContentFetcher(ABC):
    """Abstract base class for HTTP content fetchers.

    Decouples the engine from a specific HTTP library or scraping strategy.
    """

    @abstractmethod
    async def fetch(self, request: FetchRequest) -> FetchResponse:
        """Fetch content from the given URL.

        Args:
            request: The fetch parameters.

        Returns:
            A FetchResponse with the retrieved content.

        Raises:
            FetchError: If the request fails.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the fetcher can reach the network."""
        ...
