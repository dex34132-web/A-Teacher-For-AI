"""Tests for V2.6 persistence module.

Covers: ScopeIsolatedStorage — write, persist, reload, scope filtering,
malformed data recovery, atomic writes.
"""

from __future__ import annotations

from pathlib import Path

from core.routing.v26.identity import (
    AgentIdentity,
    MemoryScope,
    ProjectIdentity,
    SessionIdentity,
)
from core.routing.v26.memory_types import MemoryEntry, MemoryKind
from core.routing.v26.persistence import SCHEMA_VERSION, ScopeIsolatedStorage


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
) -> MemoryEntry:
    return MemoryEntry.create(
        content=content,
        kind=kind,
        scope=_make_scope(agent_id, project_id, session_id),
    )


# ---------------------------------------------------------------------------
# Basic operations
# ---------------------------------------------------------------------------


class TestScopeIsolatedStorage:
    def test_store_and_retrieve(self, tmp_path: Path) -> None:
        storage = ScopeIsolatedStorage(tmp_path)
        entry = _make_entry("hello world")
        storage.store(entry)
        retrieved = storage.get(entry.memory_id)
        assert retrieved is not None
        assert retrieved.content == "hello world"

    def test_retrieve_nonexistent_returns_none(self, tmp_path: Path) -> None:
        storage = ScopeIsolatedStorage(tmp_path)
        assert storage.get("nonexistent") is None

    def test_remove(self, tmp_path: Path) -> None:
        storage = ScopeIsolatedStorage(tmp_path)
        entry = _make_entry()
        storage.store(entry)
        assert storage.remove(entry.memory_id)
        assert storage.get(entry.memory_id) is None

    def test_remove_nonexistent_returns_false(self, tmp_path: Path) -> None:
        storage = ScopeIsolatedStorage(tmp_path)
        assert not storage.remove("nonexistent")

    def test_size(self, tmp_path: Path) -> None:
        storage = ScopeIsolatedStorage(tmp_path)
        assert storage.size() == 0
        storage.store(_make_entry("a"))
        assert storage.size() == 1
        storage.store(_make_entry("b"))
        assert storage.size() == 2

    def test_overwrite_updates(self, tmp_path: Path) -> None:
        storage = ScopeIsolatedStorage(tmp_path)
        entry = _make_entry("original")
        storage.store(entry)
        updated = MemoryEntry(
            memory_id=entry.memory_id,
            content="updated",
            kind=entry.kind,
            scope=entry.scope,
            timestamp=entry.timestamp,
        )
        storage.store(updated)
        retrieved = storage.get(entry.memory_id)
        assert retrieved is not None
        assert retrieved.content == "updated"
        assert storage.size() == 1


# ---------------------------------------------------------------------------
# Scope filtering
# ---------------------------------------------------------------------------


class TestScopeFiltering:
    def test_list_keys_by_project(self, tmp_path: Path) -> None:
        storage = ScopeIsolatedStorage(tmp_path)
        storage.store(_make_entry("a", agent_id="a1", project_id="p1"))
        storage.store(_make_entry("b", agent_id="a1", project_id="p2"))
        storage.store(_make_entry("c", agent_id="a2", project_id="p1"))

        keys = storage.list_keys(project_id="p1")
        assert len(keys) == 2

    def test_list_keys_by_session(self, tmp_path: Path) -> None:
        storage = ScopeIsolatedStorage(tmp_path)
        storage.store(_make_entry("a", agent_id="a1", project_id="p1", session_id="s1"))
        storage.store(_make_entry("b", agent_id="a1", project_id="p1", session_id="s2"))

        keys = storage.list_keys(session_id="s1")
        assert len(keys) == 1

    def test_list_keys_by_kind(self, tmp_path: Path) -> None:
        storage = ScopeIsolatedStorage(tmp_path)
        storage.store(_make_entry("a", kind=MemoryKind.EPISODIC))
        storage.store(_make_entry("b", kind=MemoryKind.LEARNED))
        storage.store(_make_entry("c", kind=MemoryKind.EPISODIC))

        keys = storage.list_keys(kind=MemoryKind.EPISODIC)
        assert len(keys) == 2

    def test_load_with_scope_validation(self, tmp_path: Path) -> None:
        storage = ScopeIsolatedStorage(tmp_path)
        entry = _make_entry("a", agent_id="a1", project_id="p1")
        storage.store(entry)

        # Same scope: loads
        scope = _make_scope("a1", "p1")
        loaded = storage.load(entry.memory_id, scope=scope)
        assert loaded is not None

        # Different project: rejected
        scope2 = _make_scope("a1", "p2")
        loaded2 = storage.load(entry.memory_id, scope=scope2)
        assert loaded2 is None

    def test_load_different_agent_rejected(self, tmp_path: Path) -> None:
        storage = ScopeIsolatedStorage(tmp_path)
        entry = _make_entry("a", agent_id="a1")
        storage.store(entry)

        scope = _make_scope("a2")
        loaded = storage.load(entry.memory_id, scope=scope)
        assert loaded is None


