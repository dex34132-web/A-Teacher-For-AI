"""Routing decision model for Lerev V2.5.

Defines the structured output of routing decisions, including strategies,
cost estimation, and multi-destination support.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from core.routing.cost import CostEstimate
from core.routing.destinations import Destination, DestinationType


class RoutingStrategy(Enum):
    """Available routing strategies.

    The router chooses the cheapest valid strategy rather than
    automatically performing every possible operation.
    """

    DIRECT = auto()  # Route directly to a single destination
    CONDITIONAL = auto()  # Route based on runtime conditions
    DEFERRED = auto()  # Defer for later processing
    BATCHED = auto()  # Batch with similar requests
    DISCARD = auto()  # Drop the information
    MULTI_DESTINATION = auto()  # Route to multiple destinations


@dataclass(frozen=True, slots=True)
class RoutingDecision:
    """A structured routing decision.

    This is the output of the routing pipeline. It describes where
    information should go, why, and at what cost.

    Attributes:
        packet_id: The source information packet ID.
        destinations: Where to route this information.
        strategy: The routing strategy used.
        confidence: Router's confidence in this decision (0.0-1.0).
        reason: Human-readable explanation of the decision.
        priority: Final priority after processing.
        cost_estimates: Estimated costs for this routing.
        policy_applied: Which routing policy was applied.
        deferred: Whether this is deferred for later.
        rejected: Whether this was rejected.
        rejection_reason: Why it was rejected (if applicable).
        metadata: Decision-specific metadata.
    """

    packet_id: str
    destinations: tuple[Destination, ...]
    strategy: RoutingStrategy = RoutingStrategy.DIRECT
    confidence: float = 1.0
    reason: str = ""
    priority: int = 2
    cost_estimates: tuple[CostEstimate, ...] = ()
    policy_applied: str = ""
    deferred: bool = False
    rejected: bool = False
    rejection_reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_terminal(self) -> bool:
        """Check if this decision ends routing (discard or agent context)."""
        return any(d.is_terminal for d in self.destinations)

    @property
    def destination_count(self) -> int:
        """Return the number of destinations."""
        return len(self.destinations)

    @property
    def has_cost(self) -> bool:
        """Check if any cost estimates are present."""
        return len(self.cost_estimates) > 0

    @property
    def total_estimated_cost(self) -> float:
        """Sum all cost estimates."""
        return sum(c.value for c in self.cost_estimates)

    def destination_types(self) -> tuple[DestinationType, ...]:
        """Return the destination types as a tuple."""
        return tuple(d.destination_type for d in self.destinations)

    def has_destination(self, dest_type: DestinationType) -> bool:
        """Check if a specific destination type is included."""
        return any(d.destination_type == dest_type for d in self.destinations)


# ---------------------------------------------------------------------------
# Helper constructors
# ---------------------------------------------------------------------------


def create_direct_decision(
    packet_id: str,
    destination: Destination,
    reason: str = "",
    policy: str = "",
) -> RoutingDecision:
    """Create a simple direct routing decision."""
    return RoutingDecision(
        packet_id=packet_id,
        destinations=(destination,),
        strategy=RoutingStrategy.DIRECT,
        reason=reason,
        policy_applied=policy,
    )


def create_multi_decision(
    packet_id: str,
    destinations: list[Destination],
    reason: str = "",
    policy: str = "",
) -> RoutingDecision:
    """Create a multi-destination routing decision."""
    return RoutingDecision(
        packet_id=packet_id,
        destinations=tuple(destinations),
        strategy=RoutingStrategy.MULTI_DESTINATION,
        reason=reason,
        policy_applied=policy,
    )


def create_deferred_decision(
    packet_id: str,
    reason: str = "",
    policy: str = "",
) -> RoutingDecision:
    """Create a deferred routing decision."""
    return RoutingDecision(
        packet_id=packet_id,
        destinations=(),
        strategy=RoutingStrategy.DEFERRED,
        deferred=True,
        reason=reason,
        policy_applied=policy,
    )


def create_rejected_decision(
    packet_id: str,
    reason: str = "",
    policy: str = "",
) -> RoutingDecision:
    """Create a rejected routing decision."""
    return RoutingDecision(
        packet_id=packet_id,
        destinations=(),
        strategy=RoutingStrategy.DISCARD,
        rejected=True,
        rejection_reason=reason,
        reason=reason,
        policy_applied=policy,
    )


def create_discard_decision(
    packet_id: str,
    reason: str = "",
    policy: str = "",
) -> RoutingDecision:
    """Create a discard routing decision."""
    return RoutingDecision(
        packet_id=packet_id,
        destinations=(Destination(destination_type=DestinationType.DISCARD, name="discard"),),
        strategy=RoutingStrategy.DISCARD,
        reason=reason,
        policy_applied=policy,
    )
