"""Priority system for EVO V2.5 routing.

Defines priority levels and configuration for routing decisions.
Priority influences routing, processing, and deferral decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class Priority(IntEnum):
    """Priority levels for routing.

    Lower numeric values indicate higher priority.
    Using IntEnum allows direct comparison with integers.
    """

    CRITICAL = 0  # Must be processed immediately
    HIGH = 1  # Should be processed soon
    NORMAL = 2  # Standard processing order
    LOW = 3  # Process when resources available
    BACKGROUND = 4  # Process only when idle

    @classmethod
    def from_int(cls, value: int) -> Priority:
        """Convert an integer to a Priority, clamping to valid range."""
        if value <= cls.CRITICAL:
            return cls.CRITICAL
        if value >= cls.BACKGROUND:
            return cls.BACKGROUND
        return cls(value)

    @classmethod
    def from_string(cls, name: str) -> Priority:
        """Convert a string name to a Priority."""
        upper = name.upper().strip()
        mapping = {
            "CRITICAL": cls.CRITICAL,
            "HIGH": cls.HIGH,
            "NORMAL": cls.NORMAL,
            "LOW": cls.LOW,
            "BACKGROUND": cls.BACKGROUND,
        }
        return mapping.get(upper, cls.NORMAL)

    @property
    def label(self) -> str:
        """Human-readable label."""
        return self.name.lower()

    @property
    def is_urgent(self) -> bool:
        """Check if this priority is urgent (CRITICAL or HIGH)."""
        return self <= Priority.HIGH

    @property
    def is_deferrable(self) -> bool:
        """Check if this priority can be deferred."""
        return self >= Priority.LOW


@dataclass(frozen=True, slots=True)
class PriorityConfig:
    """Configuration for priority-based routing behavior.

    Attributes:
        deferral_threshold: Priority at or below which deferral is allowed.
        batch_threshold: Priority at or below which batching is allowed.
        max_deferred_age_seconds: Maximum age before forced processing.
        critical_boost: Priority boost for critical items.
        high_boost: Priority boost for high-priority items.
    """

    deferral_threshold: Priority = Priority.LOW
    batch_threshold: Priority = Priority.LOW
    max_deferred_age_seconds: float = 300.0
    critical_boost: int = 0
    high_boost: int = 0

    def should_defer(self, priority: Priority) -> bool:
        """Check if a given priority can be deferred."""
        return priority >= self.deferral_threshold

    def should_batch(self, priority: Priority) -> bool:
        """Check if a given priority can be batched."""
        return priority >= self.batch_threshold

    def apply_boost(self, priority: Priority) -> Priority:
        """Apply priority boost based on priority level."""
        if priority == Priority.CRITICAL:
            return Priority.from_int(priority + self.critical_boost)
        if priority == Priority.HIGH:
            return Priority.from_int(priority + self.high_boost)
        return priority

    def resolve_priority(self, packet_priority: int, config_boost: int = 0) -> Priority:
        """Resolve a raw priority integer to a Priority enum."""
        boosted = packet_priority + config_boost
        return Priority.from_int(boosted)
