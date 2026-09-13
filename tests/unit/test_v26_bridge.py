"""Tests for V2.6 memory bridge.

Covers: V26Bridge — memory requests, experience storage, routing integration.
"""

from __future__ import annotations

from core.routing.integration import EVOIntegrationBridge
from core.routing.v26.experience import Experience, ExperienceOutcome
from core.routing.v26.identity import AgentIdentity, MemoryScope, ProjectIdentity, SessionIdentity
from core.routing.v26.memory_bridge import V26Bridge
from core.routing.v26.memory_manager import MemoryManager
from core.routing.v26.memory_types import MemoryEntry, MemoryKind


def _make_agent(agent_id: str = "a1") -> AgentIdentity:
    return AgentIdentity(agent_id=agent_id)


# ---------------------------------------------------------------------------
# Basic bridge operations
# ---------------------------------------------------------------------------


class TestV26Bridge:
    def test_request_memory(self) -> None:
        manager = MemoryManager()
        bridge = V26Bridge(manager)
        manager.store_memory(
            MemoryEntry.create(
                content="test memory",
                kind=MemoryKind.EPISODIC,
                scope=MemoryScope(agent=AgentIdentity(agent_id="bridge-agent")),
            )
        )
        response = bridge.request_memory(
            agent=_make_agent("bridge-agent"),
            query="test",
        )
        assert response.count == 1

    def test_store_experience(self) -> None:
        manager = MemoryManager()
        bridge = V26Bridge(manager)
        exp = Experience.create(
            agent=_make_agent(),
            observation="test observation",
            outcome=ExperienceOutcome.SUCCESS,
        )
        success, reason = bridge.store_experience(exp)
        assert success

    def test_store_memory(self) -> None:
        manager = MemoryManager()
        bridge = V26Bridge(manager)
        entry = MemoryEntry.create(
            content="bridge stored",
            kind=MemoryKind.EPISODIC,
            scope=MemoryScope(agent=AgentIdentity(agent_id="bridge-agent")),
        )
        success, reason = bridge.store_memory(entry)
        assert success

    def test_promote_experience(self) -> None:
        manager = MemoryManager()
        bridge = V26Bridge(manager)
        exp = Experience.create(
            agent=_make_agent(),
            observation="promotable",
            outcome=ExperienceOutcome.SUCCESS,
            confidence=0.9,
        )
        success, reason = bridge.promote_experience(exp)
        assert success

    def test_stats(self) -> None:
        manager = MemoryManager()
        bridge = V26Bridge(manager)
        stats = bridge.stats()
        assert "store_size" in stats
        assert "handler_count" in stats
        assert "bridge_active" in stats


# ---------------------------------------------------------------------------
# Routing integration
# ---------------------------------------------------------------------------


class TestV26BridgeRouting:
    def test_connect_to_routing(self) -> None:
        manager = MemoryManager()
        integration = EVOIntegrationBridge()
        bridge = V26Bridge(manager, integration_bridge=integration)
        bridge.connect_to_routing()
        assert bridge.has_handler()

    def test_bridge_without_routing(self) -> None:
        manager = MemoryManager()
        bridge = V26Bridge(manager)
        # Should not crash
        bridge.connect_to_routing()
        assert not bridge.has_handler()


# ---------------------------------------------------------------------------
# Scope-aware requests
# ---------------------------------------------------------------------------


class TestV26BridgeScope:
    def test_project_scoped_request(self) -> None:
        manager = MemoryManager()
        bridge = V26Bridge(manager)
        manager.store_memory(
            MemoryEntry.create(
                content="project memory",
                kind=MemoryKind.EPISODIC,
                scope=MemoryScope(
                    agent=AgentIdentity(agent_id="a1"),
                    project=ProjectIdentity(project_id="p1"),
                ),
            )
        )
        response = bridge.request_memory(
            agent=_make_agent("a1"),
            query="project",
            project_id="p1",
        )
        assert response.count == 1

    def test_session_scoped_request(self) -> None:
        manager = MemoryManager()
        bridge = V26Bridge(manager)
        manager.store_memory(
            MemoryEntry.create(
                content="session memory",
                kind=MemoryKind.EPISODIC,
                scope=MemoryScope(
                    agent=AgentIdentity(agent_id="a1"),
                    project=ProjectIdentity(project_id="p1"),
                    session=SessionIdentity(session_id="s1"),
                ),
            )
        )
        response = bridge.request_memory(
            agent=_make_agent("a1"),
            query="session",
            project_id="p1",
            session_id="s1",
        )
        assert response.count == 1
