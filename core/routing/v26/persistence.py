"""Persistent storage for Lerev V2.6 long-term memory.

Provides scope-isolated, versioned, atomic JSON persistence for
V2.6 memory entries. Handles malformed/truncated state safely.

Design principles:
- Atomic writes (no corrupted primary state after interrupted writes)
- Recovery from malformed/truncated state
- Schema version tracking for future migration
- Scope isolation preserved across persistence
- Cross-session queries without weakening isolation
- No global mutable state
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from core.routing.v26.identity import MemoryScope
from core.routing.v26.memory_types import MemoryEntry, MemoryKind

# Current schema version
SCHEMA_VERSION = "2.6.0"


# ---------------------------------------------------------------------------
# ScopeIsolatedStorage
# ---------------------------------------------------------------------------


class ScopeIsolatedStorage:
    """JSON-based persistent storage with scope isolation.

    Memories are stored in a flat list within a single JSON file,
    with scope fields enabling filtering. This avoids directory sprawl
    while maintaining logical isolation.

    No global mutable state — storage is per-instance.
    """

    def __init__(self, base_path: Path, max_entries: int = 100_000) -> None:
        """Initialize storage.

        Args:
            base_path: Base directory for storage files.
            max_entries: Maximum entries to store before warning.
        """
        self._base_path = base_path
        self._max_entries = max_entries
        self._file_path = base_path / "v26_memory.json"
        self._cache: dict[str, MemoryEntry] | None = None

    def _ensure_dir(self) -> None:
        """Ensure the storage directory exists."""
        self._base_path.mkdir(parents=True, exist_ok=True)

    def _load_raw(self) -> dict[str, Any]:
        """Load raw data from disk, handling malformed state."""
        if not self._file_path.exists():
            return {"version": SCHEMA_VERSION, "entries": []}

        try:
            text = self._file_path.read_text(encoding="utf-8")
            data = json.loads(text)
            if not isinstance(data, dict):
                return {"version": SCHEMA_VERSION, "entries": []}
            # Ensure entries is a list
            if "entries" not in data or not isinstance(data["entries"], list):
                data["entries"] = []
            return data
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            # Malformed file: return empty state
            return {"version": SCHEMA_VERSION, "entries": []}

    def _load_entries(self) -> dict[str, MemoryEntry]:
        """Load all entries into a dict keyed by memory_id."""
        data = self._load_raw()
        entries: dict[str, MemoryEntry] = {}
        for raw in data.get("entries", []):
            try:
                entry = MemoryEntry.from_dict(raw)
                if entry.memory_id:
                    entries[entry.memory_id] = entry
            except (KeyError, ValueError, TypeError):
                continue  # Skip malformed entries
        return entries

    def _get_cache(self) -> dict[str, MemoryEntry]:
        """Get or build the in-memory cache."""
        if self._cache is None:
            self._cache = self._load_entries()
        return self._cache

    def _persist(self, entries: dict[str, MemoryEntry]) -> None:
        """Persist entries to disk with atomic write."""
        self._ensure_dir()

        data = {
            "version": SCHEMA_VERSION,
            "entries": [e.to_dict() for e in entries.values()],
        }
        raw = json.dumps(data, indent=2, ensure_ascii=False)

        # Atomic write: write to temp file, then rename
        # On Windows, os.replace may fail if file is open; fall back to direct write
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=self._base_path, suffix=".tmp"
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                f.write(raw)
            # Atomic rename (on same filesystem)
            try:
                os.replace(tmp_path, self._file_path)
            except PermissionError:
                # Windows fallback: direct write
                self._file_path.write_text(raw, encoding="utf-8")
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
        except Exception:
            # Clean up temp file on failure
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

        self._cache = entries

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def store(self, entry: MemoryEntry) -> None:
        """Store a memory entry (create or update)."""
        cache = self._get_cache()
        cache[entry.memory_id] = entry
        self._persist(cache)

    def get(self, memory_id: str) -> MemoryEntry | None:
        """Retrieve a memory entry by ID."""
        cache = self._get_cache()
        return cache.get(memory_id)

    def remove(self, memory_id: str) -> bool:
        """Remove a memory entry by ID."""
        cache = self._get_cache()
        if memory_id not in cache:
            return False
        del cache[memory_id]
        self._persist(cache)
        return True

    def list_keys(
        self,
        scope: MemoryScope | None = None,
        kind: MemoryKind | None = None,
        project_id: str | None = None,
        session_id: str | None = None,
    ) -> list[str]:
        """List memory IDs with optional filtering.

        Args:
            scope: If provided, filter by scope (exact or parent match).
            kind: If provided, filter by memory kind.
            project_id: If provided, filter by project.
            session_id: If provided, filter by session.

        Returns:
            List of matching memory IDs.
        """
        cache = self._get_cache()
        results: list[str] = []

        for entry in cache.values():
            # Kind filter
            if kind is not None and entry.kind != kind:
                continue

            # Project filter
            if project_id and (
                entry.scope.project is None
                or entry.scope.project.project_id != project_id
            ):
                continue

            # Session filter
            if session_id and (
                entry.scope.session is None
                or entry.scope.session.session_id != session_id
            ):
                continue

            # Scope filter (if provided, entry must be within the scope)
            if scope is not None:
                if entry.scope.agent.agent_id != scope.agent.agent_id:
                    continue
                if scope.project and scope.project.project_id:
                    if (
                        entry.scope.project is None
                        or entry.scope.project.project_id != scope.project.project_id
                    ):
                        continue
                if scope.session and scope.session.session_id:
                    if (
                        entry.scope.session is None
                        or entry.scope.session.session_id != scope.session.session_id
                    ):
                        continue

            results.append(entry.memory_id)

        return results

    def load(
        self,
        memory_id: str,
        scope: MemoryScope | None = None,
    ) -> MemoryEntry | None:
        """Load a specific memory with optional scope validation.

        Args:
            memory_id: The memory ID to load.
            scope: If provided, validate scope access.

        Returns:
            MemoryEntry if found and scope-valid, None otherwise.
        """
        entry = self.get(memory_id)
        if entry is None:
            return None

        if scope is not None:
            if entry.scope.agent.agent_id != scope.agent.agent_id:
                return None
            if scope.project and scope.project.project_id:
                if (
                    entry.scope.project is None
                    or entry.scope.project.project_id != scope.project.project_id
                ):
                    return None

        return entry

    def count(
        self,
        scope: MemoryScope | None = None,
        kind: MemoryKind | None = None,
    ) -> int:
        """Count entries with optional filtering."""
        return len(self.list_keys(scope=scope, kind=kind))

    def clear(
        self,
        scope: MemoryScope | None = None,
    ) -> int:
        """Clear entries, optionally scoped.

        Args:
            scope: If provided, only clear entries within scope.

        Returns:
            Number of entries cleared.
        """
        cache = self._get_cache()

        if scope is None:
            count = len(cache)
            self._persist({})
            return count

        to_remove = []
        for mid, entry in cache.items():
            if entry.scope.agent.agent_id != scope.agent.agent_id:
                continue
            if scope.project and scope.project.project_id:
                if (
                    entry.scope.project is None
                    or entry.scope.project.project_id != scope.project.project_id
                ):
                    continue
            if scope.session and scope.session.session_id:
                if (
                    entry.scope.session is None
                    or entry.scope.session.session_id != scope.session.session_id
                ):
                    continue
            to_remove.append(mid)

        for mid in to_remove:
            del cache[mid]

        if to_remove:
            self._persist(cache)

        return len(to_remove)

    def reload(self) -> int:
        """Force reload from disk, discarding cache.

        Returns:
            Number of entries loaded.
        """
        self._cache = self._load_entries()
        return len(self._cache)

    def size(self) -> int:
        """Return current number of cached entries."""
        return len(self._get_cache())

    def migrate(self, from_version: str) -> bool:
        """Attempt to migrate from an older schema version.

        Currently a no-op since SCHEMA_VERSION is 2.6.0 and there
        are no prior versions. Provides migration hook for future use.

        Returns:
            True if migration was performed, False if already current.
        """
        data = self._load_raw()
        current = data.get("version", "")
        if current == SCHEMA_VERSION:
            return False
        # Future: implement version-specific migrations
        return False
