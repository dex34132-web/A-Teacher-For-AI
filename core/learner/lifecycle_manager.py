"""Lifecycle manager for V2.4.2 knowledge management.

Integrates:
- Lifecycle states (ACTIVE, UNCERTAIN, SUPERSEDED, ARCHIVED)
- Memory health computation
- Knowledge reinforcement
- Knowledge decay
- Supersession analysis
- Merging and redundancy
- Archiving
- Provenance tracking
- Persistence
- Automatic maintenance with configurable interval
- Deterministic behavior for reproducibility

This is the main entry point for lifecycle operations.

V2.4.2 Changes:
- Added automatic maintenance mechanism
- Added deterministic clock for testing
- Added maintenance history tracking
- Improved persistence with version info
- Added idempotent maintenance operations
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from core.learner.hybrid_memory import HybridExample, HybridMemory
from core.learner.knowledge_ops import (
    MergeCandidate,
    RedundancyResult,
    SupersessionResult,
    analyze_redundancy,
    analyze_supersession,
    archive_memory,
    find_merge_candidates,
    is_eligible_for_archive,
)
from core.learner.lifecycle import (
    HealthSignals,
    LifecycleConfig,
    LifecycleEvent,
    MemoryState,
    compute_decay,
    compute_health_score,
    compute_reinforcement,
)

# Persistence version for backward compatibility
PERSISTENCE_VERSION = "2.4.2"

# ---------------------------------------------------------------------------
# Lifecycle state per memory
# ---------------------------------------------------------------------------


@dataclass
class MemoryLifecycleState:
    """Per-memory lifecycle state with provenance.

    Attributes:
        memory_id: The memory's ID.
        state: Current lifecycle state.
        health_score: Current health score [0, 1].
        last_health_check: Timestamp of last health evaluation.
        lifecycle_events: History of state transitions.
        superseded_by: ID of memory that superseded this one (if any).
        merged_from: IDs of memories merged into this one (if any).
        last_reinforced: Timestamp of last reinforcement.
        last_decayed: Timestamp of last decay application.
    """

    memory_id: int
    state: MemoryState = MemoryState.ACTIVE
    health_score: float = 0.5
    last_health_check: float = 0.0
    lifecycle_events: list[LifecycleEvent] = field(default_factory=list)
    superseded_by: int | None = None
    merged_from: list[int] = field(default_factory=list)
    last_reinforced: float = 0.0
    last_decayed: float = 0.0


# ---------------------------------------------------------------------------
# Maintenance history
# ---------------------------------------------------------------------------


@dataclass
class MaintenanceRecord:
    """Record of a maintenance cycle.

    Attributes:
        timestamp: When maintenance ran.
        memories_processed: Number of memories processed.
        transitions: Number of state transitions.
        duration_seconds: How long maintenance took.
        details: Summary of what happened.
    """

    timestamp: float
    memories_processed: int
    transitions: int
    duration_seconds: float
    details: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Lifecycle manager
# ---------------------------------------------------------------------------


class LifecycleManager:
    """Manages the lifecycle of all memories in the system.

    Provides:
    - State tracking per memory
    - Health computation
    - Reinforcement on successful use
    - Decay over time
    - Supersession analysis
    - Merging and consolidation
    - Archiving
    - Provenance tracking
    - Persistence
    - Automatic maintenance with configurable interval

    Does NOT:
    - Delete memories (only archive)
    - Modify confidence system (V2.3.4 preserved)
    """

    def __init__(
        self,
        config: LifecycleConfig | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        """Initialize the lifecycle manager.

        Args:
            config: Lifecycle configuration. Uses defaults if None.
            clock: Optional clock function for deterministic testing.
                   Defaults to time.time if None.
        """
        self._config = config or LifecycleConfig()
        self._states: dict[int, MemoryLifecycleState] = {}
        self._events: list[LifecycleEvent] = []
        self._maintenance_history: list[MaintenanceRecord] = []
        self._last_maintenance: float = 0.0
        self._clock = clock or time.time

    @property
    def config(self) -> LifecycleConfig:
        """Return the lifecycle configuration."""
        return self._config

    def get_state(self, memory_id: int) -> MemoryLifecycleState:
        """Get lifecycle state for a memory.

        Args:
            memory_id: The memory's ID.

        Returns:
            MemoryLifecycleState (creates default if not tracked yet).
        """
        if memory_id not in self._states:
            self._states[memory_id] = MemoryLifecycleState(
                memory_id=memory_id,
                state=MemoryState.ACTIVE,
                health_score=0.5,
                last_health_check=self._clock(),
            )
        return self._states[memory_id]

    def get_all_states(self) -> dict[int, MemoryLifecycleState]:
        """Return all lifecycle states."""
        return dict(self._states)

    def get_events(self) -> list[LifecycleEvent]:
        """Return all lifecycle events."""
        return list(self._events)

    def get_maintenance_history(self) -> list[MaintenanceRecord]:
        """Return maintenance history."""
        return list(self._maintenance_history)

    @property
    def last_maintenance(self) -> float:
        """Return timestamp of last maintenance."""
        return self._last_maintenance

    @property
    def needs_maintenance(self) -> bool:
        """Check if maintenance is due based on interval."""
        if self._config.maintenance_interval_hours <= 0:
            return False
        elapsed_hours = (self._clock() - self._last_maintenance) / 3600.0
        return elapsed_hours >= self._config.maintenance_interval_hours

    # ------------------------------------------------------------------
    # Health evaluation
    # ------------------------------------------------------------------

    def evaluate_health(
        self,
        example: HybridExample,
        memory: HybridMemory,
    ) -> float:
        """Evaluate health score for a memory.

        Args:
            example: The memory to evaluate.
            memory: The hybrid memory store.

        Returns:
            Health score [0, 1].
        """
        # Compute signals
        total_uses = example.success_count + example.failure_count
        usage_freq = min(1.0, example.use_count / 10.0)

        # Count independent evidence (different input texts with same output)
        independent = 0
        for ex in memory.get_all_hybrid():
            if ex.output == example.output and ex.id != example.id:
                independent += 1

        # Count contradictions (different outputs for similar inputs)
        contradictions = 0
        for ex in memory.get_all_hybrid():
            if ex.id != example.id and ex.output != example.output:
                # Simple heuristic: if input words overlap significantly
                words_a = set(example.input_text.lower().split())
                words_b = set(ex.input_text.lower().split())
                if words_a and words_b:
                    overlap = len(words_a & words_b) / max(len(words_a), len(words_b))
                    if overlap > 0.5:
                        contradictions += 1

        # Recency: 0 (never used) to 1 (just used)
        now = self._clock()
        if example.last_used_at > 0:
            days_since_use = (now - example.last_used_at) / 86400.0
        else:
            days_since_use = 365.0
        recency = max(0.0, 1.0 - min(1.0, days_since_use / 30.0))

        signals = HealthSignals(
            success_rate=example.success_rate if total_uses > 0 else 0.5,
            independent_evidence=independent,
            confidence=example.weight,
            recency=recency,
            usage_frequency=usage_freq,
            redundancy=0.0,  # Will be computed separately
            contradiction_count=contradictions,
        )

        health = compute_health_score(signals)

        # Update state
        state = self.get_state(example.id)
        state.health_score = health
        state.last_health_check = now

        return health

    # ------------------------------------------------------------------
    # Reinforcement
    # ------------------------------------------------------------------

    def reinforce(self, example: HybridExample) -> float:
        """Reinforce a memory after successful use.

        Args:
            example: The memory that was used successfully.

        Returns:
            New confidence after reinforcement.
        """
        old_confidence = example.weight
        new_confidence = compute_reinforcement(
            confidence=old_confidence,
            success_count=example.success_count,
            independent_evidence=example.success_count,
            config=self._config,
        )

        # Update state
        state = self.get_state(example.id)
        now = self._clock()
        is_uncertain = state.state == MemoryState.UNCERTAIN
        conf_above_threshold = new_confidence > self._config.uncertainty_threshold
        if is_uncertain and conf_above_threshold:
            event = LifecycleEvent(
                previous_state=MemoryState.UNCERTAIN.value,
                new_state=MemoryState.ACTIVE.value,
                reason=f"Confidence improved ({old_confidence:.3f} -> {new_confidence:.3f})",
                timestamp=now,
                evidence_summary={"new_confidence": new_confidence},
                related_ids=[example.id],
                confidence_at_transition=new_confidence,
            )
            state.state = MemoryState.ACTIVE
            state.lifecycle_events.append(event)
            self._events.append(event)

        state.last_reinforced = now
        return new_confidence

    # ------------------------------------------------------------------
    # Decay
    # ------------------------------------------------------------------

    def apply_decay(self, example: HybridExample) -> float:
        """Apply time-based decay to a memory.

        Args:
            example: The memory to decay.

        Returns:
            New confidence after decay.
        """
        now = self._clock()
        if example.last_used_at > 0:
            days_since_use = (now - example.last_used_at) / 86400.0
        else:
            days_since_use = 365.0

        old_confidence = example.weight
        new_confidence = compute_decay(
            confidence=old_confidence,
            days_since_use=days_since_use,
            success_rate=example.success_rate,
            independent_evidence=example.success_count,
            config=self._config,
        )

        # Check if state should change
        state = self.get_state(example.id)
        conf_below = new_confidence < self._config.uncertainty_threshold
        is_active = state.state == MemoryState.ACTIVE
        if conf_below and is_active:
            event = LifecycleEvent(
                previous_state=MemoryState.ACTIVE.value,
                new_state=MemoryState.UNCERTAIN.value,
                reason=f"Confidence decayed ({old_confidence:.3f} -> {new_confidence:.3f})",
                timestamp=now,
                evidence_summary={"days_since_use": days_since_use},
                related_ids=[example.id],
                confidence_at_transition=new_confidence,
            )
            state.state = MemoryState.UNCERTAIN
            state.lifecycle_events.append(event)
            self._events.append(event)

        # Check if eligible for archival
        if new_confidence < self._config.archive_threshold:
            eligible, reason = is_eligible_for_archive(example, new_confidence, self._config)
            if eligible:
                new_state, event = archive_memory(example, reason, state.state)
                state.state = new_state
                state.lifecycle_events.append(event)
                self._events.append(event)

        state.last_decayed = now
        return new_confidence

    # ------------------------------------------------------------------
    # Supersession
    # ------------------------------------------------------------------

    def analyze_supersession(
        self,
        old: HybridExample,
        new: HybridExample,
    ) -> SupersessionResult:
        """Analyze whether new knowledge supersedes old.

        Args:
            old: Existing memory.
            new: Newer memory.

        Returns:
            SupersessionResult with recommendation.
        """
        return analyze_supersession(old, new, self._config)

    def apply_supersession(
        self,
        old_id: int,
        new_id: int,
        reason: str,
    ) -> LifecycleEvent:
        """Apply supersession: mark old as SUPERSEDED by new.

        Args:
            old_id: ID of memory being superseded.
            new_id: ID of memory doing the superseding.
            reason: Reason for supersession.

        Returns:
            LifecycleEvent recording the transition.
        """
        old_state = self.get_state(old_id)
        previous = old_state.state

        event = LifecycleEvent(
            previous_state=previous.value,
            new_state=MemoryState.SUPERSEDED.value,
            reason=reason,
            timestamp=self._clock(),
            related_ids=[old_id, new_id],
            confidence_at_transition=old_state.health_score,
        )

        old_state.state = MemoryState.SUPERSEDED
        old_state.superseded_by = new_id
        old_state.lifecycle_events.append(event)
        self._events.append(event)

        return event

    # ------------------------------------------------------------------
    # Merging
    # ------------------------------------------------------------------

    def find_merge_candidates(
        self,
        examples: list[HybridExample],
    ) -> list[MergeCandidate]:
        """Find merge candidate pairs.

        Args:
            examples: All memories.

        Returns:
            List of merge candidates.
        """
        return find_merge_candidates(examples, self._config)

    def apply_merge(
        self,
        target_id: int,
        source_ids: list[int],
        reason: str,
    ) -> LifecycleEvent:
        """Record that memories were merged into target.

        Args:
            target_id: ID of the surviving memory.
            source_ids: IDs of memories merged into target.
            reason: Reason for merging.

        Returns:
            LifecycleEvent recording the merge.
        """
        target_state = self.get_state(target_id)
        previous = target_state.state
        now = self._clock()

        event = LifecycleEvent(
            previous_state=previous.value,
            new_state=previous.value,  # State doesn't change on merge
            reason=reason,
            timestamp=now,
            related_ids=[target_id] + source_ids,
            confidence_at_transition=target_state.health_score,
        )

        target_state.merged_from.extend(source_ids)
        target_state.lifecycle_events.append(event)
        self._events.append(event)

        # Mark source memories as archived
        for source_id in source_ids:
            source_state = self.get_state(source_id)
            source_event = LifecycleEvent(
                previous_state=source_state.state.value,
                new_state=MemoryState.ARCHIVED.value,
                reason=f"Merged into memory {target_id}: {reason}",
                timestamp=now,
                related_ids=[source_id, target_id],
                confidence_at_transition=source_state.health_score,
            )
            source_state.state = MemoryState.ARCHIVED
            source_state.lifecycle_events.append(source_event)
            self._events.append(source_event)

        return event

    # ------------------------------------------------------------------
    # Redundancy
    # ------------------------------------------------------------------

    def analyze_redundancy(
        self,
        a: HybridExample,
        b: HybridExample,
    ) -> RedundancyResult:
        """Analyze redundancy between two memories.

        Args:
            a: First memory.
            b: Second memory.

        Returns:
            RedundancyResult with classification.
        """
        return analyze_redundancy(a, b, self._config)

    # ------------------------------------------------------------------
    # Archiving
    # ------------------------------------------------------------------

    def archive(
        self,
        example: HybridExample,
        reason: str,
    ) -> LifecycleEvent:
        """Manually archive a memory.

        Args:
            example: The memory to archive.
            reason: Reason for archival.

        Returns:
            LifecycleEvent recording the transition.
        """
        state = self.get_state(example.id)
        new_state, event = archive_memory(example, reason, state.state)
        state.state = new_state
        state.lifecycle_events.append(event)
        self._events.append(event)
        return event

    def restore(self, memory_id: int, reason: str) -> LifecycleEvent:
        """Restore an archived memory to ACTIVE.

        Args:
            memory_id: ID of memory to restore.
            reason: Reason for restoration.

        Returns:
            LifecycleEvent recording the transition.
        """
        state = self.get_state(memory_id)
        previous = state.state

        event = LifecycleEvent(
            previous_state=previous.value,
            new_state=MemoryState.ACTIVE.value,
            reason=reason,
            timestamp=self._clock(),
            related_ids=[memory_id],
            confidence_at_transition=state.health_score,
        )

        state.state = MemoryState.ACTIVE
        state.lifecycle_events.append(event)
        self._events.append(event)

        return event

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def run_maintenance(
        self,
        memory: HybridMemory,
        force: bool = False,
    ) -> MaintenanceRecord:
        """Run lifecycle maintenance on all memories.

        This is idempotent - running multiple times with no new evidence
        should not repeatedly damage the same memory.

        Args:
            memory: The hybrid memory store.
            force: If True, run even if not due based on interval.

        Returns:
            MaintenanceRecord with results.
        """
        start_time = self._clock()

        # Check if maintenance is due
        if not force and not self.needs_maintenance:
            return MaintenanceRecord(
                timestamp=start_time,
                memories_processed=0,
                transitions=0,
                duration_seconds=0.0,
                details={"skipped": "not due"},
            )

        transitions_before = len(self._events)
        memories_processed = 0

        for example in memory.get_all_hybrid():
            memories_processed += 1

            # Evaluate health
            self.evaluate_health(example, memory)

            # Apply decay
            new_confidence = self.apply_decay(example)

            # Update memory weight (preserving V2.3.4 confidence system)
            example.weight = new_confidence

        transitions_after = len(self._events)
        end_time = self._clock()

        record = MaintenanceRecord(
            timestamp=start_time,
            memories_processed=memories_processed,
            transitions=transitions_after - transitions_before,
            duration_seconds=end_time - start_time,
            details={
                "events_total": transitions_after,
            },
        )

        self._maintenance_history.append(record)
        self._last_maintenance = start_time

        return record

    def needs_maintenance_check(self, memory: HybridMemory) -> bool:
        """Check if any memories need health evaluation.

        Args:
            memory: The hybrid memory store.

        Returns:
            True if any memories need evaluation.
        """
        now = self._clock()
        for example in memory.get_all_hybrid():
            state = self.get_state(example.id)
            if now - state.last_health_check > 3600:  # 1 hour
                return True
        return False

    # ------------------------------------------------------------------
    # Batch processing (legacy, calls run_maintenance)
    # ------------------------------------------------------------------

    def process_all(
        self,
        memory: HybridMemory,
    ) -> dict[str, Any]:
        """Run lifecycle processing on all memories.

        Evaluates health, applies decay, checks for archival.

        Args:
            memory: The hybrid memory store.

        Returns:
            Summary of processing results.
        """
        results = {
            "total": 0,
            "active": 0,
            "uncertain": 0,
            "superseded": 0,
            "archived": 0,
            "health_scores": {},
            "transitions": [],
        }

        for example in memory.get_all_hybrid():
            results["total"] += 1

            # Evaluate health
            health = self.evaluate_health(example, memory)
            results["health_scores"][example.id] = health

            # Apply decay
            new_confidence = self.apply_decay(example)

            # Update memory weight (preserving V2.3.4 confidence system)
            example.weight = new_confidence

            # Count states
            state = self.get_state(example.id)
            if state.state == MemoryState.ACTIVE:
                results["active"] += 1
            elif state.state == MemoryState.UNCERTAIN:
                results["uncertain"] += 1
            elif state.state == MemoryState.SUPERSEDED:
                results["superseded"] += 1
            elif state.state == MemoryState.ARCHIVED:
                results["archived"] += 1

        # Record transitions
        results["transitions"] = [
            {
                "previous": e.previous_state,
                "new": e.new_state,
                "reason": e.reason,
                "timestamp": e.timestamp,
            }
            for e in self._events[-10:]  # Last 10 events
        ]

        return results

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: Path) -> None:
        """Save lifecycle state to JSON.

        Args:
            path: Directory path to save to.
        """
        save_path = Path(path)
        save_path.mkdir(parents=True, exist_ok=True)

        # Save states
        states_data = {}
        for mid, state in self._states.items():
            states_data[str(mid)] = {
                "memory_id": state.memory_id,
                "state": state.state.value,
                "health_score": state.health_score,
                "last_health_check": state.last_health_check,
                "superseded_by": state.superseded_by,
                "merged_from": state.merged_from,
                "last_reinforced": state.last_reinforced,
                "last_decayed": state.last_decayed,
                "events": [
                    {
                        "previous_state": e.previous_state,
                        "new_state": e.new_state,
                        "reason": e.reason,
                        "timestamp": e.timestamp,
                        "evidence_summary": e.evidence_summary,
                        "related_ids": e.related_ids,
                        "confidence_at_transition": e.confidence_at_transition,
                    }
                    for e in state.lifecycle_events
                ],
            }

        (save_path / "lifecycle_states.json").write_text(
            json.dumps(states_data, indent=2), encoding="utf-8"
        )

        # Save config
        config_data = {
            "decay_rate": self._config.decay_rate,
            "decay_min": self._config.decay_min,
            "reinforcement_strength": self._config.reinforcement_strength,
            "independence_bonus": self._config.independence_bonus,
            "supersession_threshold": self._config.supersession_threshold,
            "merge_similarity": self._config.merge_similarity,
            "archive_threshold": self._config.archive_threshold,
            "uncertainty_threshold": self._config.uncertainty_threshold,
            "max_redundancy": self._config.max_redundancy,
            "maintenance_interval_hours": self._config.maintenance_interval_hours,
            "merge_input_similarity": self._config.merge_input_similarity,
            "merge_min_evidence": self._config.merge_min_evidence,
        }
        (save_path / "lifecycle_config.json").write_text(
            json.dumps(config_data, indent=2), encoding="utf-8"
        )

        # Save metadata with version
        metadata = {
            "version": PERSISTENCE_VERSION,
            "last_maintenance": self._last_maintenance,
            "events_count": len(self._events),
            "states_count": len(self._states),
        }
        (save_path / "lifecycle_metadata.json").write_text(
            json.dumps(metadata, indent=2), encoding="utf-8"
        )

    @classmethod
    def load(cls, path: Path) -> LifecycleManager:
        """Load lifecycle state from JSON.

        Supports loading from:
        - V2.4.2 (current version)
        - V2.4.0 (backward compatible, missing new fields get defaults)

        Args:
            path: Directory path to load from.

        Returns:
            Restored LifecycleManager instance.
        """
        load_path = Path(path)

        # Load config (with backward compatibility for new fields)
        config_data = json.loads(
            (load_path / "lifecycle_config.json").read_text(encoding="utf-8")
        )
        # Add defaults for fields that may not exist in older versions
        config_data.setdefault("maintenance_interval_hours", 24.0)
        config_data.setdefault("merge_input_similarity", 0.6)
        config_data.setdefault("merge_min_evidence", 2)
        config = LifecycleConfig(**config_data)

        manager = cls(config=config)

        # Load metadata if available
        metadata_file = load_path / "lifecycle_metadata.json"
        if metadata_file.exists():
            metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
            manager._last_maintenance = metadata.get("last_maintenance", 0.0)

        # Load states
        states_file = load_path / "lifecycle_states.json"
        if states_file.exists():
            states_data = json.loads(states_file.read_text(encoding="utf-8"))
            for mid_str, data in states_data.items():
                mid = int(mid_str)
                state = MemoryLifecycleState(
                    memory_id=mid,
                    state=MemoryState(data["state"]),
                    health_score=data.get("health_score", 0.5),
                    last_health_check=data.get("last_health_check", 0.0),
                    superseded_by=data.get("superseded_by"),
                    merged_from=data.get("merged_from", []),
                    last_reinforced=data.get("last_reinforced", 0.0),
                    last_decayed=data.get("last_decayed", 0.0),
                )
                # Load events
                for e_data in data.get("events", []):
                    event = LifecycleEvent(
                        previous_state=e_data["previous_state"],
                        new_state=e_data["new_state"],
                        reason=e_data["reason"],
                        timestamp=e_data["timestamp"],
                        evidence_summary=e_data.get("evidence_summary", {}),
                        related_ids=e_data.get("related_ids", []),
                        confidence_at_transition=e_data.get("confidence_at_transition", 0.0),
                    )
                    state.lifecycle_events.append(event)
                    manager._events.append(event)

                manager._states[mid] = state

        return manager
