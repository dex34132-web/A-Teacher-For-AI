"""Universal information model for EVO V2.5.

Defines the normalized representation of information flowing through
the routing layer. InformationPackets are the fundamental unit that
agents submit to EVO for routing and processing.

Design principles:
- Agent-agnostic: does not assume coding, chat, or any specific domain
- Type-safe: strong enums for all categorical fields
- Immutable: packets are frozen dataclasses
- Extensible: metadata dict for domain-specific extensions
- Secure: sensitivity classification prevents secret leakage
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum, auto

# ---------------------------------------------------------------------------
# Information types
# ---------------------------------------------------------------------------


class InformationType(Enum):
    """Classification of information content.

    These are domain-agnostic. They work for coding agents, general agents,
    hosted models, local models, and future architectures.
    """

    INSTRUCTION = auto()  # An instruction or command
    TASK = auto()  # A task to be performed
    CONTEXT = auto()  # Supporting context
    OBSERVATION = auto()  # An observation or observation result
    DATA = auto()  # Raw data
    EVENT = auto()  # An event that occurred
    TOOL_RESULT = auto()  # Result from a tool invocation
    FEEDBACK = auto()  # Feedback on a previous action
    OUTCOME = auto()  # Outcome of a completed action
    EVIDENCE = auto()  # Evidence supporting a conclusion
    EXPERIENCE = auto()  # A learned experience
    KNOWLEDGE = auto()  # Structured knowledge
    METADATA = auto()  # Metadata about other information
    UNKNOWN = auto()  # Unclassified information


# ---------------------------------------------------------------------------
# Source tracking
# ---------------------------------------------------------------------------


class SourceType(Enum):
    """Where the information originated."""

    AGENT = auto()  # From the connected AI agent
    EVO = auto()  # From EVO itself (internal)
    USER = auto()  # From a human user
    EXTERNAL = auto()  # From an external system
    UNKNOWN = auto()  # Source not identified


# ---------------------------------------------------------------------------
# Sensitivity classification
# ---------------------------------------------------------------------------


class SensitivityLevel(Enum):
    """Security classification for information.

    Controls visibility, caching, logging, and routing behavior.
    """

    PUBLIC = auto()  # Non-sensitive, safe for all contexts
    PROJECT = auto()  # Project-scoped, not for external sharing
    PRIVATE = auto()  # Private to the current session/agent
    SENSITIVE = auto()  # Sensitive data, restricted handling
    SECRET = auto()  # Secrets, never logged or cached
    UNKNOWN = auto()  # Classification unknown, treat as PRIVATE


# ---------------------------------------------------------------------------
# InformationPacket
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class InformationPacket:
    """A normalized unit of information for routing through EVO.

    This is the fundamental input to the V2.5 routing system. Agents
    submit InformationPackets, and EVO routes them to appropriate
    destinations based on type, priority, cost, and policy.

    Attributes:
        id: Unique identifier for this packet.
        content: The information content (text).
        information_type: Classification of the content.
        source: Where this information came from.
        scope: Scoping identifier (e.g., project, session, agent).
        timestamp: When this packet was created.
        priority: Routing priority level.
        sensitivity: Security classification.
        confidence: Agent-provided confidence (0.0-1.0).
        cost_estimate: Agent-provided cost estimate.
        provenance: Provenance chain (list of parent packet IDs).
        metadata: Extensible metadata for domain-specific needs.
        tags: Optional tags for filtering/grouping.
        parent_id: Optional reference to a parent packet.
    """

    content: str
    information_type: InformationType = InformationType.UNKNOWN
    source: SourceType = SourceType.AGENT
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    scope: str = ""
    timestamp: float = field(default_factory=lambda: datetime.now(UTC).timestamp())
    priority: int = 2  # 0=CRITICAL, 1=HIGH, 2=NORMAL, 3=LOW, 4=BACKGROUND
    sensitivity: SensitivityLevel = SensitivityLevel.UNKNOWN
    confidence: float = 0.5
    cost_estimate: float | None = None
    provenance: tuple[str, ...] = ()
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)
    tags: frozenset[str] = field(default_factory=frozenset)
    parent_id: str | None = None

    @property
    def is_instruction(self) -> bool:
        """Check if this packet contains an instruction."""
        return self.information_type == InformationType.INSTRUCTION

    @property
    def is_data(self) -> bool:
        """Check if this packet contains data (not instruction)."""
        return self.information_type in {
            InformationType.OBSERVATION,
            InformationType.DATA,
            InformationType.CONTEXT,
            InformationType.TOOL_RESULT,
            InformationType.METADATA,
        }

    @property
    def is_sensitive(self) -> bool:
        """Check if this packet requires sensitive handling."""
        return self.sensitivity in {
            SensitivityLevel.SENSITIVE,
            SensitivityLevel.SECRET,
        }

    @property
    def content_length(self) -> int:
        """Return the character length of the content."""
        return len(self.content)

    @property
    def estimated_tokens(self) -> int:
        """Rough token estimate (chars / 4)."""
        return max(1, self.content_length // 4)

    def with_parent(self, parent_id: str) -> InformationPacket:
        """Return a copy with a parent reference and extended provenance."""
        return InformationPacket(
            content=self.content,
            information_type=self.information_type,
            source=self.source,
            id=self.id,
            scope=self.scope,
            timestamp=self.timestamp,
            priority=self.priority,
            sensitivity=self.sensitivity,
            confidence=self.confidence,
            cost_estimate=self.cost_estimate,
            provenance=(*self.provenance, parent_id),
            metadata=self.metadata,
            tags=self.tags,
            parent_id=parent_id,
        )

    def extend_provenance(self, parent_id: str) -> InformationPacket:
        """Return a copy with extended provenance chain."""
        return InformationPacket(
            content=self.content,
            information_type=self.information_type,
            source=self.source,
            id=self.id,
            scope=self.scope,
            timestamp=self.timestamp,
            priority=self.priority,
            sensitivity=self.sensitivity,
            confidence=self.confidence,
            cost_estimate=self.cost_estimate,
            provenance=(*self.provenance, parent_id),
            metadata=self.metadata,
            tags=self.tags,
            parent_id=self.parent_id,
        )
