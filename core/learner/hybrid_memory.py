"""Extended memory for hybrid lexical+semantic learner (V2).

Stores both TF-IDF feature vectors and dense semantic vectors alongside
each learned example. This allows V2 to compute similarity using either
or both representations.

V1 memory is untouched — HybridMemory adds semantic_vector as an optional
field. If no semantic encoder is available, semantic vectors are None
and the system degrades to V1 behavior.

V2.1 adds usage metadata (created_at, last_used_at, use_count,
success_count, failure_count) stored separately to preserve V1/V2
backward compatibility.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.learner.feature_extractor import FeatureVector
from core.learner.memory import ExampleMemory, LearnedExample

# ---------------------------------------------------------------------------
# Extended example with semantic vector and usage metadata
# ---------------------------------------------------------------------------


@dataclass
class HybridExample:
    """A learned example with lexical, semantic, and usage representations.

    Attributes:
        id: Unique identifier.
        input_text: Original input text.
        output: Expected output/label.
        lexical_vector: TF-IDF feature vector (from V1).
        semantic_vector: Dense semantic embedding (optional, from V2).
        weight: Confidence/weight of this example.
        feedback_count: Number of times feedback was received.
        correct_count: Number of times confirmed correct.
        metadata: Additional information.
        created_at: Epoch timestamp when this memory was created.
        last_used_at: Epoch timestamp when this memory was last used.
        use_count: Number of times this memory was accessed.
        success_count: Number of successful uses.
        failure_count: Number of failed uses.
    """

    id: int
    input_text: str
    output: str
    lexical_vector: FeatureVector
    semantic_vector: list[float] | None = None
    weight: float = 1.0
    feedback_count: int = 0
    correct_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0
    last_used_at: float = 0.0
    use_count: int = 0
    success_count: int = 0
    failure_count: int = 0

    @property
    def accuracy(self) -> float:
        """Return the accuracy ratio for this example."""
        if self.feedback_count == 0:
            return 0.0
        return self.correct_count / self.feedback_count

    @property
    def success_rate(self) -> float:
        """Return the success rate for this example based on usage."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.5  # Neutral for untested memories
        return self.success_count / total


# ---------------------------------------------------------------------------
# Hybrid memory
# ---------------------------------------------------------------------------


