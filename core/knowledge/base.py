"""Abstract base class for the KnowledgeBase component.

A KnowledgeBase maintains structured knowledge (rules, facts,
ontologies) that can be queried and updated. Concrete implementations
may use graph databases, semantic stores, or simple dictionaries.
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

class KnowledgeType(Enum):
    """Type of knowledge entry."""

    FACT = auto()
    RULE = auto()
    HYPOTHESIS = auto()
    METADATA = auto()


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class KnowledgeEntry:
    """A single piece of knowledge."""

    subject: str
    predicate: str
    obj: Any
    knowledge_type: KnowledgeType = KnowledgeType.FACT
    confidence: float = 1.0
    source: str = ""
    created_at: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True, slots=True)
class KnowledgeQuery:
    """Parameters for querying the knowledge base."""

    subject: str | None = None
    predicate: str | None = None
    knowledge_type: KnowledgeType | None = None
    min_confidence: float = 0.0
    limit: int = 100


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------

class KnowledgeBase(ABC):
    """Interface that every knowledge store must implement."""

    @abstractmethod
    def add(self, entry: KnowledgeEntry) -> None:
        """Insert a new knowledge entry.

        Args:
            entry: The knowledge to add.
        """

    @abstractmethod
    def query(self, query: KnowledgeQuery) -> list[KnowledgeEntry]:
        """Retrieve entries matching *query*.

        Args:
            query: Search parameters.

        Returns:
            A list of matching entries.
        """

    @abstractmethod
    def update(self, entry: KnowledgeEntry) -> bool:
        """Update an existing entry (matched by subject + predicate).

        Args:
            entry: Updated knowledge.

        Returns:
            ``True`` if the entry existed and was updated.
        """

    @abstractmethod
    def remove(self, subject: str, predicate: str) -> bool:
        """Remove entries matching the given subject/predicate pair.

        Returns:
            ``True`` if at least one entry was removed.
        """

    @abstractmethod
    def count(self) -> int:
        """Return the total number of knowledge entries."""

    @abstractmethod
    def clear(self) -> None:
        """Remove all entries from the knowledge base."""
