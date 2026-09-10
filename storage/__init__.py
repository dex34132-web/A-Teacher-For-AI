"""Storage abstraction layer."""

from storage.base import StorageBackend, StorageEntry

__all__ = [
    "StorageBackend",
    "StorageEntry",
]
