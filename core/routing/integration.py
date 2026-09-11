"""Integration bridge between EVO V2.5 and existing V2.4.2 subsystems.

The distinction:
    V2.5 decides WHERE information should go.
    Existing EVO subsystems decide WHAT should happen to that information.

This bridge connects routing destinations to existing V2.4.2 capability
providers without rebuilding them: confidence estimation, conflict
detection, lifecycle management, retrieval, knowledge operations,
provenance, maintenance, and persistence.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from core.routing.decision import RoutingDecision
from core.routing.destinations import DestinationType
from core.routing.information import InformationPacket, InformationType


class BridgeError(Exception):
    """Raised when a destination handler cannot process a packet."""


# ---------------------------------------------------------------------------
# Capability provider protocol — anything the V2.4.2 core exposes
# ---------------------------------------------------------------------------


class CapabilityProvider(Protocol):
    """Minimal structural interface a V2.4.2 subsystem must satisfy.

    Concrete V2.4.2 systems (HybridMemory, LifecycleManager, etc.)
    optionally advertise subset(s) of these methods.
    """

    def add(self, *args: Any, **kwargs: Any) -> Any: ...
    def query(self, *args: Any, **kwargs: Any) -> Any: ...
    def record_event(self, *args: Any, **kwargs: Any) -> Any: ...
    def run_maintenance(self, *args: Any, **kwargs: Any) -> Any: ...
    def reinforce(self, *args: Any, **kwargs: Any) -> Any: ...


# ---------------------------------------------------------------------------
# The bridge
# ---------------------------------------------------------------------------


class EVOIntegrationBridge:
    """Wires routing decisions to V2.4.2 capability providers.

    No global mutable state. The bridge is constructed per-integration
    and holds references to provider callables.
    """

    def __init__(self) -> None:
        """Initialize an empty bridge."""
        self._handlers: dict[
            DestinationType,
            Callable[[InformationPacket, RoutingDecision], None],
        ] = {}
        self._dispatch_count = 0
        self._error_count = 0

    def register_handler(
        self,
        destination_type: DestinationType,
        handler: Callable[[InformationPacket, RoutingDecision], None],
    ) -> None:
        """Register a handler for a destination type.

        Args:
            destination_type: The destination to handle.
            handler: Callable that processes routed packets.
        """
        self._handlers[destination_type] = handler

    def dispatch(
        self,
        packet: InformationPacket,
        decision: RoutingDecision,
    ) -> bool:
        """Dispatch a packet to all destination handlers in the decision.

        Args:
            packet: The information packet.
            decision: The routing decision to execute.

        Returns:
            True if all handlers succeeded, False otherwise.
        """
        all_succeeded = True
        for destination in decision.destinations:
            handler = self._handlers.get(destination.destination_type)
            if handler is None:
                # No handler registered: no-op (V2.5 routes, V2.6 wires)
                self._dispatch_count += 1
                continue

            try:
                handler(packet, decision)
                self._dispatch_count += 1
            except Exception:
                self._error_count += 1
                all_succeeded = False

        return all_succeeded

    # ------------------------------------------------------------------
    # Convenience factories for common V2.4.2 destinations
    # ------------------------------------------------------------------

    def connect_learning_memory(self, memory: Any) -> None:
        """Connect the LEARNING destination to a HybridMemory-like store.

        EXPERIENCE/KNOWLEDGE packets are added to memory.
        """
        def handler(packet: InformationPacket, decision: RoutingDecision) -> None:
            if packet.information_type in {
                InformationType.EXPERIENCE,
                InformationType.KNOWLEDGE,
                InformationType.EVIDENCE,
            } and hasattr(memory, "add"):
                from core.learner.feature_extractor import FeatureVector
                # Create a minimal vector for routing-sourced memories
                vec = FeatureVector(features={}, norm=0.0)
                memory.add(
                    input_text=packet.content,
                    output=packet.content,
                    vector=vec,
                )

        self.register_handler(DestinationType.LEARNING, handler)

    def connect_lifecycle(self, manager: Any) -> None:
        """Connect the LIFECYCLE destination to a LifecycleManager-like object.

        OUTCOME/FEEDBACK packets trigger reinforcement event records.
        """
        def handler(packet: InformationPacket, decision: RoutingDecision) -> None:
            if packet.information_type in {
                InformationType.OUTCOME,
                InformationType.FEEDBACK,
            } and hasattr(manager, "record_event"):
                from core.learner.lifecycle_manager import MaintenanceEvent

                success_meta = packet.metadata.get("success")
                if success_meta is True:
                    manager.record_event(MaintenanceEvent.REPEATED_SUCCESS, memory_id=None)
                elif success_meta is False:
                    manager.record_event(MaintenanceEvent.REPEATED_FAILURE, memory_id=None)

        self.register_handler(DestinationType.LIFECYCLE, handler)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Return bridge usage statistics."""
        return {
            "dispatch_count": self._dispatch_count,
            "error_count": self._error_count,
            "registered_destinations": sorted(
                d.name for d in self._handlers
            ),
        }

    def clear(self) -> None:
        """Clear all handlers and reset counters."""
        self._handlers.clear()
        self._dispatch_count = 0
        self._error_count = 0


def make_noop_handler() -> Callable[[InformationPacket, RoutingDecision], None]:
    """Return a handler that does nothing (for tests and defaults)."""
    def _noop(packet: InformationPacket, decision: RoutingDecision) -> None:
        return None
    return _noop


def make_collector_handler(
    sink: list[InformationPacket],
) -> Callable[[InformationPacket, RoutingDecision], None]:
    """Return a handler that appends packets to a list (for tests)."""
    def _collect(packet: InformationPacket, decision: RoutingDecision) -> None:
        sink.append(packet)
    return _collect
