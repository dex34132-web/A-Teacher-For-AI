"""Routing destinations for Lerev V2.5.

Defines where information can be routed within Lerev. Destinations are
extensible and agent-agnostic. The same destination types work for
coding agents, general agents, hosted models, and local models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class DestinationType(Enum):
    """Built-in routing destinations.

    These are the standard destinations within Lerev. Custom destinations
    can be registered by extending the system.
    """

    # Agent interaction
    AGENT_CONTEXT = auto()  # Return to agent as context
    LEREV_CONTEXT = auto()  # Internal Lerev context

    # Learning & knowledge
    LEARNING = auto()  # Route to learning subsystem
    RETRIEVAL = auto()  # Route to retrieval for indexing
    KNOWLEDGE = auto()  # Route to knowledge base
    CONFLICT = auto()  # Route to conflict detection

    # Confidence & quality
    CONFIDENCE = auto()  # Route to confidence estimation
    LIFECYCLE = auto()  # Route to lifecycle management

    # Provenance & observability
    PROVENANCE = auto()  # Route to provenance tracking
    OBSERVABILITY = auto()  # Route to telemetry/observability

    # Control
    DISCARD = auto()  # Drop the information
    DEFER = auto()  # Defer for later processing
    BATCH = auto()  # Add to batch for group processing

    # Custom (extensible)
    CUSTOM = auto()  # User-registered destination


@dataclass(frozen=True, slots=True)
class Destination:
    """A routing destination with optional configuration.

    Attributes:
        destination_type: The type of destination.
        name: Optional human-readable name.
        priority: Processing priority (lower = higher priority).
        max_batch_size: Maximum items to batch together.
        timeout_seconds: Processing timeout (None = no limit).
        metadata: Destination-specific configuration.
    """

    destination_type: DestinationType
    name: str = ""
    priority: int = 2
    max_batch_size: int = 1
    timeout_seconds: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_terminal(self) -> bool:
        """Check if this destination ends the routing chain."""
        return self.destination_type in {
            DestinationType.DISCARD,
            DestinationType.AGENT_CONTEXT,
        }

    @property
    def is_control(self) -> bool:
        """Check if this is a control destination (not a processing destination)."""
        return self.destination_type in {
            DestinationType.DISCARD,
            DestinationType.DEFER,
            DestinationType.BATCH,
        }

    def matches(self, other: Destination) -> bool:
        """Check if two destinations refer to the same target."""
        if self.destination_type != other.destination_type:
            return False
        if self.name and other.name:
            return self.name == other.name
        return True


# ---------------------------------------------------------------------------
# Pre-built destination instances
# ---------------------------------------------------------------------------

AGENT_CONTEXT = Destination(destination_type=DestinationType.AGENT_CONTEXT, name="agent_context")
LEREV_CONTEXT = Destination(destination_type=DestinationType.LEREV_CONTEXT, name="lerev_context")
LEARNING = Destination(destination_type=DestinationType.LEARNING, name="learning")
RETRIEVAL = Destination(destination_type=DestinationType.RETRIEVAL, name="retrieval")
KNOWLEDGE = Destination(destination_type=DestinationType.KNOWLEDGE, name="knowledge")
CONFLICT = Destination(destination_type=DestinationType.CONFLICT, name="conflict")
CONFIDENCE = Destination(destination_type=DestinationType.CONFIDENCE, name="confidence")
LIFECYCLE = Destination(destination_type=DestinationType.LIFECYCLE, name="lifecycle")
PROVENANCE = Destination(destination_type=DestinationType.PROVENANCE, name="provenance")
OBSERVABILITY = Destination(destination_type=DestinationType.OBSERVABILITY, name="observability")
DISCARD = Destination(destination_type=DestinationType.DISCARD, name="discard")
DEFER = Destination(destination_type=DestinationType.DEFER, name="defer")
BATCH = Destination(destination_type=DestinationType.BATCH, name="batch")

# Default destination registry
DEFAULT_DESTINATIONS: list[Destination] = [
    AGENT_CONTEXT,
    LEREV_CONTEXT,
    LEARNING,
    RETRIEVAL,
    KNOWLEDGE,
    CONFLICT,
    CONFIDENCE,
    LIFECYCLE,
    PROVENANCE,
    OBSERVABILITY,
    DISCARD,
    DEFER,
    BATCH,
]
