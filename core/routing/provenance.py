"""Provenance tracking for Lerev V2.5 routing.

Records compact provenance for every important routing decision.
Explains why information was routed, where, which policy applied,
and whether it was deferred or rejected.

Do not create giant verbose logs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.routing.decision import RoutingDecision
from core.routing.information import InformationPacket


@dataclass(frozen=True, slots=True)
class RoutingProvenance:
    """Compact provenance for a routing decision.

    Attributes:
        packet_id: The routed packet's ID.
        decision_id: Unique ID for this provenance record.
        timestamp: When the routing occurred.
        packet_source: Where the packet came from.
        packet_type: Type of information routed.
        destinations: Where it was routed.
        strategy: Routing strategy used.
        confidence: Router's confidence.
        reason: Why this routing was chosen.
        policy_applied: Which policy was applied.
        estimated_cost: Estimated cost of routing.
        was_deferred: Whether it was deferred.
        was_rejected: Whether it was rejected.
        rejection_reason: Why it was rejected (if applicable).
        parent_provenance: Provenance of parent packet (if any).
        metadata: Additional provenance data.
    """

    packet_id: str
    decision_id: str
    timestamp: float
    packet_source: str
    packet_type: str
    destinations: tuple[str, ...]
    strategy: str
    confidence: float
    reason: str
    policy_applied: str = ""
    estimated_cost: float = 0.0
    was_deferred: bool = False
    was_rejected: bool = False
    rejection_reason: str = ""
    parent_provenance: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_terminal(self) -> bool:
        """Check if this provenance represents a terminal routing."""
        return "DISCARD" in self.destinations or "AGENT_CONTEXT" in self.destinations

    @property
    def destination_count(self) -> int:
        """Number of destinations."""
        return len(self.destinations)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for persistence."""
        return {
            "packet_id": self.packet_id,
            "decision_id": self.decision_id,
            "timestamp": self.timestamp,
            "packet_source": self.packet_source,
            "packet_type": self.packet_type,
            "destinations": list(self.destinations),
            "strategy": self.strategy,
            "confidence": self.confidence,
            "reason": self.reason,
            "policy_applied": self.policy_applied,
            "estimated_cost": self.estimated_cost,
            "was_deferred": self.was_deferred,
            "was_rejected": self.was_rejected,
            "rejection_reason": self.rejection_reason,
            "parent_provenance": self.parent_provenance,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RoutingProvenance:
        """Deserialize from dictionary."""
        return cls(
            packet_id=data["packet_id"],
            decision_id=data["decision_id"],
            timestamp=data["timestamp"],
            packet_source=data["packet_source"],
            packet_type=data["packet_type"],
            destinations=tuple(data["destinations"]),
            strategy=data["strategy"],
            confidence=data["confidence"],
            reason=data["reason"],
            policy_applied=data.get("policy_applied", ""),
            estimated_cost=data.get("estimated_cost", 0.0),
            was_deferred=data.get("was_deferred", False),
            was_rejected=data.get("was_rejected", False),
            rejection_reason=data.get("rejection_reason", ""),
            parent_provenance=data.get("parent_provenance", ""),
            metadata=data.get("metadata", {}),
        )


def create_provenance(
    packet: InformationPacket,
    decision: RoutingDecision,
    decision_id: str,
    timestamp: float,
) -> RoutingProvenance:
    """Create a RoutingProvenance from a packet and decision.

    Args:
        packet: The source information packet.
        decision: The routing decision.
        decision_id: Unique ID for this provenance record.
        timestamp: When the routing occurred.

    Returns:
        A RoutingProvenance record.
    """
    return RoutingProvenance(
        packet_id=packet.id,
        decision_id=decision_id,
        timestamp=timestamp,
        packet_source=packet.source.name,
        packet_type=packet.information_type.name,
        destinations=tuple(d.name or d.destination_type.name for d in decision.destinations),
        strategy=decision.strategy.name,
        confidence=decision.confidence,
        reason=decision.reason,
        policy_applied=decision.policy_applied,
        estimated_cost=decision.total_estimated_cost,
        was_deferred=decision.deferred,
        was_rejected=decision.rejected,
        rejection_reason=decision.rejection_reason,
        parent_provenance=packet.provenance[-1] if packet.provenance else "",
    )


class ProvenanceTracker:
    """Tracks routing provenance with bounded history.

    No global mutable state — provenance is per-tracker instance.
    """

    def __init__(self, max_history: int = 10_000) -> None:
        """Initialize the provenance tracker.

        Args:
            max_history: Maximum provenance records to retain.
        """
        self._max_history = max_history
        self._records: list[RoutingProvenance] = []
        self._by_packet: dict[str, list[str]] = {}  # packet_id -> [decision_ids]

    def record(self, provenance: RoutingProvenance) -> None:
        """Record a provenance entry.

        Args:
            provenance: The provenance to record.
        """
        self._records.append(provenance)
        if len(self._records) > self._max_history:
            self._records = self._records[-self._max_history:]
            self._rebuild_by_packet()

        packet_id = provenance.packet_id
        if packet_id not in self._by_packet:
            self._by_packet[packet_id] = []
        self._by_packet[packet_id].append(provenance.decision_id)

    def _rebuild_by_packet(self) -> None:
        """Rebuild _by_packet index from current records."""
        self._by_packet.clear()
        for r in self._records:
            if r.packet_id not in self._by_packet:
                self._by_packet[r.packet_id] = []
            self._by_packet[r.packet_id].append(r.decision_id)

    def get_for_packet(self, packet_id: str) -> list[RoutingProvenance]:
        """Get all provenance records for a packet."""
        decision_ids = self._by_packet.get(packet_id, [])
        return [r for r in self._records if r.decision_id in decision_ids]

    def get_recent(self, count: int = 10) -> list[RoutingProvenance]:
        """Get the most recent provenance records."""
        return self._records[-count:]

    def count(self) -> int:
        """Return total provenance records."""
        return len(self._records)

    def clear(self) -> None:
        """Clear all provenance records."""
        self._records.clear()
        self._by_packet.clear()
