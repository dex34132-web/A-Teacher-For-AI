"""Tests for V2.6 memory types.

Covers: MemoryKind, MemoryEntry, MemoryRequest, MemoryResponse.
"""

from __future__ import annotations

import pytest

from core.routing.v26.identity import (
    AgentIdentity,
    MemoryScope,
    ProjectIdentity,
    SessionIdentity,
)
from core.routing.v26.memory_types import (
    MemoryEntry,
    MemoryKind,
    MemoryRequest,
    MemoryResponse,
)


def _make_scope(agent_id: str = "a1", project_id: str = "", session_id: str = "") -> MemoryScope:
    agent = AgentIdentity(agent_id=agent_id)
    project = ProjectIdentity(project_id=project_id) if project_id else None
    session = SessionIdentity(session_id=session_id) if session_id else None
    return MemoryScope(agent=agent, project=project, session=session)


# ---------------------------------------------------------------------------
# MemoryEntry
# ---------------------------------------------------------------------------


class TestMemoryEntry:
    def test_create(self) -> None:
        entry = MemoryEntry.create(
            content="test content",
            kind=MemoryKind.EPISODIC,
            scope=_make_scope(),
        )
        assert entry.content == "test content"
        assert entry.kind == MemoryKind.EPISODIC
        assert entry.memory_id  # auto-generated

    def test_content_length(self) -> None:
        entry = MemoryEntry.create(
            content="hello",
            kind=MemoryKind.WORKING,
            scope=_make_scope(),
        )
        assert entry.content_length == 5

    def test_estimated_tokens(self) -> None:
        entry = MemoryEntry.create(
            content="a" * 40,
            kind=MemoryKind.WORKING,
            scope=_make_scope(),
        )
        assert entry.estimated_tokens == 10

    def test_to_dict_roundtrip(self) -> None:
        entry = MemoryEntry.create(
            content="test",
            kind=MemoryKind.LEARNED,
            scope=_make_scope("a1", "p1", "s1"),
            tags=frozenset({"tag1", "tag2"}),
            confidence=0.8,
        )
        d = entry.to_dict()
        restored = MemoryEntry.from_dict(d)
        assert restored.content == entry.content
        assert restored.kind == entry.kind
        assert restored.tags == entry.tags
        assert restored.confidence == entry.confidence

    def test_from_dict_defaults(self) -> None:
        d: dict = {"memory_id": "m1", "content": "x"}
        entry = MemoryEntry.from_dict(d)
        assert entry.kind == MemoryKind.EPISODIC  # default

    def test_frozen(self) -> None:
        entry = MemoryEntry.create(
            content="x",
            kind=MemoryKind.WORKING,
            scope=_make_scope(),
        )
        with pytest.raises(AttributeError):
            entry.content = "y"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# MemoryRequest
# ---------------------------------------------------------------------------


class TestMemoryRequest:
    def test_validate_valid(self) -> None:
        req = MemoryRequest(
            agent=AgentIdentity(agent_id="a1"),
            query="test query",
        )
        is_valid, reason = req.validate()
        assert is_valid
        assert reason == ""

    def test_validate_empty_query(self) -> None:
        req = MemoryRequest(
            agent=AgentIdentity(agent_id="a1"),
            query="",
        )
        is_valid, reason = req.validate()
        assert not is_valid
        assert "query" in reason

    def test_validate_negative_limit(self) -> None:
        req = MemoryRequest(
            agent=AgentIdentity(agent_id="a1"),
            query="test",
            limit=-1,
        )
        is_valid, _ = req.validate()
        assert not is_valid

    def test_validate_excessive_limit(self) -> None:
        req = MemoryRequest(
            agent=AgentIdentity(agent_id="a1"),
            query="test",
            limit=2000,
        )
        is_valid, _ = req.validate()
        assert not is_valid

    def test_validate_confidence_out_of_range(self) -> None:
        req = MemoryRequest(
            agent=AgentIdentity(agent_id="a1"),
            query="test",
            minimum_confidence=1.5,
        )
        is_valid, _ = req.validate()
        assert not is_valid

    def test_to_scope(self) -> None:
        req = MemoryRequest(
            agent=AgentIdentity(agent_id="a1"),
            query="test",
            project=ProjectIdentity(project_id="p1"),
            session=SessionIdentity(session_id="s1"),
        )
        scope = req.to_scope()
        assert scope.agent.agent_id == "a1"
        assert scope.project is not None
        assert scope.project.project_id == "p1"
        assert scope.session is not None
        assert scope.session.session_id == "s1"


# ---------------------------------------------------------------------------
# MemoryResponse
# ---------------------------------------------------------------------------


class TestMemoryResponse:
    def test_empty_response(self) -> None:
        resp = MemoryResponse()
        assert resp.is_empty
        assert resp.count == 0

    def test_with_memories(self) -> None:
        entry = MemoryEntry.create(
            content="x",
            kind=MemoryKind.WORKING,
            scope=_make_scope(),
        )
        resp = MemoryResponse(memories=(entry,), total=1)
        assert not resp.is_empty
        assert resp.count == 1

    def test_to_dict_roundtrip(self) -> None:
        entry = MemoryEntry.create(
            content="test",
            kind=MemoryKind.EPISODIC,
            scope=_make_scope(),
        )
        resp = MemoryResponse(
            memories=(entry,),
            total=5,
            truncated=True,
            context_cost=100,
            provenance=("m1",),
        )
        d = resp.to_dict()
        restored = MemoryResponse.from_dict(d)
        assert restored.total == 5
        assert restored.truncated is True
        assert restored.context_cost == 100
        assert len(restored.memories) == 1