class HybridMemory(ExampleMemory):
    """In-memory store supporting both lexical and semantic vectors.

    Extends ExampleMemory by adding:
    - Optional semantic vector storage per example
    - Usage metadata (timestamps, counts) for V2.1 retrieval scoring
    - save/load that persists all V2/V2.1 data
    - get_hybrid() returning HybridExample with all representations

    Falls back gracefully when semantic vectors are absent.
    Backward compatible with V1/V2 persistence formats.
    """

    def __init__(self) -> None:
        """Initialize empty hybrid memory."""
        super().__init__()
        self._semantic_vectors: dict[int, list[float]] = {}
        # V2.1 usage metadata — stored separately to preserve V1 compatibility
        self._created_at: dict[int, float] = {}
        self._last_used_at: dict[int, float] = {}
        self._use_count: dict[int, int] = {}
        self._success_count: dict[int, int] = {}
        self._failure_count: dict[int, int] = {}

    def add(  # type: ignore[override]
        self,
        input_text: str,
        output: str,
        vector: FeatureVector,
        weight: float = 1.0,
        metadata: dict[str, Any] | None = None,
        semantic_vector: list[float] | None = None,
    ) -> HybridExample:
        """Add a new example with optional semantic vector.

        Args:
            input_text: Original input text.
            output: Expected output/label.
            vector: TF-IDF feature vector.
            weight: Initial weight.
            metadata: Optional metadata.
            semantic_vector: Optional dense semantic embedding.

        Returns:
            The created HybridExample.
        """
        now = time.time()

        # Store lexical example via parent
        parent_example = super().add(
            input_text=input_text,
            output=output,
            vector=vector,
            weight=weight,
            metadata=metadata,
        )

        # Store semantic vector separately
        if semantic_vector is not None:
            self._semantic_vectors[parent_example.id] = semantic_vector

        # V2.1: Initialize usage metadata
        ex_id = parent_example.id
        self._created_at[ex_id] = now
        self._last_used_at[ex_id] = now
        self._use_count[ex_id] = 0
        self._success_count[ex_id] = 0
        self._failure_count[ex_id] = 0

        result = self.get_hybrid(parent_example.id)
        assert result is not None, "Example was just added, must exist"
        return result

    def set_semantic_vector(self, example_id: int, semantic_vector: list[float]) -> bool:
        """Set or update the semantic vector for an existing example.

        Args:
            example_id: The example's ID.
            semantic_vector: Dense semantic embedding.

        Returns:
            True if the example was found and updated.
        """
        if self.get(example_id) is not None:
            self._semantic_vectors[example_id] = semantic_vector
            return True
        return False

    def get_hybrid(self, example_id: int) -> HybridExample | None:
        """Retrieve an example with all vector representations and metadata.

        Args:
            example_id: The example's ID.

        Returns:
            HybridExample if found, None otherwise.
        """
        base = self.get(example_id)
        if base is None:
            return None

        return HybridExample(
            id=base.id,
            input_text=base.input_text,
            output=base.output,
            lexical_vector=base.vector,
            semantic_vector=self._semantic_vectors.get(base.id),
            weight=base.weight,
            feedback_count=base.feedback_count,
            correct_count=base.correct_count,
            metadata=base.metadata,
            created_at=self._created_at.get(base.id, 0.0),
            last_used_at=self._last_used_at.get(base.id, 0.0),
            use_count=self._use_count.get(base.id, 0),
            success_count=self._success_count.get(base.id, 0),
            failure_count=self._failure_count.get(base.id, 0),
        )

    def get_all_hybrid(self) -> list[HybridExample]:
        """Return all examples with all vector representations and metadata.

        Returns:
            List of HybridExample instances.
        """
        results = []
        for base in self.get_all():
            results.append(
                HybridExample(
                    id=base.id,
                    input_text=base.input_text,
                    output=base.output,
                    lexical_vector=base.vector,
                    semantic_vector=self._semantic_vectors.get(base.id),
                    weight=base.weight,
                    feedback_count=base.feedback_count,
                    correct_count=base.correct_count,
                    metadata=base.metadata,
                    created_at=self._created_at.get(base.id, 0.0),
                    last_used_at=self._last_used_at.get(base.id, 0.0),
                    use_count=self._use_count.get(base.id, 0),
                    success_count=self._success_count.get(base.id, 0),
                    failure_count=self._failure_count.get(base.id, 0),
                )
            )
        return results

    def has_semantic_vectors(self) -> bool:
        """Check if any examples have semantic vectors."""
        return len(self._semantic_vectors) > 0

    def record_use(self, example_id: int) -> bool:
        """Record that an example was used in a prediction.

        Updates last_used_at and increments use_count.

        Args:
            example_id: The example's ID.

        Returns:
            True if the example was found and updated.
        """
        if self.get(example_id) is not None:
            self._last_used_at[example_id] = time.time()
            self._use_count[example_id] = self._use_count.get(example_id, 0) + 1
            return True
        return False

    def record_success(self, example_id: int) -> bool:
        """Record a successful use of an example.

        Args:
            example_id: The example's ID.

        Returns:
            True if the example was found and updated.
        """
        if self.get(example_id) is not None:
            self._success_count[example_id] = self._success_count.get(example_id, 0) + 1
            return True
        return False

    def record_failure(self, example_id: int) -> bool:
        """Record a failed use of an example.

        Args:
            example_id: The example's ID.

        Returns:
            True if the example was found and updated.
        """
        if self.get(example_id) is not None:
            self._failure_count[example_id] = self._failure_count.get(example_id, 0) + 1
            return True
        return False

    def get_usage_stats(self, example_id: int) -> dict[str, Any] | None:
        """Return usage statistics for an example.

        Args:
            example_id: The example's ID.

        Returns:
            Dict with usage stats, or None if not found.
        """
        if self.get(example_id) is None:
            return None
        total = self._success_count.get(example_id, 0) + self._failure_count.get(example_id, 0)
        return {
            "created_at": self._created_at.get(example_id, 0.0),
            "last_used_at": self._last_used_at.get(example_id, 0.0),
            "use_count": self._use_count.get(example_id, 0),
            "success_count": self._success_count.get(example_id, 0),
            "failure_count": self._failure_count.get(example_id, 0),
            "success_rate": (
                self._success_count.get(example_id, 0) / total if total > 0 else 0.5
            ),
        }

    def remove(self, example_id: int) -> bool:
        """Remove an example and all associated data.

        Args:
            example_id: The example's ID.

        Returns:
            True if found and removed.
        """
        removed = super().remove(example_id)
        if removed:
            self._semantic_vectors.pop(example_id, None)
            self._created_at.pop(example_id, None)
            self._last_used_at.pop(example_id, None)
            self._use_count.pop(example_id, None)
            self._success_count.pop(example_id, None)
            self._failure_count.pop(example_id, None)
        return removed

    def clear(self) -> None:
        """Remove all examples and all associated data."""
        super().clear()
        self._semantic_vectors.clear()
        self._created_at.clear()
        self._last_used_at.clear()
        self._use_count.clear()
        self._success_count.clear()
        self._failure_count.clear()

    def save(self, path: Path) -> None:
        """Save memory state including all V2/V2.1 data to JSON.

        Perserves: lexical vectors, semantic vectors, usage metadata,
        weights, feedback counts. Backward compatible with V1/V2 formats.

        Args:
            path: File path to save to.
        """
        data: dict[str, Any] = {
            "next_id": self._next_id,
            "examples": [],
        }

        for ex in self._examples:
            ex_data: dict[str, Any] = {
                "id": ex.id,
                "input_text": ex.input_text,
                "output": ex.output,
                "vector": ex.vector.features,
                "norm": ex.vector.norm,
                "weight": ex.weight,
                "feedback_count": ex.feedback_count,
                "correct_count": ex.correct_count,
                "metadata": ex.metadata,
            }
            # Include semantic vector if present
            sem = self._semantic_vectors.get(ex.id)
            if sem is not None:
                ex_data["semantic_vector"] = sem

            # V2.1: Include usage metadata
            ex_data["created_at"] = self._created_at.get(ex.id, 0.0)
            ex_data["last_used_at"] = self._last_used_at.get(ex.id, 0.0)
            ex_data["use_count"] = self._use_count.get(ex.id, 0)
            ex_data["success_count"] = self._success_count.get(ex.id, 0)
            ex_data["failure_count"] = self._failure_count.get(ex.id, 0)

            data["examples"].append(ex_data)

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> HybridMemory:
        """Load memory state from a JSON file.

        Handles V1 (no semantic), V2 (with semantic), and V2.1
        (with semantic + usage metadata) formats. Missing fields
        default to neutral values.

        Args:
            path: File path to load from.

        Returns:
            Restored HybridMemory instance.
        """
        data = json.loads(path.read_text(encoding="utf-8"))
        memory = cls()
        memory._next_id = data["next_id"]

        for ex_data in data["examples"]:
            vector = FeatureVector(
                features=ex_data["vector"],
                norm=ex_data["norm"],
            )
            example = LearnedExample(
                id=ex_data["id"],
                input_text=ex_data["input_text"],
                output=ex_data["output"],
                vector=vector,
                weight=ex_data["weight"],
                feedback_count=ex_data["feedback_count"],
                correct_count=ex_data["correct_count"],
                metadata=ex_data.get("metadata", {}),
            )
            memory._examples.append(example)

            # Load semantic vector if present (V2+)
            sem = ex_data.get("semantic_vector")
            if sem is not None:
                memory._semantic_vectors[example.id] = sem

            # V2.1: Load usage metadata with backward-compatible defaults
            now = time.time()
            memory._created_at[example.id] = ex_data.get("created_at", now)
            memory._last_used_at[example.id] = ex_data.get("last_used_at", now)
            memory._use_count[example.id] = ex_data.get("use_count", 0)
            memory._success_count[example.id] = ex_data.get("success_count", 0)
            memory._failure_count[example.id] = ex_data.get("failure_count", 0)

        return memory
