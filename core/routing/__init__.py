"""EVO V2.5 — Universal Agent Routing & Intelligence Layer.

This module provides the agent-agnostic routing infrastructure that
connects any AI system to EVO's learning, experience, memory, and
knowledge subsystems.

The core principle:
    Let the agent do the semantic thinking.
    Let EVO make the routing structured, efficient, safe, explainable,
    and cheap.

V2.5 is agent-agnostic at its core. It does not depend on any specific
AI agent, model, or harness. The same core should theoretically be usable
by hosted AI, local AI, coding agents, general agents, custom agents,
multi-agent systems, and future agent architectures.
"""

from __future__ import annotations

from core.routing.cache import RoutingCache
from core.routing.context import ContextBudget, ContextState
from core.routing.contracts import (
    AgentRoutingContract,
    DestinationHandler,
)
from core.routing.cost import CostEstimate, CostPrecision, CostType
from core.routing.decision import (
    RoutingDecision,
    RoutingStrategy,
)
from core.routing.destinations import Destination, DestinationType
from core.routing.efficiency import EfficiencyController
from core.routing.information import (
    InformationPacket,
    InformationType,
    SensitivityLevel,
    SourceType,
)
from core.routing.integration import (
    EVOIntegrationBridge,
    make_collector_handler,
    make_noop_handler,
)
from core.routing.priority import Priority, PriorityConfig
from core.routing.protocol import (
    AgentOperation,
    RoutingIntent,
    format_protocol_prompt,
)
from core.routing.provenance import ProvenanceTracker, RoutingProvenance
from core.routing.router import UniversalRouter
from core.routing.security import (
    SecurityPolicy,
    validate_instruction_boundary,
)
from core.routing.telemetry import TelemetryEvent, TelemetryRecord

__all__ = [
    # Information model
    "InformationPacket",
    "InformationType",
    "SensitivityLevel",
    "SourceType",
    # Destinations
    "Destination",
    "DestinationType",
    # Routing decisions
    "RoutingDecision",
    "RoutingStrategy",
    "CostEstimate",
    "CostType",
    "CostPrecision",
    # Priority
    "Priority",
    "PriorityConfig",
    # Context
    "ContextState",
    "ContextBudget",
    # Security
    "SecurityPolicy",
    "validate_instruction_boundary",
    # Provenance
    "RoutingProvenance",
    "ProvenanceTracker",
    # Telemetry
    "TelemetryEvent",
    "TelemetryRecord",
    "TelemetryRecorder",
    # Efficiency
    "EfficiencyController",
    # Caching
    "RoutingCache",
    # Protocol (agent-as-semantic-router)
    "AgentOperation",
    "RoutingIntent",
    "format_protocol_prompt",
    # Contracts (V2.6 interface)
    "AgentRoutingContract",
    "DestinationHandler",
    # Integration bridge (V2.4.2)
    "EVOIntegrationBridge",
    "make_noop_handler",
    "make_collector_handler",
    # Main router
    "UniversalRouter",
]
