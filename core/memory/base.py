"""Abstract base class for the MemoryStore component.

A MemoryStore persists and retrieves past experiences, observations,
or derived artefacts. Concrete implementations may use vector databases,
key-value stores, or relational backends.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Generic, TypeVar

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MemoryType(Enum):
    """Category of stored memory."""

    EPISODIC = auto()
    SEMANTIC = auto()
    PROCEDURAL = auto()


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class MemoryEntry:
    """A single record in the memory store."""

    key: str
    content: dict[str, Any]
    memory_type: MemoryType = MemoryType.EPISODIC
    tags: frozenset[str] = frozenset()
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True, slots=True)
class RetrievalQuery:
    """Parameters for querying the memory store."""

    query: str
    k: int = 5
    memory_type: MemoryType | None = None
    tags: frozenset[str] = frozenset()
    metadata_filter: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------

class MemoryStore(ABC, Generic[T]):
    """Interface that every memory backend must implement.

    The type parameter ``T`` represents the storage backend's native
    connection or handle type.
    """

    @abstractmethod
    def store(self, entry: MemoryEntry) -> None:
        """Persist a memory entry.

        Args:
            entry: The entry to store.
        """

    @abstractmethod
    def retrieve(self, query: RetrievalQuery) -> list[MemoryEntry]:
        """Retrieve entries matching *query*.

        Args:
            query: Search parameters.

        Returns:
            A list of matching entries, ordered by relevance.
        """

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete the entry identified by *key*.

        Args:
            key: The unique key of the entry.

        Returns:
            ``True`` if the entry existed and was deleted.
        """

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Return ``True`` if *key* is present in the store."""

    @abstractmethod
    def count(self) -> int:
        """Return the total number of stored entries."""

    @abstractmethod
    def clear(self) -> None:
        """Remove all entries from the store."""
