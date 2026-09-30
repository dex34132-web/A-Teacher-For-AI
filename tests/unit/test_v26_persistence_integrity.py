"""Regression tests for persistence data-integrity defects (H2 / atomic write).

Root causes under test (proven by forensic investigation of the 2026-09-30
1,373 -> 383 store regression):

H2 — torn/empty read treated as empty state:
  _load_raw() used to swallow JSONDecodeError/OSError/UnicodeDecodeError and
  return {}, so a reader observing a partially-written file would silently
  load an empty store and then rewrite the whole file from that empty base.

Destructive fallback:
  _persist() used to fall back to Path.write_text() (truncate-in-place) when
  os.replace() raised PermissionError on Windows, exposing the live file to
  concurrent readers as empty/partial JSON.

These tests are deterministic unit tests of the fallback/error semantics.
The real Windows file-handle contention path is exercised separately in
tests/integration/test_v26_persistence_concurrency.py.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from core.routing.v26 import persistence as persistence_module
from core.routing.v26.identity import AgentIdentity, MemoryScope
from core.routing.v26.memory_types import MemoryEntry, MemoryKind
from core.routing.v26.persistence import PersistenceError, ScopeIsolatedStorage


def _make_entry(content: str, memory_id: str | None = None) -> MemoryEntry:
    scope = MemoryScope(
        agent=AgentIdentity(agent_id="a1"), project=None, session=None
    )
    base = MemoryEntry.create(content=content, kind=MemoryKind.EPISODIC, scope=scope)
    if memory_id is None:
        return base
    return MemoryEntry(
        memory_id=memory_id,
        content=content,
        kind=base.kind,
        scope=base.scope,
        timestamp=base.timestamp,
    )


def _store_path(base: Path) -> Path:
    return base / "v26_memory.json"


def _seed(base: Path, n: int = 5) -> None:
    storage = ScopeIsolatedStorage(base)
    entries = {
        f"S{i:04d}": _make_entry(f"seed fact {i}", memory_id=f"S{i:04d}")
        for i in range(n)
    }
    storage._persist(entries)


# ---------------------------------------------------------------------------
# Test 3: torn-read / corrupt state must be rejected, never treated as empty
# ---------------------------------------------------------------------------


class TestTornReadRejected:
    def test_empty_file_raises_not_empty_state(self, tmp_path: Path) -> None:
        """An existing zero-byte file is corruption, not an empty store."""
        _store_path(tmp_path).write_bytes(b"")
        storage = ScopeIsolatedStorage(tmp_path)
        with pytest.raises(PersistenceError):
            storage.reload()

    def test_truncated_json_raises_not_empty_state(self, tmp_path: Path) -> None:
        _store_path(tmp_path).write_text(
            '{"version": "2.6.0", "entries": [{"memory_id":', encoding="utf-8"
        )
        storage = ScopeIsolatedStorage(tmp_path)
        with pytest.raises(PersistenceError):
            storage.reload()

    def test_malformed_json_raises_not_empty_state(self, tmp_path: Path) -> None:
        _store_path(tmp_path).write_text("{invalid json", encoding="utf-8")
        storage = ScopeIsolatedStorage(tmp_path)
        with pytest.raises(PersistenceError):
            storage.reload()

    def test_non_object_root_raises_not_empty_state(self, tmp_path: Path) -> None:
        _store_path(tmp_path).write_text("[]", encoding="utf-8")
        storage = ScopeIsolatedStorage(tmp_path)
        with pytest.raises(PersistenceError):
            storage.reload()

    def test_entries_wrong_type_raises_not_empty_state(self, tmp_path: Path) -> None:
        _store_path(tmp_path).write_text(
            '{"version": "2.6.0", "entries": "not a list"}', encoding="utf-8"
        )
        storage = ScopeIsolatedStorage(tmp_path)
        with pytest.raises(PersistenceError):
            storage.reload()

    def test_corrupt_store_rejects_write_never_overwrites(
        self, tmp_path: Path
    ) -> None:
        """store() on a corrupt file must fail loudly, not silently replace it."""
        corrupt = b"{invalid json"
        _store_path(tmp_path).write_bytes(corrupt)
        storage = ScopeIsolatedStorage(tmp_path)
        with pytest.raises(PersistenceError):
            storage.store(_make_entry("should not land"))
        assert _store_path(tmp_path).read_bytes() == corrupt, (
            "corrupt store was modified by a failed write"
        )

    def test_first_get_on_corrupt_store_raises(self, tmp_path: Path) -> None:
        _store_path(tmp_path).write_text("not json at all", encoding="utf-8")
        storage = ScopeIsolatedStorage(tmp_path)
        with pytest.raises(PersistenceError):
            storage.size()


# ---------------------------------------------------------------------------
# Test 4: a genuinely missing file must still initialize normally
# ---------------------------------------------------------------------------


class TestMissingFileInitialization:
    def test_missing_file_initializes_empty(self, tmp_path: Path) -> None:
        storage = ScopeIsolatedStorage(tmp_path / "nonexistent")
        assert storage.reload() == 0
        storage.store(_make_entry("first run"))
        assert storage.size() == 1

    def test_missing_file_first_store_creates_valid_document(
        self, tmp_path: Path
    ) -> None:
        storage = ScopeIsolatedStorage(tmp_path)
        storage.store(_make_entry("boot"))
        data = json.loads(_store_path(tmp_path).read_text(encoding="utf-8"))
        assert data["version"] == persistence_module.SCHEMA_VERSION
        assert isinstance(data["entries"], list)
        assert len(data["entries"]) == 1

    def test_valid_json_without_entries_key_loads_empty(self, tmp_path: Path) -> None:
        """Valid JSON that simply carries no entries list is not corruption."""
        _store_path(tmp_path).write_text('{"version": "2.6.0"}', encoding="utf-8")
        storage = ScopeIsolatedStorage(tmp_path)
        assert storage.reload() == 0


# ---------------------------------------------------------------------------
# Test 5: atomic replacement failure must preserve the old file
# ---------------------------------------------------------------------------


class TestAtomicReplacementFailure:
    def test_replace_failure_raises_and_preserves_old_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Forced os.replace failure: old state intact, no silent fallback."""
        _seed(tmp_path, n=5)
        before = _store_path(tmp_path).read_bytes()

        def _boom(src: str, dst: str) -> None:
            raise PermissionError("simulated Windows share violation")

        monkeypatch.setattr(persistence_module.os, "replace", _boom)
        monkeypatch.setattr(persistence_module, "_REPLACE_ATTEMPTS", 2)
        monkeypatch.setattr(persistence_module, "_REPLACE_INITIAL_DELAY", 0.001)

        storage = ScopeIsolatedStorage(tmp_path)
        with pytest.raises(PersistenceError):
            storage.store(_make_entry("must not land"))

        after = _store_path(tmp_path).read_bytes()
        assert after == before, "old valid file was altered by a failed write"
        leftovers = list(tmp_path.glob("*.tmp"))
        assert leftovers == [], f"temp files left behind: {leftovers}"

    def test_replace_failure_never_truncates_via_write_text(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The destructive Path.write_text fallback must not exist."""
        _seed(tmp_path, n=3)
        before = _store_path(tmp_path).read_bytes()
        write_text_calls: list[str] = []
        real_write_text = Path.write_text

        def _spy(self: Path, *args: object, **kwargs: object) -> int:
            write_text_calls.append(str(self))
            return real_write_text(self, *args, **kwargs)  # type: ignore[arg-type]

        def _boom(src: str, dst: str) -> None:
            raise PermissionError("simulated Windows share violation")

        monkeypatch.setattr(Path, "write_text", _spy)
        monkeypatch.setattr(persistence_module.os, "replace", _boom)
        monkeypatch.setattr(persistence_module, "_REPLACE_ATTEMPTS", 2)
        monkeypatch.setattr(persistence_module, "_REPLACE_INITIAL_DELAY", 0.001)

        storage = ScopeIsolatedStorage(tmp_path)
        with pytest.raises(PersistenceError):
            storage.store(_make_entry("must not land"))

        assert str(_store_path(tmp_path)) not in write_text_calls, (
            "store file was written directly (destructive truncate fallback)"
        )
        assert _store_path(tmp_path).read_bytes() == before

    def test_transient_replace_failure_retries_then_succeeds(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """PermissionError is transient: bounded backoff, then success."""
        storage = ScopeIsolatedStorage(tmp_path)
        storage.store(_make_entry("original", memory_id="E1"))

        real_replace = os.replace
        attempts = {"n": 0}

        def _flaky(src: str, dst: str) -> None:
            attempts["n"] += 1
            if attempts["n"] <= 2:
                raise PermissionError("transient share violation")
            real_replace(src, dst)

        monkeypatch.setattr(persistence_module.os, "replace", _flaky)
        monkeypatch.setattr(persistence_module, "_REPLACE_INITIAL_DELAY", 0.001)

        storage.store(_make_entry("after retry", memory_id="E1"))
        assert attempts["n"] >= 3, "retry path was not exercised"

        fresh = ScopeIsolatedStorage(tmp_path)
        assert fresh.reload() == 1
        landed = fresh.get("E1")
        assert landed is not None
        assert landed.content == "after retry"

    def test_write_fsyncs_temp_before_replace(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Durability: temp file is fsynced before it replaces the target."""
        fsynced: list[int] = []
        real_fsync = os.fsync

        def _spy(fd: int) -> None:
            fsynced.append(fd)
            real_fsync(fd)

        monkeypatch.setattr(persistence_module.os, "fsync", _spy)
        storage = ScopeIsolatedStorage(tmp_path)
        storage.store(_make_entry("durable"))
        assert len(fsynced) >= 1, "no fsync performed before replace"
