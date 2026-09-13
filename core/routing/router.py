"""Universal Router for Lerev V2.5.

The UniversalRouter is the main entry point for agent-agnostic routing.
It orchestrates the routing pipeline and provides the contracts that
future adapters can use to connect any AI system to Lerev.

V2.5 boundary:
- Routes information
- Provides context and cost awareness
- Integrates with existing V2.4.2 systems
- Does NOT implement long-term agent memory or deep agent connection
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from core.routing.cache import RoutingCache
from core.routing.context import ContextBudget, ContextState
from core.routing.cost import CostEstimate
from core.routing.decision import RoutingDecision
from core.routing.destinations import Destination, DestinationType
from core.routing.efficiency import EfficiencyController
from core.routing.information import InformationPacket, SensitivityLevel
from core.routing.pipeline import RoutingPipeline
from core.routing.priority import PriorityConfig
from core.routing.provenance import ProvenanceTracker, RoutingProvenance
from core.routing.security import SecurityPolicy
from core.routing.telemetry import TelemetryEvent, TelemetryRecord, TelemetryRecorder


class UniversalRouter:
    """Agent-agnostic routing layer for Lerev V2.5.

    The router accepts information packets from any AI system and routes
    them to the appropriate Lerev subsystems based on type, priority,
    cost, context, and policy.

    This class does not implement any specific agent, model, or harness.
    It provides the universal contracts that future adapters can use.
    """

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        cache: RoutingCache | None = None,
        telemetry: TelemetryRecorder | None = None,
        provenance: ProvenanceTracker | None = None,
        efficiency: EfficiencyController | None = None,
        priority_config: PriorityConfig | None = None,
        security_policy: SecurityPolicy | None = None,
    ) -> None:
        """Initialize the UniversalRouter.

        Args:
            config: Router configuration.
            cache: Routing result cache.
            telemetry: Telemetry recorder.
            provenance: Provenance tracker.
            efficiency: Efficiency controller.
            priority_config: Priority configuration.
            security_policy: Security policy.
        """
        self._config = config or {}
        self._cache = cache or RoutingCache()
        self._telemetry = telemetry or TelemetryRecorder()
        self._provenance = provenance or ProvenanceTracker()
        self._efficiency = efficiency or EfficiencyController(
            priority_config=priority_config
        )
        self._priority_config = priority_config or PriorityConfig()
        self._security_policy = security_policy or SecurityPolicy()
        self._pipeline = RoutingPipeline(
            efficiency_controller=self._efficiency,
            priority_config=self._priority_config,
            cache=self._cache,
            security_policy=self._security_policy,
            telemetry=self._telemetry,
        )
        self._context = ContextState(
            budget=ContextBudget(
                max_tokens=self._config.get("max_context_tokens", 128_000),
                reserved_tokens=self._config.get("reserved_context_tokens", 4_096),
                overhead_tokens=self._config.get("system_prompt_tokens", 0),
            )
        )
        self._destinations: dict[DestinationType, Destination] = {
            dest.destination_type: dest
            for dest in (
                Destination(destination_type=DestinationType.AGENT_CONTEXT, name="agent_context"),
                Destination(destination_type=DestinationType.LEREV_CONTEXT, name="lerev_context"),
                Destination(destination_type=DestinationType.LEARNING, name="learning"),
                Destination(destination_type=DestinationType.RETRIEVAL, name="retrieval"),
                Destination(destination_type=DestinationType.KNOWLEDGE, name="knowledge"),
                Destination(destination_type=DestinationType.CONFLICT, name="conflict"),
                Destination(destination_type=DestinationType.CONFIDENCE, name="confidence"),
                Destination(destination_type=DestinationType.LIFECYCLE, name="lifecycle"),
                Destination(destination_type=DestinationType.PROVENANCE, name="provenance"),
                Destination(destination_type=DestinationType.OBSERVABILITY, name="observability"),
                Destination(destination_type=DestinationType.DISCARD, name="discard"),
                Destination(destination_type=DestinationType.DEFER, name="defer"),
                Destination(destination_type=DestinationType.BATCH, name="batch"),
            )
        }
        self._policies: dict[str, Any] = {}
        self._result_handlers: dict[
            DestinationType,
            Callable[[InformationPacket, RoutingDecision], None],
        ] = {}
        self._last_decision: RoutingDecision | None = None
        self._started_at = time.time()

    def register_destination(self, destination: Destination) -> None:
        """Register a custom destination.

        Args:
            destination: The destination to register.
        """
        self._destinations[destination.destination_type] = destination

    def register_policy(self, name: str, policy: Any) -> None:
        """Register a routing policy.

        Args:
            name: Policy name.
            policy: Policy object.
        """
        self._policies[name] = policy

    def register_result_handler(
        self,
        destination_type: DestinationType,
        handler: Callable[[InformationPacket, RoutingDecision], None],
    ) -> None:
        """Register a handler for a destination.

        Args:
            destination_type: Destination type.
            handler: Handler function.
        """
        self._result_handlers[destination_type] = handler

    def submit_information(
        self,
        packet: InformationPacket,
        policy: str | None = None,
    ) -> RoutingDecision:
        """Submit information for routing.

        This is the main entry point for agents. The router normalizes,
        classifies, scopes, secures, prioritizes, estimates cost, and
        routes the information.

        Args:
            packet: The information packet to route.
            policy: Optional registered policy name.

        Returns:
            RoutingDecision describing where the information should go.
        """
        start = time.time()
        selected_policy = self._policies.get(policy) if policy else None

        # Update context
        self._context.operation_count += 1
        self._context.current_task = str(
            packet.metadata.get("current_task", self._context.current_task)
        )

        # Check cache for non-sensitive packets
        cached = None
        if packet.sensitivity not in {
            SensitivityLevel.SENSITIVE,
            SensitivityLevel.SECRET,
        }:
            cached = self._cache.get(packet)
            if cached is not None:
                self._telemetry.record(
                    TelemetryRecord(
                        event=TelemetryEvent.ROUTE_CACHED,
                        timestamp=time.time(),
                        packet_id=packet.id,
                        latency_ms=(time.time() - start) * 1000,
                        destinations=tuple(d.name for d in cached.destinations),
                    )
                )
                return cached

        # Run the pipeline
        decision = self._pipeline.route(packet, context=self._context, policy=selected_policy)
        self._last_decision = decision

        # Record provenance
        provenance = RoutingProvenance(
            packet_id=packet.id,
            decision_id=f"route_{packet.id}",
            timestamp=time.time(),
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
        )
        self._provenance.record(provenance)

        # Record telemetry
        self._telemetry.record(
            TelemetryRecord(
                event=TelemetryEvent.ROUTE_COMPLETE,
                timestamp=time.time(),
                packet_id=packet.id,
                latency_ms=(time.time() - start) * 1000,
                destinations=tuple(d.name for d in decision.destinations),
                metadata={
                    "strategy": decision.strategy.name,
                    "confidence": decision.confidence,
                    "cost": decision.total_estimated_cost,
                    "deferred": decision.deferred,
                    "rejected": decision.rejected,
                },
            )
        )

        # Cache the decision for non-sensitive packets
        if packet.sensitivity not in {
            SensitivityLevel.SENSITIVE,
            SensitivityLevel.SECRET,
        }:
            self._cache.put(packet, decision)

        # Update context with routing results
        for dest in decision.destinations:
            dest_name = dest.name or dest.destination_type.name
            if dest_name not in self._context.recent_destinations:
                self._context.recent_destinations.append(dest_name)
        type_name = packet.information_type.name
        if type_name not in self._context.recent_types:
            self._context.recent_types.append(type_name)

        return decision

    def request_route(
        self,
        packet: InformationPacket,
        policy: str | None = None,
    ) -> RoutingDecision:
        """Request a routing decision without dispatching.

        This is an alias for submit_information for agents that only
        want the decision.

        Args:
            packet: The information packet.
            policy: Optional registered policy name.

        Returns:
            RoutingDecision.
        """
        return self.submit_information(packet, policy=policy)

    def get_routing_decision(
        self,
        packet: InformationPacket,
        policy: str | None = None,
    ) -> RoutingDecision:
        """Get a routing decision for an information packet.

        Args:
            packet: The information packet.
            policy: Optional registered policy name.

        Returns:
            RoutingDecision.
        """
        return self.submit_information(packet, policy=policy)

    def estimate_cost(self, packet: InformationPacket) -> CostEstimate:
        """Estimate the cost of processing a packet.

        Args:
            packet: The information packet.

        Returns:
            Cost estimate.
        """
        _, cost = self._pipeline.estimate_cost(packet)
        return cost

    def get_context_state(self) -> ContextState:
        """Get the current routing context state.

        Returns:
            Current context state.
        """
        return self._context

    def record_routing_result(
        self,
        packet_id: str,
        success: bool,
        actual_cost: CostEstimate | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record the result of a routing operation.

        Args:
            packet_id: The packet ID.
            success: Whether the operation succeeded.
            actual_cost: Actual measured cost.
            metadata: Additional result metadata.
        """
        if actual_cost is not None:
            self._telemetry.record(
                TelemetryRecord(
                    event=TelemetryEvent.COST_MEASURED,
                    timestamp=time.time(),
                    packet_id=packet_id,
                    metadata={
                        "success": success,
                        "actual_cost": actual_cost.value,
                        "currency": actual_cost.currency,
                        "metadata": metadata or {},
                    },
                )
            )
        else:
            self._telemetry.record(
                TelemetryRecord(
                    event=TelemetryEvent.ROUTE_COMPLETE,
                    timestamp=time.time(),
                    packet_id=packet_id,
                    metadata={
                        "success": success,
                        "metadata": metadata or {},
                    },
                )
            )

    def flush_batch(self) -> list[InformationPacket]:
        """Flush the current batch.

        Returns:
            Batched packets.
        """
        # In V2.5, batching is represented by the decision strategy.
        # Actual batching is handled by the adapter/integration layer.
        self._telemetry.record(
            TelemetryRecord(
                event=TelemetryEvent.BATCH_FLUSH,
                timestamp=time.time(),
            )
        )
        return []

    def get_stats(self) -> dict[str, Any]:
        """Get router statistics.

        Returns:
            Router statistics.
        """
        return {
            "uptime_seconds": time.time() - self._started_at,
            "operation_count": self._context.operation_count,
            "cache": self._cache.stats(),
            "telemetry": self._telemetry.get_summary(),
            "provenance_records": self._provenance.count(),
            "registered_destinations": len(self._destinations),
            "registered_policies": len(self._policies),
        }

    def clear(self) -> None:
        """Clear all internal state.

        This is useful for tests and controlled restarts.
        """
        self._cache.clear()
        self._telemetry.clear()
        self._provenance.clear()
        self._context.operation_count = 0
        self._context.deferred_count = 0
        self._context.batch_count = 0
        self._last_decision = None
        self._started_at = time.time()
