"""In-memory storage for learned examples.

Stores feature vectors alongside their expected outputs and metadata.
This is the learner's working memory - it holds all examples the learner
has seen and can retrieve them by similarity.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.learner.feature_extractor import FeatureVector


@dataclass
class LearnedExample:
    """A single learned example in memory.

    Attributes:
        id: Unique identifier.
        input_text: Original input text.
        output: Expected output/label.
        vector: Feature vector representation.
        weight: Confidence/weight of this example (updated by feedback).
        feedback_count: Number of times feedback was received.
        correct_count: Number of times this example was confirmed correct.
        metadata: Additional information.
    """

    id: int
    input_text: str
    output: str
    vector: FeatureVector
    weight: float = 1.0
    feedback_count: int = 0
    correct_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def accuracy(self) -> float:
        """Return the accuracy ratio for this example."""
        if self.feedback_count == 0:
            return 0.0
        return self.correct_count / self.feedback_count


class ExampleMemory:
    """In-memory store for learned examples.

    This memory stores input-output pairs along with their feature
    vectors. It supports similarity-based retrieval and weight updates
    based on feedback.
    """

    def __init__(self) -> None:
        """Initialize empty memory."""
        self._examples: list[LearnedExample] = []
        self._next_id: int = 0

    def add(
        self,
        input_text: str,
        output: str,
        vector: FeatureVector,
        weight: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> LearnedExample:
        """Add a new example to memory.

        Args:
            input_text: Original input text.
            output: Expected output/label.
            vector: Feature vector for the input.
            weight: Initial weight/confidence.
            metadata: Optional additional information.

        Returns:
            The created LearnedExample.
        """
        example = LearnedExample(
            id=self._next_id,
            input_text=input_text,
            output=output,
            vector=vector,
            weight=weight,
            metadata=metadata or {},
        )
        self._examples.append(example)
        self._next_id += 1
        return example

    def get(self, example_id: int) -> LearnedExample | None:
        """Retrieve an example by ID.

        Args:
            example_id: The example's unique ID.

        Returns:
            The example if found, None otherwise.
        """
        for example in self._examples:
            if example.id == example_id:
                return example
        return None

    def update_weight(self, example_id: int, delta: float) -> bool:
        """Update an example's weight.

        Args:
            example_id: The example's ID.
            delta: Amount to add to weight (can be negative).

        Returns:
            True if the example was found and updated.
        """
        for example in self._examples:
            if example.id == example_id:
                example.weight = max(0.1, example.weight + delta)
                example.feedback_count += 1
                if delta > 0:
                    example.correct_count += 1
                return True
        return False

    def record_feedback(self, example_id: int, correct: bool) -> bool:
        """Record feedback for an example.

        Weight adjustments are deliberately conservative:
        - Correct feedback: +0.05 (max 5.0)
        - Incorrect feedback: -0.1 (min 0.3)

        The minimum weight is 0.3 (not 0) so that examples are never
        completely silenced by a few rounds of bad feedback.

        Args:
            example_id: The example's ID.
            correct: Whether the prediction was correct.

        Returns:
            True if the example was found and updated.
        """
        for example in self._examples:
            if example.id == example_id:
                example.feedback_count += 1
                if correct:
                    example.correct_count += 1
                    example.weight = min(5.0, example.weight + 0.05)
                else:
                    example.weight = max(0.3, example.weight - 0.1)
                return True
        return False

    def get_all(self) -> list[LearnedExample]:
        """Return all stored examples.

        Returns:
            List of all learned examples.
        """
        return list(self._examples)

    def count(self) -> int:
        """Return the number of stored examples."""
        return len(self._examples)

    def clear(self) -> None:
        """Remove all examples."""
        self._examples.clear()
        self._next_id = 0

    def remove(self, example_id: int) -> bool:
        """Remove an example by ID.

        Args:
            example_id: The example's ID.

        Returns:
            True if the example was found and removed.
        """
        for i, example in enumerate(self._examples):
            if example.id == example_id:
                self._examples.pop(i)
                return True
        return False

    def save(self, path: Path) -> None:
        """Save memory state to a JSON file.

        Args:
            path: File path to save to.
        """
        data = {
            "next_id": self._next_id,
            "examples": [
                {
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
                for ex in self._examples
            ],
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> ExampleMemory:
        """Load memory state from a JSON file.

        Args:
            path: File path to load from.

        Returns:
            Restored ExampleMemory instance.
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

        return memory
