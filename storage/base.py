"""Abstract storage backend interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class StorageEntry:
    """A single stored item."""

    key: str
    value: Any
    namespace: str = "default"
    metadata: dict[str, Any] = field(default_factory=dict)


class StorageBackend(ABC):
    """Abstract base class for persistent storage.

    Provides a key-value abstraction so the engine can swap between
    local filesystem, SQLite, Redis, or any other backend without
    changing the rest of the codebase.
    """

    @abstractmethod
    async def get(self, key: str, namespace: str = "default") -> StorageEntry | None:
        """Retrieve an entry by key.

        Args:
            key: The storage key.
            namespace: The namespace to look in.

        Returns:
            The StorageEntry if found, None otherwise.
        """
        ...

    @abstractmethod
    async def put(self, entry: StorageEntry) -> None:
        """Store an entry.

        Args:
            entry: The StorageEntry to store.
        """
        ...

    @abstractmethod
    async def delete(self, key: str, namespace: str = "default") -> bool:
        """Delete an entry by key.

        Args:
            key: The storage key.
            namespace: The namespace to delete from.

        Returns:
            True if the entry was deleted, False if not found.
        """
        ...

    @abstractmethod
    async def list_keys(self, namespace: str = "default", prefix: str = "") -> list[str]:
        """List all keys in a namespace, optionally filtered by prefix.

        Args:
            namespace: The namespace to list.
            prefix: Optional prefix filter.

        Returns:
            A list of matching keys.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the storage backend is operational."""
        ...
