"""Universal Router for EVO V2.5.

The core router orchestrates routing operations. It is agent-agnostic
and does not depend on any specific AI model or agent architecture.

The key principle:
    Let the agent do the semantic thinking.
    Let EVO make the routing structured, efficient, safe, explainable,
    and cheap.
"""

from __future__ import annotations

import time
from typing import Any

from core.routing.cache import RoutingCache
from core.routing.cost import CostEstimate, CostPrecision, CostType, estimate_cost_from_tokens
from core.routing.decision import (
    RoutingDecision,
    RoutingStrategy,
)
from core.routing.destinations import Destination, DestinationType
from core.routing.efficiency import EfficiencyController, EfficiencyDecision
from core.routing.information import (
    InformationPacket,
    InformationType,
    SensitivityLevel,
)
from core.routing.priority import Priority, PriorityConfig
from core.routing.security import enforce_policy
from core.routing.telemetry import (
    TelemetryEvent,
    TelemetryRecord,
    TelemetryRecorder,
)


class RoutingPipeline:
    """The V2.5 routing pipeline.

    Stages (from spec):
    - INPUT → NORMALIZE → CLASSIFY → SCOPE → SAFETY CHECK → PRIORITIZE
    - COST ESTIMATION → ROUTING POLICY → ROUTING DECISION → DESTINATION DISPATCH → TELEMETRY

    Each stage has a clean responsibility. The pipeline as a whole is
    lightweight and agent-agnostic.
    """

    def __init__(
        self,
        efficiency_controller: EfficiencyController | None = None,
        priority_config: PriorityConfig | None = None,
        cache: RoutingCache | None = None,
        security_policy: Any = None,
        telemetry: TelemetryRecorder | None = None,
    ) -> None:
        """Initialize the routing pipeline.

        Args:
            efficiency_controller: For value-vs-cost evaluation.
            priority_config: For priority-based routing decisions.
            cache: For caching routing results.
            security_policy: For instruction/data boundary enforcement.
            telemetry: For structured observability.
        """
        self._efficiency = efficiency_controller or EfficiencyController(
            priority_config=priority_config
        )
        self._priority_config = priority_config or PriorityConfig()
        self._cache = cache or RoutingCache()
        self._security_policy = security_policy
        self._telemetry = telemetry or TelemetryRecorder()
        self._stage_latencies: dict[str, float] = {}

    def _record_stage_latency(self, stage: str, latency: float) -> None:
        """Record latency for a pipeline stage."""
        self._stage_latencies[stage] = self._stage_latencies.get(stage, 0.0) + latency
        self._telemetry.record(
            TelemetryRecord(
                event=TelemetryEvent.ROUTE_COMPLETE,
                timestamp=time.time(),
                latency_ms=latency,
            )
        )

    def _telemetry_record(self, record: TelemetryRecord) -> None:
        """Record a telemetry event."""
        self._telemetry.record(record)

    def normalize(self, packet: InformationPacket) -> InformationPacket:
        """Stage 1: Normalize the information packet.

        Ensures consistent format across different agent interfaces.
        """
        # Normalize sensitivity to UNKNOWN if not set
        sensitivity = packet.sensitivity
        if sensitivity == SensitivityLevel.UNKNOWN:
            # Default based on information type
            if packet.information_type == InformationType.INSTRUCTION:
                sensitivity = SensitivityLevel.PROJECT
            else:
                sensitivity = SensitivityLevel.PUBLIC

        # Normalize confidence range
        confidence = max(0.0, min(1.0, packet.confidence))

        return InformationPacket(
            id=packet.id,
            content=packet.content,
            information_type=packet.information_type,
            source=packet.source,
            scope=packet.scope,
            timestamp=packet.timestamp,
            priority=packet.priority,
            sensitivity=sensitivity,
            confidence=confidence,
            cost_estimate=packet.cost_estimate,
            provenance=packet.provenance,
            metadata=packet.metadata,
            tags=packet.tags,
            parent_id=packet.parent_id,
        )

    def classify(self, packet: InformationPacket) -> InformationPacket:
        """Stage 2: Classify the information type.

        Ensures consistent type encoding across agents.
        """
        info_type = packet.information_type
        # Re-classify UNKNOWN types based on content hints
        if info_type == InformationType.UNKNOWN:
            lower = packet.content.lower()
            if lower.startswith(("ignore", "disregard", "forget")):
                info_type = InformationType.INSTRUCTION
            elif any(kw in lower for kw in ["observation:", "result:", "output:"]):
                info_type = InformationType.OBSERVATION
            elif any(kw in lower for kw in ["task:", "need:", "require:"]):
                info_type = InformationType.TASK
            else:
                info_type = InformationType.CONTEXT

        return InformationPacket(
            id=packet.id,
            content=packet.content,
            information_type=info_type,
            source=packet.source,
            scope=packet.scope,
            timestamp=packet.timestamp,
            priority=packet.priority,
            sensitivity=packet.sensitivity,
            confidence=packet.confidence,
            cost_estimate=packet.cost_estimate,
            provenance=packet.provenance,
            metadata=packet.metadata,
            tags=packet.tags,
            parent_id=packet.parent_id,
        )

    def scope(self, packet: InformationPacket, context: Any | None = None) -> InformationPacket:
        """Stage 3: Determine the scope of the information.

        Scoping enables isolation and targeted routing.
        """
        # Scope already set on packet; ensure consistency
        # In V2.5, scope is managed by the agent
        return InformationPacket(
            id=packet.id,
            content=packet.content,
            information_type=packet.information_type,
            source=packet.source,
            scope=packet.scope or "default",
            timestamp=packet.timestamp,
            priority=packet.priority,
            sensitivity=packet.sensitivity,
            confidence=packet.confidence,
            cost_estimate=packet.cost_estimate,
            provenance=packet.provenance,
            metadata=packet.metadata,
            tags=packet.tags,
            parent_id=packet.parent_id,
        )

    def safety_check(self, packet: InformationPacket) -> tuple[InformationPacket, bool, str]:
        """Stage 4: Security and policy check.

        Verifies instruction/data boundaries, sensitivity, injection patterns.
        Returns (packet, allowed, reason).
        """
        if self._security_policy is not None:
            allowed, reason = enforce_policy(packet, self._security_policy)
        else:
            allowed, reason = True, ""

        if not allowed:
            self._telemetry_record(
                TelemetryRecord(
                    event=TelemetryEvent.SECURITY_BLOCK,
                    timestamp=time.time(),
                    packet_id=packet.id,
                    destinations=("discard",),
                    metadata={"reason": reason},
                )
            )
            return packet, False, reason

        return packet, True, reason

    def prioritize(self, packet: InformationPacket) -> InformationPacket:
        """Stage 5: Apply priority-based routing.

        Priority influences processing order and deferral decisions.
        """
        # Apply priority config if available
        priority = Priority.from_int(packet.priority)
        priority = self._priority_config.apply_boost(priority)
        packet = InformationPacket(
            id=packet.id,
            content=packet.content,
            information_type=packet.information_type,
            source=packet.source,
            scope=packet.scope,
            timestamp=packet.timestamp,
            priority=priority.value,
            sensitivity=packet.sensitivity,
            confidence=packet.confidence,
            cost_estimate=packet.cost_estimate,
            provenance=packet.provenance,
            metadata=packet.metadata,
            tags=packet.tags,
            parent_id=packet.parent_id,
        )

        return packet

    def estimate_cost(self, packet: InformationPacket) -> tuple[InformationPacket, CostEstimate]:
        """Stage 6: Estimate routing cost.

        Explicitly treats agent interaction as a resource.
        """
        # Use agent-provided cost estimate if available
        if packet.cost_estimate is not None:
            cost = CostEstimate(
                cost_type=CostType.TOKEN,
                value=float(packet.cost_estimate),
                precision=CostPrecision.MEASURED,
                currency="agent_units",
            )
        else:
            # Estimate from content length
            cost = estimate_cost_from_tokens(
                packet.estimated_tokens,
                cost_per_1k_tokens=0.001,
            )

        return packet, cost

    def route(
        self,
        packet: InformationPacket,
        context: Any | None = None,
        policy: Any | None = None,
    ) -> RoutingDecision:
        """Stage 7-9: Route the information.

        Execute the full routing pipeline and return a RoutingDecision.
        """
        start = time.time()

        # Stage 1: Normalize
        packet = self.normalize(packet)
        n_latency = time.time() - start

        # Stage 2: Classify
        packet = self.classify(packet)
        c_latency = time.time() - start - n_latency

        # Stage 3: Scope
        packet = self.scope(packet, context)
        s_latency = time.time() - start - n_latency - c_latency

        # Stage 4: Safety check
        packet, allowed, reason = self.safety_check(packet)
        sc_latency = time.time() - start - n_latency - c_latency - s_latency

        if not allowed:
            return RoutingDecision(
                packet_id=packet.id,
                destinations=(Destination(destination_type=DestinationType.DISCARD),),
                strategy=RoutingStrategy.DISCARD,
                reason=f"Security policy blocked: {reason}",
                confidence=1.0,
                priority=packet.priority,
                cost_estimates=(CostEstimate(cost_type=CostType.PROCESSING, value=0.0),),
                policy_applied="security_policy",
                rejected=True,
                rejection_reason=reason,
            )

        # Stage 5: Prioritize
        packet = self.prioritize(packet)
        p_latency = time.time() - start - n_latency - c_latency - s_latency - sc_latency

        # Stage 6: Cost estimation
        packet, cost = self.estimate_cost(packet)
        est_latency = (
            time.time() - start - n_latency - c_latency - s_latency - sc_latency - p_latency
        )

        # Stage 7: Efficiency evaluation
        eff_start = time.time()
        efficiency_decision = self._efficiency.evaluate(packet)
        eff_latency = time.time() - eff_start

        # Stage 8: Routing policy
        routing_start = time.time()

        # Determine routing decision based on efficiency and priority
        decision = self._build_decision(
            packet=packet,
            cost=cost,
            efficiency_decision=efficiency_decision,
            policy=policy,
        )

        routing_latency = time.time() - routing_start

        # Stage 9: Dispatch and telemetry
        self._dispatch(decision=decision, packet=packet)

        # Record stage latencies
        self._record_stage_latency("total", time.time() - start)
        self._record_stage_latency("normalize", n_latency)
        self._record_stage_latency("classify", c_latency)
        self._record_stage_latency("scope", s_latency)
        self._record_stage_latency("safety_check", sc_latency)
        self._record_stage_latency("prioritize", p_latency)
        self._record_stage_latency("estimate_cost", est_latency)
        self._record_stage_latency("efficiency", eff_latency)
        self._record_stage_latency("routing_policy", routing_latency)

        return decision

    def _build_decision(
        self,
        packet: InformationPacket,
        cost: CostEstimate,
        efficiency_decision: EfficiencyDecision,
        policy: Any | None = None,
    ) -> RoutingDecision:
        """Build the RoutingDecision based on all evaluations.

        Agent-agnostic: routing strategies are generic, not model-specific.
        """
        # Base routing logic
        strategy = RoutingStrategy.DIRECT
        destinations: tuple[Destination, ...] = ()
        deferred = False
        rejected = False
        reason = ""
        final_priority = packet.priority

        if efficiency_decision == EfficiencyDecision.REJECT:
            rejected = True
            reason = "Efficiency threshold not met"
            strategy = RoutingStrategy.DISCARD
            final_priority = Priority.BACKGROUND.value

        elif efficiency_decision == EfficiencyDecision.DEFER:
            deferred = True
            reason = "Operation deferred based on efficiency analysis"
            strategy = RoutingStrategy.DEFERRED

        elif efficiency_decision == EfficiencyDecision.BATCH:
            strategy = RoutingStrategy.BATCHED

        elif efficiency_decision == EfficiencyDecision.SIMPLIFY:
            reason = "Content simplified due to size"
            # Route to learning with simplified representation
            strategy = RoutingStrategy.DIRECT
            destinations = (Destination(destination_type=DestinationType.LEARNING),)

        else:  # EXECUTE
            # Determine best destination based on information type
            itype = packet.information_type
            pc = packet.priority

            if itype in {
                InformationType.INSTRUCTION,
                InformationType.TASK,
            }:
                strategy = RoutingStrategy.DIRECT
                if pc <= Priority.HIGH.value:
                    destinations = (Destination(destination_type=DestinationType.AGENT_CONTEXT),)
                else:
                    destinations = (Destination(destination_type=DestinationType.EVO_CONTEXT),)

            elif itype == InformationType.OUTCOME:
                strategy = RoutingStrategy.DIRECT
                destinations = (Destination(destination_type=DestinationType.PROVENANCE),)

            elif itype in {
                InformationType.OBSERVATION,
                InformationType.DATA,
                InformationType.CONTEXT,
            }:
                strategy = RoutingStrategy.DIRECT
                destinations = (Destination(destination_type=DestinationType.RETRIEVAL),)

            elif itype == InformationType.FEEDBACK:
                strategy = RoutingStrategy.DIRECT
                destinations = (Destination(destination_type=DestinationType.CONFIDENCE),)

            elif itype == InformationType.EVIDENCE:
                strategy = RoutingStrategy.DIRECT
                destinations = (Destination(destination_type=DestinationType.KNOWLEDGE),)

            else:
                strategy = RoutingStrategy.DIRECT
                destinations = (Destination(destination_type=DestinationType.EVO_CONTEXT),)

        # Apply priority from config
        if policy and hasattr(policy, 'apply_priority'):
            final_priority = policy.apply_priority(int(packet.priority))
        else:
            final_priority = int(packet.priority)

        # Build the decision
        decision = RoutingDecision(
            packet_id=packet.id,
            destinations=destinations,
            strategy=strategy,
            confidence=packet.confidence,
            reason=reason,
            priority=final_priority,
            cost_estimates=(cost,),
            policy_applied=policy.name if policy else "",
            deferred=deferred,
            rejected=rejected,
            rejection_reason=reason if rejected else "",
            metadata={
                "information_type": packet.information_type.name,
                "efficiency_decision": efficiency_decision.name,
                "estimated_tokens": packet.estimated_tokens,
            },
        )

        return decision

    def _dispatch(self, decision: RoutingDecision, packet: InformationPacket) -> None:
        """Dispatch to destinations and record telemetry.

        In V2.5, dispatch is conceptual - the decision describes where
        information should go. Actual dispatch is handled by the agent
        or integration layer.
        """
        timestamp = time.time()

        # Record telemetry for each destination
        for destination in decision.destinations:
            self._telemetry_record(
                TelemetryRecord(
                    event=TelemetryEvent.DESTINATION_DISPATCH,
                    timestamp=timestamp,
                    packet_id=packet.id,
                    destinations=(destination.name,),
                    metadata={
                        "strategy": decision.strategy.name,
                        "confidence": decision.confidence,
                        "cost": decision.total_estimated_cost,
                        "deferred": decision.deferred,
                        "rejected": decision.rejected,
                    },
                )
            )

        # Record cost estimation
        if decision.has_cost:
            self._telemetry_record(
                TelemetryRecord(
                    event=TelemetryEvent.COST_ESTIMATED,
                    timestamp=timestamp,
                    packet_id=packet.id,
                    latency_ms=decision.total_estimated_cost * 10,  # rough proxy
                    destinations=tuple(d.name for d in decision.destination_types()),
                    metadata={
                        "estimated_cost": decision.total_estimated_cost,
                        "currency": (
                            decision.cost_estimates[0].currency if decision.cost_estimates else ""
                        ),
                    },
                )
            )

    def get_stats(self) -> dict[str, Any]:
        """Get pipeline statistics."""
        route_starts = (
            self._telemetry.get_counter("ROUTE_START")
            if hasattr(self._telemetry, 'get_counter')
            else 0
        )
        return {
            "cache_stats": self._cache.stats(),
            "telemetry_summary": self._telemetry.get_summary(),
            "total_operations": route_starts,
            "latency_breakdown": getattr(self, '_stage_latencies', {}),
        }

    def clear(self) -> None:
        """Clear all internal state."""
        self._cache.clear()
        self._telemetry.clear()
        self._stage_latencies.clear()
