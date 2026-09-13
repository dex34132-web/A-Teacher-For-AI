"""Bridge between V2.6 memory and V2.5 routing/integration.

Connects V2.6 memory operations to the existing V2.5 routing and
integration infrastructure. Uses public APIs only — never accesses
private attributes of V2.5 components.

Design principles:
- Uses public V2.5 APIs exclusively
- Does not create provider-specific connectivity
- Preserves existing V2.5 integration contracts
- V2.6 memory is DATA — never gains instruction priority
"""

from __future__ import annotations

from typing import Any

from core.routing.integration import EVOIntegrationBridge
from core.routing.v26.experience import Experience
from core.routing.v26.identity import AgentIdentity, MemoryScope
from core.routing.v26.memory_manager import MemoryManager
from core.routing.v26.memory_types import MemoryEntry, MemoryKind, MemoryRequest, MemoryResponse


class V26Bridge:
    """Connects V2.6 memory operations to V2.5 routing infrastructure.

    Uses public APIs only. Does not access private attributes of
    V2.5 components.

    No global mutable state — bridge is per-instance.
    """

    def __init__(
        self,
        manager: MemoryManager,
        integration_bridge: EVOIntegrationBridge | None = None,
    ) -> None:
        """Initialize the V2.6 bridge.

        Args:
            manager: V2.6 memory manager.
            integration_bridge: Optional V2.5 integration bridge for routing.
        """
        self._manager = manager
        self._bridge = integration_bridge
        self._handler_count = 0
        self._handler_registered = False

    def request_memory(
        self,
        agent: AgentIdentity,
        query: str,
        project_id: str = "",
        session_id: str = "",
        limit: int = 10,
        context_budget: int = 4096,
        minimum_confidence: float = 0.0,
    ) -> MemoryResponse:
        """Request memory from V2.6 through the bridge.

        This is the primary read interface for agents connecting to EVO.

        Args:
            agent: Requesting agent identity.
            query: Search query.
            project_id: Optional project scope.
            session_id: Optional session scope.
            limit: Maximum memories to return.
            context_budget: Maximum tokens for returned memories.
            minimum_confidence: Minimum confidence threshold.

        Returns:
            MemoryResponse with matching memories.
        """
        from core.routing.v26.identity import ProjectIdentity, SessionIdentity

        project = ProjectIdentity(project_id=project_id) if project_id else None
        session = SessionIdentity(session_id=session_id) if session_id else None

        request = MemoryRequest(
            agent=agent,
            query=query,
            project=project,
            session=session,
            limit=limit,
            context_budget=context_budget,
            minimum_confidence=minimum_confidence,
        )

        return self._manager.request_memory(request)

    def store_experience(
        self,
        experience: Experience,
    ) -> tuple[bool, str]:
        """Store an experience through the bridge.

        Args:
            experience: The experience to store.

        Returns:
            Tuple of (success, reason).
        """
        return self._manager.store_experience(experience)

    def store_memory(
        self,
        entry: MemoryEntry,
        agent: AgentIdentity | None = None,
    ) -> tuple[bool, str]:
        """Store a memory entry through the bridge.

        Args:
            entry: The memory entry to store.
            agent: Optional agent for ownership validation.

        Returns:
            Tuple of (success, reason).
        """
        return self._manager.store_memory(entry, agent=agent)

    def promote_experience(
        self,
        experience: Experience,
    ) -> tuple[bool, str]:
        """Promote an experience to learned knowledge.

        Args:
            experience: The experience to promote.

        Returns:
            Tuple of (success, reason).
        """
        success, reason, _ = self._manager.promote_experience(experience)
        return success, reason

    def connect_to_routing(self) -> None:
        """Connect V2.6 memory as a destination handler in V2.5 routing.

        Registers V2.6 memory operations as handlers for appropriate
        V2.5 destination types.
        """
        if self._bridge is None:
            return

        def memory_handler(packet: Any, decision: Any) -> None:
            """Route EXPERIENCE/KNOWLEDGE packets to V2.6 memory."""
            from core.routing.information import InformationType

            info_type = getattr(packet, "information_type", None)
            if info_type in {
                InformationType.EXPERIENCE,
                InformationType.KNOWLEDGE,
            }:
                content = getattr(packet, "content", "")

                # Create a minimal memory entry
                agent = AgentIdentity(agent_id="routing")
                entry = MemoryEntry.create(
                    content=content,
                    kind=MemoryKind.EPISODIC,
                    scope=MemoryScope(agent=agent),
                    source="routing",
                )
                self._manager.store_memory(entry)
                self._handler_count += 1

        # Register using the public register_handler method
        from core.routing.destinations import DestinationType

        self._bridge.register_handler(DestinationType.LEARNING, memory_handler)
        self._handler_registered = True

    def has_handler(self) -> bool:
        """Check if the bridge has registered handlers."""
        return self._handler_registered

    def stats(self) -> dict[str, Any]:
        """Return bridge statistics."""
        manager_stats = self._manager.stats()
        return {
            **manager_stats,
            "handler_count": self._handler_count,
            "bridge_active": self._bridge is not None,
        }