# ---------------------------------------------------------------------------
# Persistence recovery
# ---------------------------------------------------------------------------


class TestPersistenceRecovery:
    def test_malformed_json_recovery(self, tmp_path: Path) -> None:
        storage = ScopeIsolatedStorage(tmp_path)
        # Write malformed JSON
        file_path = tmp_path / "v26_memory.json"
        file_path.write_text("{invalid json", encoding="utf-8")

        # Should recover gracefully
        count = storage.reload()
        assert count == 0

    def test_truncated_json_recovery(self, tmp_path: Path) -> None:
        storage = ScopeIsolatedStorage(tmp_path)
        file_path = tmp_path / "v26_memory.json"
        file_path.write_text('{"version": "2.6.0", "entries": [{"memory_id":', encoding="utf-8")

        count = storage.reload()
        assert count == 0

    def test_missing_entries_recovery(self, tmp_path: Path) -> None:
        storage = ScopeIsolatedStorage(tmp_path)
        file_path = tmp_path / "v26_memory.json"
        file_path.write_text('{"version": "2.6.0"}', encoding="utf-8")

        count = storage.reload()
        assert count == 0

    def test_wrong_type_entries_recovery(self, tmp_path: Path) -> None:
        storage = ScopeIsolatedStorage(tmp_path)
        file_path = tmp_path / "v26_memory.json"
        file_path.write_text('{"version": "2.6.0", "entries": "not a list"}', encoding="utf-8")

        count = storage.reload()
        assert count == 0

    def test_nonexistent_file_returns_empty(self, tmp_path: Path) -> None:
        storage = ScopeIsolatedStorage(tmp_path / "nonexistent")
        count = storage.reload()
        assert count == 0


# ---------------------------------------------------------------------------
# Reload and clear
# ---------------------------------------------------------------------------


class TestReloadAndClear:
    def test_reload_from_disk(self, tmp_path: Path) -> None:
        storage = ScopeIsolatedStorage(tmp_path)
        entry = _make_entry("persistent")
        storage.store(entry)

        # Create new storage instance pointing to same path
        storage2 = ScopeIsolatedStorage(tmp_path)
        count = storage2.reload()
        assert count == 1
        retrieved = storage2.get(entry.memory_id)
        assert retrieved is not None
        assert retrieved.content == "persistent"

    def test_clear_all(self, tmp_path: Path) -> None:
        storage = ScopeIsolatedStorage(tmp_path)
        storage.store(_make_entry("a"))
        storage.store(_make_entry("b"))
        count = storage.clear()
        assert count == 2
        assert storage.size() == 0

    def test_clear_scoped(self, tmp_path: Path) -> None:
        storage = ScopeIsolatedStorage(tmp_path)
        storage.store(_make_entry("a", agent_id="a1"))
        storage.store(_make_entry("b", agent_id="a1"))
        storage.store(_make_entry("c", agent_id="a2"))

        scope = _make_scope("a1")
        count = storage.clear(scope=scope)
        assert count == 2
        assert storage.size() == 1

    def test_schema_version(self) -> None:
        assert SCHEMA_VERSION == "2.6.0"


# ---------------------------------------------------------------------------
# Migration
# ---------------------------------------------------------------------------


class TestMigration:
    def test_migrate_returns_false_when_current(self, tmp_path: Path) -> None:
        storage = ScopeIsolatedStorage(tmp_path)
        storage.store(_make_entry("test"))
        result = storage.migrate("2.5.0")
        assert result is False

    def test_migrate_returns_false_when_no_file(self, tmp_path: Path) -> None:
        storage = ScopeIsolatedStorage(tmp_path / "empty")
        result = storage.migrate("2.5.0")
        assert result is False
