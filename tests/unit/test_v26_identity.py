"""Tests for V2.6 identity module.

Covers: AgentIdentity, ProjectIdentity, SessionIdentity, MemoryScope.
"""

from __future__ import annotations

import pytest

from core.routing.v26.identity import (
    AgentIdentity,
    MemoryScope,
    ProjectIdentity,
    SessionIdentity,
)

# ---------------------------------------------------------------------------
# AgentIdentity
# ---------------------------------------------------------------------------


class TestAgentIdentity:
    def test_create_with_valid_id(self) -> None:
        agent = AgentIdentity(agent_id="agent-1")
        assert agent.agent_id == "agent-1"

    def test_create_rejects_empty_id(self) -> None:
        with pytest.raises(ValueError, match="agent_id must not be empty"):
            AgentIdentity(agent_id="")

    def test_from_provider_generates_stable_id(self) -> None:
        a1 = AgentIdentity.from_provider("openai", "gpt-4")
        a2 = AgentIdentity.from_provider("openai", "gpt-4")
        assert a1.agent_id == a2.agent_id

    def test_from_provider_different_models_different_ids(self) -> None:
        a1 = AgentIdentity.from_provider("openai", "gpt-4")
        a2 = AgentIdentity.from_provider("openai", "gpt-3.5")
        assert a1.agent_id != a2.agent_id

    def test_to_dict_roundtrip(self) -> None:
        agent = AgentIdentity(
            agent_id="a1", provider="openai", model="gpt-4", adapter="opencode"
        )
        d = agent.to_dict()
        restored = AgentIdentity.from_dict(d)
        assert restored.agent_id == agent.agent_id
        assert restored.provider == agent.provider
        assert restored.model == agent.model
        assert restored.adapter == agent.adapter

    def test_scope_key(self) -> None:
        agent = AgentIdentity(agent_id="a1")
        assert agent.scope_key() == "agent:a1"

    def test_metadata_preserved(self) -> None:
        agent = AgentIdentity(agent_id="a1", metadata={"version": 2})
        d = agent.to_dict()
        assert d["metadata"]["version"] == 2


# ---------------------------------------------------------------------------
# ProjectIdentity
# ---------------------------------------------------------------------------


class TestProjectIdentity:
    def test_create_with_valid_id(self) -> None:
        proj = ProjectIdentity(project_id="proj-1")
        assert proj.project_id == "proj-1"

    def test_create_rejects_empty_id(self) -> None:
        with pytest.raises(ValueError, match="project_id must not be empty"):
            ProjectIdentity(project_id="")

    def test_from_name_generates_stable_id(self) -> None:
        p1 = ProjectIdentity.from_name("my-project", agent_id="a1")
        p2 = ProjectIdentity.from_name("my-project", agent_id="a1")
        assert p1.project_id == p2.project_id

    def test_from_name_different_names_different_ids(self) -> None:
        p1 = ProjectIdentity.from_name("project-a")
        p2 = ProjectIdentity.from_name("project-b")
        assert p1.project_id != p2.project_id

    def test_to_dict_roundtrip(self) -> None:
        proj = ProjectIdentity(project_id="p1", name="Test", agent_id="a1")
        d = proj.to_dict()
        restored = ProjectIdentity.from_dict(d)
        assert restored.project_id == proj.project_id
        assert restored.name == proj.name

    def test_scope_key(self) -> None:
        proj = ProjectIdentity(project_id="p1")
        assert proj.scope_key() == "project:p1"


# ---------------------------------------------------------------------------
# SessionIdentity
# ---------------------------------------------------------------------------


class TestSessionIdentity:
    def test_create_with_valid_id(self) -> None:
        sess = SessionIdentity(session_id="s1")
        assert sess.session_id == "s1"

    def test_create_rejects_empty_id(self) -> None:
        with pytest.raises(ValueError, match="session_id must not be empty"):
            SessionIdentity(session_id="")

    def test_from_context_generates_stable_id(self) -> None:
        s1 = SessionIdentity.from_context("a1", "p1")
        s2 = SessionIdentity.from_context("a1", "p1")
        assert s1.session_id == s2.session_id

    def test_to_dict_roundtrip(self) -> None:
        sess = SessionIdentity(session_id="s1", project_id="p1", agent_id="a1")
        d = sess.to_dict()
        restored = SessionIdentity.from_dict(d)
        assert restored.session_id == sess.session_id

    def test_scope_key(self) -> None:
        sess = SessionIdentity(session_id="s1")
        assert sess.scope_key() == "session:s1"


