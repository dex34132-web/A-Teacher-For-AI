"""V2.6 interface contracts for EVO V2.5 routing.

Defines the clean interface contracts that V2.6 (long-term memory and
deep agent connection) will later implement. V2.5 does NOT implement
V2.6 memory or deep agent connection yet — these are contracts only.

Design principle:
    V2.5 establishes the universal routing layer and its contracts.
    V2.6 will implement the memory and connection semantics behind
    these same contracts without redesigning the core.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from core.routing.context import ContextState
from core.routing.cost import CostEstimate
from core.routing.decision import RoutingDecision
from core.routing.destinations import Destination
from core.routing.information import InformationPacket


class AgentRoutingContract(ABC):
    """The universal contract that future agent adapters (V2.6+) implement.

    These methods define the minimal surface an adapter must expose to
    connect any AI system to EVO. V2.5 only declares them; it does not
    ship any concrete adapter.
    """

    @abstractmethod
    def submit_information(self, packet: InformationPacket) -> RoutingDecision:
        """Submit information for routing through EVO."""
        ...

    @abstractmethod
    def request_information(
        self,
        query: str,
        limit: int = 10,
        scope: str | None = None,
    ) -> list[InformationPacket]:
        """Request relevant information from EVO."""
        ...

    @abstractmethod
    def request_route(
        self,
        packet: InformationPacket,
        policy: str | None = None,
    ) -> RoutingDecision:
        """Request a routing decision without side effects."""
        ...

    @abstractmethod
    def get_routing_decision(self, packet: InformationPacket) -> RoutingDecision:
        """Retrieve a cached or recomputed routing decision."""
        ...

    @abstractmethod
    def register_destination(self, destination: Destination) -> None:
        """Register a new routing destination."""
        ...

    @abstractmethod
    def register_policy(self, name: str, policy: Any) -> None:
        """Register a routing policy by name."""
        ...

    @abstractmethod
    def estimate_cost(self, packet: InformationPacket) -> CostEstimate:
        """Estimate the cost of routing a packet."""
        ...

    @abstractmethod
    def get_context_state(self) -> ContextState:
        """Return the current routing context state."""
        ...

    @abstractmethod
    def record_routing_result(
        self,
        packet_id: str,
        success: bool,
        actual_cost: CostEstimate | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record the observed outcome of a prior routing decision."""
        ...


class DestinationHandler(ABC):
    """Contract for a destination implementation (V2.6+).

    V2.5 routes information to abstract destinations. V2.6 adapters
    (e.g. lifecycle bridge, retrieval bridge, knowledge bridge) will
    implement this contract to actually process routed information.
    """

    @abstractmethod
    def handle(self, packet: InformationPacket, decision: RoutingDecision) -> None:
        """Process a packet routed to this destination."""
        ...
