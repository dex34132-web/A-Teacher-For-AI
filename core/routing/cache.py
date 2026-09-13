"""Caching and batching for Lerev V2.5 routing.

Supports routing-result caching, repeated-request detection,
batching, and deferred processing.

Caches must respect scope and invalidation.
Never allow caching to violate correctness or isolation.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from core.routing.decision import RoutingDecision
from core.routing.information import InformationPacket, SensitivityLevel


@dataclass(frozen=True, slots=True)
class CacheEntry:
    """A cached routing decision.

    Attributes:
        cache_key: The cache key.
        decision: The cached routing decision.
        timestamp: When this entry was created.
        hit_count: Number of times this cache was hit.
        scope: The scope this cache entry belongs to.
    """

    cache_key: str
    decision: RoutingDecision
    timestamp: float
    hit_count: int = 0
    scope: str = ""

    def with_hit(self) -> CacheEntry:
        """Return a copy with incremented hit count."""
        return CacheEntry(
            cache_key=self.cache_key,
            decision=self.decision,
            timestamp=self.timestamp,
            hit_count=self.hit_count + 1,
            scope=self.scope,
        )


def compute_cache_key(packet: InformationPacket) -> str:
    """Compute a deterministic cache key for a packet.

    The key is based on content, type, source, and scope.
    Sensitive packets are never cached.

    Args:
        packet: The information packet.

    Returns:
        Cache key string.
    """
    # Never cache sensitive/secret content
    if packet.sensitivity in {SensitivityLevel.SENSITIVE, SensitivityLevel.SECRET}:
        return ""

    # Build key from deterministic fields
    key_parts = [
        packet.content,
        packet.information_type.name,
        packet.source.name,
        packet.scope,
        str(packet.priority),
    ]
    raw = "|".join(key_parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


class RoutingCache:
    """Bounded routing result cache with scope isolation.

    No global mutable state — cache is per-instance.
    """

    def __init__(self, max_entries: int = 10_000, default_ttl: float = 300.0) -> None:
        """Initialize the routing cache.

        Args:
            max_entries: Maximum cache entries.
            default_ttl: Default time-to-live in seconds.
        """
        self._max_entries = max_entries
        self._default_ttl = default_ttl
        self._entries: dict[str, CacheEntry] = {}
        self._by_scope: dict[str, list[str]] = defaultdict(list)
        self._hits = 0
        self._misses = 0

    def get(self, packet: InformationPacket) -> RoutingDecision | None:
        """Look up a cached routing decision.

        Args:
            packet: The information packet.

        Returns:
            Cached decision if found, None otherwise.
        """
        key = compute_cache_key(packet)
        if not key:
            self._misses += 1
            return None

        entry = self._entries.get(key)
        if entry is None:
            self._misses += 1
            return None

        # Check scope isolation
        if entry.scope and entry.scope != packet.scope:
            self._misses += 1
            return None

        self._hits += 1
        self._entries[key] = entry.with_hit()
        return entry.decision

    def put(
        self,
        packet: InformationPacket,
        decision: RoutingDecision,
        ttl: float | None = None,
    ) -> None:
        """Cache a routing decision.

        Args:
            packet: The information packet.
            decision: The routing decision to cache.
            ttl: Time-to-live (unused in V2.5, reserved for future).
        """
        key = compute_cache_key(packet)
        if not key:
            return  # Never cache sensitive content

        # Evict if at capacity
        if len(self._entries) >= self._max_entries:
            self._evict_oldest()

        entry = CacheEntry(
            cache_key=key,
            decision=decision,
            timestamp=0.0,  # Caller should set timestamp if needed
            scope=packet.scope,
        )
        self._entries[key] = entry
        self._by_scope[packet.scope].append(key)

    def invalidate(self, scope: str | None = None) -> int:
        """Invalidate cache entries.

        Args:
            scope: If provided, invalidate only this scope. Otherwise all.

        Returns:
            Number of entries invalidated.
        """
        if scope is None:
            count = len(self._entries)
            self._entries.clear()
            self._by_scope.clear()
            return count

        keys = self._by_scope.pop(scope, [])
        for key in keys:
            self._entries.pop(key, None)
        return len(keys)

    def has(self, packet: InformationPacket) -> bool:
        """Check if a packet has a cached decision (no side effects)."""
        key = compute_cache_key(packet)
        if not key:
            return False
        entry = self._entries.get(key)
        if entry is None:
            return False
        return not (entry.scope and entry.scope != packet.scope)

    @property
    def hit_rate(self) -> float:
        """Cache hit rate."""
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return self._hits / total

    @property
    def size(self) -> int:
        """Current cache size."""
        return len(self._entries)

    def _evict_oldest(self) -> None:
        """Evict the oldest entry."""
        if not self._entries:
            return
        oldest_key = next(iter(self._entries))
        entry = self._entries.pop(oldest_key)
        if entry.scope in self._by_scope:
            self._by_scope[entry.scope] = [
                k for k in self._by_scope[entry.scope] if k != oldest_key
            ]

    def clear(self) -> None:
        """Clear the entire cache."""
        self._entries.clear()
        self._by_scope.clear()
        self._hits = 0
        self._misses = 0

    def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": self.size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self.hit_rate,
            "max_entries": self._max_entries,
        }


# ---------------------------------------------------------------------------
# Batching
# ---------------------------------------------------------------------------


@dataclass
class BatchEntry:
    """An entry in a routing batch.

    Attributes:
        packet: The information packet.
        destinations: Requested destinations.
        added_at: When this entry was added to the batch.
    """

    packet: InformationPacket
    destinations: tuple[str, ...] = ()
    added_at: float = 0.0


class RoutingBatch:
    """Accumulates packets for batch processing.

    No global mutable state — batch is per-instance.
    """

    def __init__(self, max_batch_size: int = 10) -> None:
        """Initialize the batch.

        Args:
            max_batch_size: Maximum batch size before auto-flush.
        """
        self._max_batch_size = max_batch_size
        self._entries: list[BatchEntry] = []

    def add(
        self,
        packet: InformationPacket,
        destinations: tuple[str, ...] = (),
        timestamp: float = 0.0,
    ) -> bool:
        """Add a packet to the batch.

        Args:
            packet: The information packet.
            destinations: Requested destinations.
            timestamp: When the packet was added.

        Returns:
            True if added, False if batch is full.
        """
        if len(self._entries) >= self._max_batch_size:
            return False

        self._entries.append(BatchEntry(
            packet=packet,
            destinations=destinations,
            added_at=timestamp,
        ))
        return True

    def should_flush(self, current_time: float, cooldown: float = 5.0) -> bool:
        """Check if the batch should be flushed.

        Args:
            current_time: Current timestamp.
            cooldown: Minimum time between flushes.

        Returns:
            True if batch should be flushed.
        """
        if not self._entries:
            return False
        if len(self._entries) >= self._max_batch_size:
            return True
        return current_time - self._entries[0].added_at >= cooldown

    def flush(self) -> list[BatchEntry]:
        """Flush and return all batched entries."""
        entries = list(self._entries)
        self._entries.clear()
        return entries

    @property
    def size(self) -> int:
        """Current batch size."""
        return len(self._entries)

    @property
    def is_empty(self) -> bool:
        """Check if batch is empty."""
        return len(self._entries) == 0
