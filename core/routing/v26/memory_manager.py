"""Central memory manager for Lerev V2.6.

Coordinates the V2.6 read/write paths:
- Memory request validation and scope enforcement
- Retrieval coordination (via existing Lerev systems)
- Confidence filtering
- Context budget enforcement
- Experience capture
- Lifecycle coordination
- Provenance tracking

Design principles:
- Does NOT replace V2.3 confidence, V2.2 conflict, V2.4.2 lifecycle, V2.5 routing
- Coordinates existing Lerev systems rather than rebuilding them
- No global mutable state
- Deterministic and auditable
"""

from __future__ import annotations

from typing import Any

from core.routing.v26.consolidation import ConsolidationResult, consolidate_experiences
from core.routing.v26.experience import (
    Experience,
    is_promotable,
    validate_experience_content,
)
from core.routing.v26.identity import AgentIdentity, MemoryScope
from core.routing.v26.memory_store import MemoryStore
from core.routing.v26.memory_types import (
    MemoryEntry,
    MemoryKind,
    MemoryRequest,
    MemoryResponse,
)
from core.routing.v26.persistence import ScopeIsolatedStorage
from core.routing.v26.security import (
    V26SecurityPolicy,
    enforce_instruction_boundary,
    validate_memory_content,
    validate_memory_request,
)


