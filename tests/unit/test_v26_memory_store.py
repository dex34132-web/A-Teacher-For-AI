"""Tests for V2.6 memory store module.

Covers: MemoryStore — store, query, scope filtering, eviction, clear.
"""

from __future__ import annotations

from core.routing.v26.identity import (
    AgentIdentity,
    MemoryScope,
    ProjectIdentity,
    SessionIdentity,
)
from core.routing.v26.memory_store import MemoryStore
from core.routing.v26.memory_types import MemoryEntry, MemoryKind


def _make_scope(agent_id: str = "a1", project_id: str = "", session_id: str = "") -> MemoryScope:
    agent = AgentIdentity(agent_id=agent_id)
    project = ProjectIdentity(project_id=project_id) if project_id else None
    session = SessionIdentity(session_id=session_id) if session_id else None
    return MemoryScope(agent=agent, project=project, session=session)


def _make_entry(
    content: str = "test",
    agent_id: str = "a1",
    project_id: str = "",
    session_id: str = "",
    kind: MemoryKind = MemoryKind.EPISODIC,
    confidence: float = 0.5,
    tags: frozenset[str] | None = None,
) -> MemoryEntry:
    return MemoryEntry.create(
        content=content,
        kind=kind,
        scope=_make_scope(agent_id, project_id, session_id),
        confidence=confidence,
        tags=tags or frozenset(),
    )


# ---------------------------------------------------------------------------
# Basic operations
# ---------------------------------------------------------------------------


class TestMemoryStore:
    def test_store_and_get(self) -> None:
        store = MemoryStore()
        entry = _make_entry("hello")
        store.store(entry)
        retrieved = store.get(entry.memory_id)
        assert retrieved is not None
        assert retrieved.content == "hello"

    def test_get_nonexistent(self) -> None:
        store = MemoryStore()
        assert store.get("nonexistent") is None

    def test_remove(self) -> None:
        store = MemoryStore()
        entry = _make_entry()
        store.store(entry)
        assert store.remove(entry.memory_id)
        assert store.get(entry.memory_id) is None

    def test_remove_nonexistent(self) -> None:
        store = MemoryStore()
        assert not store.remove("nonexistent")

    def test_size(self) -> None:
        store = MemoryStore()
        assert store.size == 0
        store.store(_make_entry("a"))
        assert store.size == 1

    def test_is_empty(self) -> None:
        store = MemoryStore()
        assert store.is_empty
        store.store(_make_entry())
        assert not store.is_empty

    def test_all_ids(self) -> None:
        store = MemoryStore()
        e1 = _make_entry("a")
        e2 = _make_entry("b")
        store.store(e1)
        store.store(e2)
        ids = store.all_ids()
        assert e1.memory_id in ids
        assert e2.memory_id in ids


# ---------------------------------------------------------------------------
# Query filtering
# ---------------------------------------------------------------------------


class TestQuery:
    def test_query_all(self) -> None:
        store = MemoryStore()
        store.store(_make_entry("a"))
        store.store(_make_entry("b"))
        results = store.query()
        assert len(results) == 2

    def test_query_by_scope(self) -> None:
        store = MemoryStore()
        store.store(_make_entry("a", agent_id="a1"))
        store.store(_make_entry("b", agent_id="a2"))
        scope = _make_scope("a1")
        results = store.query(scope=scope)
        assert len(results) == 1
        assert results[0].scope.agent.agent_id == "a1"

    def test_query_by_kind(self) -> None:
        store = MemoryStore()
        store.store(_make_entry("a", kind=MemoryKind.EPISODIC))
        store.store(_make_entry("b", kind=MemoryKind.LEARNED))
        results = store.query(kind=MemoryKind.EPISODIC)
        assert len(results) == 1

    def test_query_by_confidence(self) -> None:
        store = MemoryStore()
        store.store(_make_entry("a", confidence=0.3))
        store.store(_make_entry("b", confidence=0.8))
        results = store.query(minimum_confidence=0.5)
        assert len(results) == 1
        assert results[0].confidence >= 0.5

    def test_query_by_text(self) -> None:
        store = MemoryStore()
        store.store(_make_entry("Python is great"))
        store.store(_make_entry("JavaScript is fast"))
        results = store.query(query_text="Python")
        assert len(results) == 1
        assert "Python" in results[0].content

    def test_query_by_tags(self) -> None:
        store = MemoryStore()
        store.store(_make_entry("a", tags=frozenset({"tag1", "tag2"})))
        store.store(_make_entry("b", tags=frozenset({"tag1"})))
        results = store.query(tags=frozenset({"tag1"}))
        assert len(results) == 2

    def test_query_by_tags_requires_all(self) -> None:
        store = MemoryStore()
        store.store(_make_entry("a", tags=frozenset({"tag1", "tag2"})))
        store.store(_make_entry("b", tags=frozenset({"tag1"})))
        results = store.query(tags=frozenset({"tag1", "tag2"}))
        assert len(results) == 1

    def test_query_limit(self) -> None:
        store = MemoryStore()
        for i in range(10):
            store.store(_make_entry(f"item {i}"))
        results = store.query(limit=3)
        assert len(results) == 3

    def test_query_project_filter(self) -> None:
        store = MemoryStore()
        store.store(_make_entry("a", agent_id="a1", project_id="p1"))
        store.store(_make_entry("b", agent_id="a1", project_id="p2"))
        scope = _make_scope("a1", "p1")
        results = store.query(scope=scope)
        assert len(results) == 1

    def test_query_session_filter(self) -> None:
        store = MemoryStore()
        store.store(_make_entry("a", agent_id="a1", project_id="p1", session_id="s1"))
        store.store(_make_entry("b", agent_id="a1", project_id="p1", session_id="s2"))
        scope = _make_scope("a1", "p1", "s1")
        results = store.query(scope=scope)
        assert len(results) == 1


# ---------------------------------------------------------------------------
# Eviction
# ---------------------------------------------------------------------------


class TestEviction:
    def test_evicts_oldest_when_over_capacity(self) -> None:
        store = MemoryStore(max_entries=3)
        e1 = _make_entry("first")
        e2 = _make_entry("second")
        e3 = _make_entry("third")
        e4 = _make_entry("fourth")
        store.store(e1)
        store.store(e2)
        store.store(e3)
        store.store(e4)
        assert store.size == 3
        assert store.get(e1.memory_id) is None  # evicted
        assert store.get(e4.memory_id) is not None  # kept


# ---------------------------------------------------------------------------
# Clear
# ---------------------------------------------------------------------------


class TestClear:
    def test_clear_all(self) -> None:
        store = MemoryStore()
        store.store(_make_entry("a"))
        store.store(_make_entry("b"))
        count = store.clear()
        assert count == 2
        assert store.is_empty

    def test_clear_scoped(self) -> None:
        store = MemoryStore()
        store.store(_make_entry("a", agent_id="a1"))
        store.store(_make_entry("b", agent_id="a1"))
        store.store(_make_entry("c", agent_id="a2"))
        scope = _make_scope("a1")
        count = store.clear(scope=scope)
        assert count == 2
        assert store.size == 1
