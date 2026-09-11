"""Agent-as-Semantic-Router protocol for EVO V2.5.

Allows an AI agent to communicate routing intent directly to EVO.
EVO does not perform expensive semantic reasoning when the connected
AI agent already understands the meaning of its own actions.

Principles:
- Compact: Minimal token footprint (< 200 tokens for protocol schema)
- Model-agnostic: Works with any LLM, local model, or rule-based agent
- Structured: Validated enum-driven operations
- Injection-resistant: Content is treated as payload data, never executable code
- Extensible: Metadata dictionary for agent-specific needs
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from core.routing.information import (
    InformationPacket,
    InformationType,
    SensitivityLevel,
    SourceType,
)
from core.routing.priority import Priority


class AgentOperation(Enum):
    """Operations an external agent can request through the routing protocol."""

    NEED_CONTEXT = "need_context"  # Agent requests context for current task
    NEED_KNOWLEDGE = "need_knowledge"  # Agent requests specific domain knowledge
    REPORT_OBSERVATION = "report_observation"  # Agent reports an environmental observation
    REPORT_OUTCOME = "report_outcome"  # Agent reports the result of an action
    REPORT_FEEDBACK = "report_feedback"  # Agent reports success/failure feedback
    STORE_CANDIDATE = "store_candidate"  # Agent suggests information to learn/store
    REQUEST_RELEVANT_INFO = "request_relevant_info"  # Agent queries relevant memories/facts
    HEARTBEAT = "heartbeat"  # Keepalive / status inquiry


# Mapping from agent operations to normalized InformationTypes
_OP_TO_TYPE: dict[AgentOperation, InformationType] = {
    AgentOperation.NEED_CONTEXT: InformationType.CONTEXT,
    AgentOperation.NEED_KNOWLEDGE: InformationType.TASK,
    AgentOperation.REPORT_OBSERVATION: InformationType.OBSERVATION,
    AgentOperation.REPORT_OUTCOME: InformationType.OUTCOME,
    AgentOperation.REPORT_FEEDBACK: InformationType.FEEDBACK,
    AgentOperation.STORE_CANDIDATE: InformationType.EXPERIENCE,
    AgentOperation.REQUEST_RELEVANT_INFO: InformationType.DATA,
    AgentOperation.HEARTBEAT: InformationType.METADATA,
}


@dataclass(frozen=True, slots=True)
class RoutingIntent:
    """Structured message from an agent communicating routing intent.

    Attributes:
        operation: The requested AgentOperation.
        payload: Content or payload data from the agent.
        scope: Target scope or namespace.
        priority: Processing urgency.
        sensitivity: Sensitivity classification.
        confidence: Agent's subjective confidence (0.0 - 1.0).
        context_hint: Short hint about current subtask or goal.
        metadata: Domain-specific parameters.
    """

    operation: AgentOperation
    payload: str
    scope: str = "default"
    priority: Priority = Priority.NORMAL
    sensitivity: SensitivityLevel = SensitivityLevel.PUBLIC
    confidence: float = 1.0
    context_hint: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_packet(self) -> InformationPacket:
        """Convert this intent into a normalized InformationPacket."""
        info_type = _OP_TO_TYPE.get(self.operation, InformationType.UNKNOWN)
        meta = dict(self.metadata)
        if self.context_hint:
            meta["context_hint"] = self.context_hint
        meta["operation"] = self.operation.value

        return InformationPacket(
            content=self.payload,
            information_type=info_type,
            source=SourceType.AGENT,
            scope=self.scope,
            priority=int(self.priority.value),
            sensitivity=self.sensitivity,
            confidence=self.confidence,
            metadata=meta,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize intent to JSON-serializable dictionary."""
        return {
            "operation": self.operation.value,
            "payload": self.payload,
            "scope": self.scope,
            "priority": self.priority.name,
            "sensitivity": self.sensitivity.name,
            "confidence": self.confidence,
            "context_hint": self.context_hint,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RoutingIntent:
        """Parse intent from a dictionary."""
        op_val = data.get("operation", "report_observation")
        try:
            op = AgentOperation(op_val)
        except ValueError:
            op = AgentOperation.REPORT_OBSERVATION

        priority_str = data.get("priority", "NORMAL")
        priority = Priority.from_string(priority_str)

        sens_str = data.get("sensitivity", "PUBLIC")
        try:
            sensitivity = SensitivityLevel[sens_str]
        except KeyError:
            sensitivity = SensitivityLevel.PUBLIC

        return cls(
            operation=op,
            payload=str(data.get("payload", "")),
            scope=str(data.get("scope", "default")),
            priority=priority,
            sensitivity=sensitivity,
            confidence=float(data.get("confidence", 1.0)),
            context_hint=str(data.get("context_hint", "")),
            metadata=dict(data.get("metadata", {})),
        )

    @classmethod
    def from_json(cls, json_str: str) -> RoutingIntent:
        """Parse intent from JSON string with fallback on malformed input."""
        try:
            data = json.loads(json_str)
            if isinstance(data, dict):
                return cls.from_dict(data)
        except Exception:
            pass
        # Fallback: treat raw string as payload
        return cls(
            operation=AgentOperation.REPORT_OBSERVATION,
            payload=json_str,
        )


def format_protocol_prompt() -> str:
    """Generate a compact protocol explanation string for agents.

    Costs fewer than 100 tokens when included in an agent's context.
    """
    return (
        "EVO Routing Protocol: send JSON with keys:\n"
        "- operation: need_context | need_knowledge | report_observation | "
        "report_outcome | report_feedback | store_candidate | request_relevant_info\n"
        "- payload: <text content>\n"
        "- priority: CRITICAL | HIGH | NORMAL | LOW | BACKGROUND\n"
        "- sensitivity: PUBLIC | PROJECT | PRIVATE | SENSITIVE | SECRET\n"
        "- confidence: 0.0 - 1.0\n"
        "- context_hint: <short string>\n"
    )