class MemoryManager:
    """Central coordinator for V2.6 long-term memory.

    Manages the full lifecycle of memory: storage, retrieval,
    experience capture, consolidation, and persistence.

    No global mutable state — manager is per-instance.
    """

    def __init__(
        self,
        storage: ScopeIsolatedStorage | None = None,
        policy: V26SecurityPolicy | None = None,
        store: MemoryStore | None = None,
    ) -> None:
        """Initialize the memory manager.

        Args:
            storage: Persistent storage backend (optional, for durability).
            policy: Security policy (optional, uses defaults if None).
            store: In-memory store (optional, creates default if None).
        """
        self._storage = storage
        self._policy = policy or V26SecurityPolicy()
        self._store = store or MemoryStore()
        self._consolidation_history: list[ConsolidationResult] = []
        self._operation_count = 0
        self._error_count = 0

    # ------------------------------------------------------------------
    # Read path
    # ------------------------------------------------------------------

    def request_memory(self, request: MemoryRequest) -> MemoryResponse:
        """Process a memory retrieval request.

        The read path:
        1. Validate request and security policy
        2. Validate scope access
        3. Query in-memory store with scope filtering
        4. Filter by confidence
        5. Apply context budget
        6. Return bounded response

        Args:
            request: The memory retrieval request.

        Returns:
            MemoryResponse with matching memories.
        """
        self._operation_count += 1

        # Step 1: Validate request
        is_valid, reason = validate_memory_request(request, self._policy)
        if not is_valid:
            self._error_count += 1
            return MemoryResponse(
                memories=(),
                total=0,
                truncated=False,
                context_cost=0,
                provenance=(),
            )

        # Step 2: Build scope
        scope = request.to_scope()

        # Step 3: Query store
        kinds = request.kinds if request.kinds else None
        entries = self._store.query(
            scope=scope,
            kind=kinds[0] if kinds and len(kinds) == 1 else None,
            limit=request.limit + 100,  # Extra for budget filtering
            minimum_confidence=request.minimum_confidence,
            tags=request.tags if request.tags else None,
            query_text=request.query,
        )

        # Step 4: Filter by instruction boundary (security)
        safe_entries: list[MemoryEntry] = []
        for entry in entries:
            is_safe, _ = enforce_instruction_boundary(entry)
            if is_safe:
                safe_entries.append(entry)

        # Step 5: Apply context budget
        total_tokens = 0
        selected: list[MemoryEntry] = []
        truncated = False

        for entry in safe_entries:
            entry_tokens = entry.estimated_tokens
            if total_tokens + entry_tokens > request.context_budget:
                truncated = True
                break
            if len(selected) >= request.limit:
                truncated = True
                break
            selected.append(entry)
            total_tokens += entry_tokens

        # Step 6: Build response
        provenance = tuple(e.memory_id for e in selected)
        return MemoryResponse(
            memories=tuple(selected),
            total=len(safe_entries),
            truncated=truncated,
            context_cost=total_tokens,
            provenance=provenance,
        )

    # ------------------------------------------------------------------
    # Write path
    # ------------------------------------------------------------------

    def store_memory(
        self,
        entry: MemoryEntry,
        agent: AgentIdentity | None = None,
    ) -> tuple[bool, str]:
        """Store a memory entry.

        Validates content and scope before storage.

        Args:
            entry: The memory entry to store.
            agent: If provided, validates agent ownership.

        Returns:
            Tuple of (success, reason).
        """
        self._operation_count += 1

        # Validate content
        is_valid, reason = validate_memory_content(entry, self._policy)
        if not is_valid:
            self._error_count += 1
            return False, reason

        # Validate agent ownership
        if agent is not None:
            if entry.scope.agent.agent_id != agent.agent_id:
                self._error_count += 1
                return False, "agent ownership mismatch"

        # Store in memory
        self._store.store(entry)

        # Persist if storage backend available
        if self._storage is not None:
            try:
                self._storage.store(entry)
            except Exception as e:
                return False, f"persistence error: {e}"

        return True, ""

    def store_experience(self, experience: Experience) -> tuple[bool, str]:
        """Store an experience as episodic memory.

        Validates the experience, converts to MemoryEntry, and stores.

        Args:
            experience: The experience to store.

        Returns:
            Tuple of (success, reason).
        """
        self._operation_count += 1

        # Validate experience
        is_valid, reason = experience.validate()
        if not is_valid:
            self._error_count += 1
            return False, reason

        # Validate content
        is_valid, reason = validate_experience_content(experience)
        if not is_valid:
            self._error_count += 1
            return False, reason

        # Convert to memory entry
        entry = experience.to_memory_entry()

        # Validate content
        is_valid, reason = validate_memory_content(entry, self._policy)
        if not is_valid:
            self._error_count += 1
            return False, reason

        # Store
        self._store.store(entry)

        # Persist if storage backend available
        if self._storage is not None:
            try:
                self._storage.store(entry)
            except Exception as e:
                return False, f"persistence error: {e}"

        return True, ""

    # ------------------------------------------------------------------
    # Experience promotion
    # ------------------------------------------------------------------

    def check_promotion(
        self,
        experience: Experience,
    ) -> tuple[bool, str]:
        """Check if an experience is a candidate for promotion.

        Uses existing Lerev mechanisms (confidence, evidence, lifecycle)
        to determine promotion readiness.

        Args:
            experience: The experience to evaluate.

        Returns:
            Tuple of (promotable, reason).
        """
        return is_promotable(experience)

    def promote_experience(
        self,
        experience: Experience,
    ) -> tuple[bool, str, MemoryEntry | None]:
        """Promote an experience to learned knowledge.

        Only promotes if the experience passes promotion criteria.

        Args:
            experience: The experience to promote.

        Returns:
            Tuple of (success, reason, created_entry).
        """
        self._operation_count += 1

        is_promotable_result, reason = is_promotable(experience)
        if not is_promotable_result:
            return False, reason, None

        # Create learned memory entry
        entry = MemoryEntry(
            memory_id=experience.experience_id,
            content=experience.observation or experience.action,
            kind=MemoryKind.LEARNED,
            scope=experience.to_scope(),
            timestamp=experience.timestamp,
            source=experience.source,
            tags=experience.tags | frozenset({"promoted"}),
            confidence=experience.confidence,
            metadata=dict(experience.metadata),
            promoted_from=experience.experience_id,
        )

        # Validate and store
        is_valid, val_reason = validate_memory_content(entry, self._policy)
        if not is_valid:
            return False, val_reason, None

        self._store.store(entry)

        if self._storage is not None:
            try:
                self._storage.store(entry)
            except Exception as e:
                return False, f"persistence error: {e}", None

        return True, "", entry

    # ------------------------------------------------------------------
    # Consolidation
    # ------------------------------------------------------------------

    def consolidate(
        self,
        experiences: list[Experience],
        scope: MemoryScope | None = None,
    ) -> ConsolidationResult:
        """Consolidate experiences into learned knowledge.

        Groups experiences, merges consistent groups, and promotes
        when evidence is sufficient.

        Args:
            experiences: Experiences to consolidate.
            scope: Optional scope restriction.

        Returns:
            ConsolidationResult with promoted and retained entries.
        """
        self._operation_count += 1

        result = consolidate_experiences(experiences, scope=scope)
        self._consolidation_history.append(result)

        # Store promoted entries
        for entry in result.promoted:
            self._store.store(entry)
            if self._storage is not None:
                try:
                    self._storage.store(entry)
                except Exception:
                    pass  # Best effort for consolidation

        return result

    # ------------------------------------------------------------------
    # Scope queries
    # ------------------------------------------------------------------

    def list_memories(
        self,
        scope: MemoryScope | None = None,
        kind: MemoryKind | None = None,
        limit: int = 100,
    ) -> list[MemoryEntry]:
        """List memories with optional filtering.

        Args:
            scope: Scope filter.
            kind: Kind filter.
            limit: Maximum results.

        Returns:
            List of matching memory entries.
        """
        return self._store.query(scope=scope, kind=kind, limit=limit)

    def count_memories(
        self,
        scope: MemoryScope | None = None,
        kind: MemoryKind | None = None,
    ) -> int:
        """Count memories with optional filtering."""
        return self._store.count(scope=scope, kind=kind)

    def get_memory(self, memory_id: str) -> MemoryEntry | None:
        """Retrieve a specific memory by ID."""
        return self._store.get(memory_id)

    def remove_memory(self, memory_id: str) -> bool:
        """Remove a memory by ID."""
        removed = self._store.remove(memory_id)
        if removed and self._storage is not None:
            try:
                self._storage.remove(memory_id)
            except Exception:
                pass
        return removed

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def reload(self) -> int:
        """Reload from persistent storage.

        Returns:
            Number of entries loaded.
        """
        if self._storage is None:
            return 0
        count = self._storage.reload()
        # Rebuild in-memory store from persistence
        self._store.clear()
        for mid in self._storage.list_keys():
            entry = self._storage.get(mid)
            if entry is not None:
                self._store.store(entry)
        return count

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def stats(self) -> dict[str, Any]:
        """Return manager statistics."""
        return {
            "operation_count": self._operation_count,
            "error_count": self._error_count,
            "store_size": self._store.size,
            "consolidations": len(self._consolidation_history),
            "total_promoted": sum(
                r.promoted_count for r in self._consolidation_history
            ),
        }

    def clear(self, scope: MemoryScope | None = None) -> int:
        """Clear memories, optionally scoped.

        Returns:
            Number of memories cleared.
        """
        count = self._store.clear(scope=scope)
        if self._storage is not None:
            try:
                self._storage.clear(scope=scope)
            except Exception:
                pass
        return count
