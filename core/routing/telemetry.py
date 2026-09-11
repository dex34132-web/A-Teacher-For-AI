"""Telemetry and observability for EVO V2.5 routing.

Structured observability for routing decisions, latency, destination
usage, deferred operations, rejected operations, cost estimates,
cache effectiveness, and errors.

Telemetry must itself respect security and privacy boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class TelemetryEvent(Enum):
    """Types of telemetry events."""

    ROUTE_START = auto()  # Routing operation started
    ROUTE_COMPLETE = auto()  # Routing operation completed
    ROUTE_DEFERRED = auto()  # Operation was deferred
    ROUTE_REJECTED = auto()  # Operation was rejected
    ROUTE_CACHED = auto()  # Cache hit
    ROUTE_BATCHED = auto()  # Added to batch
    DESTINATION_DISPATCH = auto()  # Dispatched to destination
    COST_ESTIMATED = auto()  # Cost was estimated
    COST_MEASURED = auto()  # Actual cost measured
    SECURITY_BLOCK = auto()  # Security policy blocked
    INJECTION_DETECTED = auto()  # Prompt injection detected
    ERROR = auto()  # Error occurred
    BATCH_FLUSH = auto()  # Batch was flushed
    CACHE_INVALIDATE = auto()  # Cache was invalidated


@dataclass(frozen=True, slots=True)
class TelemetryRecord:
    """A single telemetry record.

    Attributes:
        event: Type of telemetry event.
        timestamp: When the event occurred.
        packet_id: Related packet ID (if any).
        latency_ms: Latency in milliseconds (if applicable).
        destinations: Destination names (if applicable).
        metadata: Additional telemetry data.
    """

    event: TelemetryEvent
    timestamp: float
    packet_id: str = ""
    latency_ms: float = 0.0
    destinations: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "event": self.event.name,
            "timestamp": self.timestamp,
            "packet_id": self.packet_id,
            "latency_ms": self.latency_ms,
            "destinations": list(self.destinations),
            "metadata": self.metadata,
        }


class TelemetryRecorder:
    """Mutable telemetry accumulator for tracking aggregates."""

    def __init__(self, max_records: int = 50_000) -> None:
        """Initialize the telemetry recorder.

        Args:
            max_records: Maximum records to retain.
        """
        self._max_records = max_records
        self._records: list[TelemetryRecord] = []
        self._counters: dict[str, int] = {}
        self._latencies: dict[str, list[float]] = {}

    def record(self, event: TelemetryRecord) -> None:
        """Record a telemetry event.

        Args:
            event: The telemetry record.
        """
        self._records.append(event)
        if len(self._records) > self._max_records:
            self._records = self._records[-self._max_records:]

        # Update counters
        key = event.event.name
        self._counters[key] = self._counters.get(key, 0) + 1

        # Update latencies
        if event.latency_ms > 0:
            if key not in self._latencies:
                self._latencies[key] = []
            self._latencies[key].append(event.latency_ms)
            if len(self._latencies[key]) > 1000:
                self._latencies[key] = self._latencies[key][-1000:]

    def get_counter(self, event_name: str) -> int:
        """Get the count for a telemetry event type."""
        return self._counters.get(event_name, 0)

    def get_latency_stats(self, event_name: str) -> dict[str, float]:
        """Get latency statistics for an event type."""
        latencies = self._latencies.get(event_name, [])
        if not latencies:
            return {"count": 0, "min": 0.0, "max": 0.0, "avg": 0.0, "p95": 0.0}

        sorted_lat = sorted(latencies)
        count = len(sorted_lat)
        p95_idx = max(0, int(count * 0.95) - 1)

        return {
            "count": float(count),
            "min": sorted_lat[0],
            "max": sorted_lat[-1],
            "avg": sum(sorted_lat) / count,
            "p95": sorted_lat[p95_idx],
        }

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of all telemetry."""
        return {
            "total_records": len(self._records),
            "counters": dict(self._counters),
            "latency_stats": {
                k: self.get_latency_stats(k) for k in self._latencies
            },
        }

    def get_recent(self, count: int = 10) -> list[TelemetryRecord]:
        """Get recent telemetry records."""
        return self._records[-count:]

    def clear(self) -> None:
        """Clear all telemetry data."""
        self._records.clear()
        self._counters.clear()
        self._latencies.clear()