# ---------------------------------------------------------------------------
# MemoryScope
# ---------------------------------------------------------------------------


class TestMemoryScope:
    def test_agent_only_scope(self) -> None:
        scope = MemoryScope(agent=AgentIdentity(agent_id="a1"))
        key = scope.scope_key()
        assert "agent:a1" in key
        assert "project:" not in key
        assert "session:" not in key

    def test_full_scope(self) -> None:
        scope = MemoryScope(
            agent=AgentIdentity(agent_id="a1"),
            project=ProjectIdentity(project_id="p1"),
            session=SessionIdentity(session_id="s1"),
        )
        key = scope.scope_key()
        assert "agent:a1" in key
        assert "project:p1" in key
        assert "session:s1" in key

    def test_includes_same_agent(self) -> None:
        s1 = MemoryScope(agent=AgentIdentity(agent_id="a1"))
        s2 = MemoryScope(agent=AgentIdentity(agent_id="a1"))
        assert s1.includes(s2)

    def test_excludes_different_agent(self) -> None:
        s1 = MemoryScope(agent=AgentIdentity(agent_id="a1"))
        s2 = MemoryScope(agent=AgentIdentity(agent_id="a2"))
        assert not s1.includes(s2)

    def test_project_scope_includes_matching_project(self) -> None:
        s1 = MemoryScope(
            agent=AgentIdentity(agent_id="a1"),
            project=ProjectIdentity(project_id="p1"),
        )
        s2 = MemoryScope(
            agent=AgentIdentity(agent_id="a1"),
            project=ProjectIdentity(project_id="p1"),
        )
        assert s1.includes(s2)

    def test_project_scope_excludes_different_project(self) -> None:
        s1 = MemoryScope(
            agent=AgentIdentity(agent_id="a1"),
            project=ProjectIdentity(project_id="p1"),
        )
        s2 = MemoryScope(
            agent=AgentIdentity(agent_id="a1"),
            project=ProjectIdentity(project_id="p2"),
        )
        assert not s1.includes(s2)

    def test_session_scope_includes_matching_session(self) -> None:
        s1 = MemoryScope(
            agent=AgentIdentity(agent_id="a1"),
            session=SessionIdentity(session_id="s1"),
        )
        s2 = MemoryScope(
            agent=AgentIdentity(agent_id="a1"),
            session=SessionIdentity(session_id="s1"),
        )
        assert s1.includes(s2)

    def test_session_scope_excludes_different_session(self) -> None:
        s1 = MemoryScope(
            agent=AgentIdentity(agent_id="a1"),
            session=SessionIdentity(session_id="s1"),
        )
        s2 = MemoryScope(
            agent=AgentIdentity(agent_id="a1"),
            session=SessionIdentity(session_id="s2"),
        )
        assert not s1.includes(s2)

    def test_to_dict_roundtrip(self) -> None:
        scope = MemoryScope(
            agent=AgentIdentity(agent_id="a1"),
            project=ProjectIdentity(project_id="p1"),
            session=SessionIdentity(session_id="s1"),
        )
        d = scope.to_dict()
        restored = MemoryScope.from_dict(d)
        assert restored.agent.agent_id == "a1"
        assert restored.project is not None
        assert restored.project.project_id == "p1"
        assert restored.session is not None
        assert restored.session.session_id == "s1"

    def test_from_dict_without_optional_fields(self) -> None:
        d = {"agent": {"agent_id": "a1"}}
        scope = MemoryScope.from_dict(d)
        assert scope.project is None
        assert scope.session is None

    def test_agent_only_scope_includes_agent_with_project(self) -> None:
        """Agent-only scope should include agent+project (no project restriction)."""
        s1 = MemoryScope(agent=AgentIdentity(agent_id="a1"))
        s2 = MemoryScope(
            agent=AgentIdentity(agent_id="a1"),
            project=ProjectIdentity(project_id="p1"),
        )
        assert s1.includes(s2)
