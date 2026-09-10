"""Tests for ExampleMemory.

Covers adding, retrieving, updating, feedback recording, persistence,
clearing, and removing examples.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from core.learner.feature_extractor import FeatureVector
from core.learner.memory import ExampleMemory, LearnedExample

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _vec(features: dict[str, float] | None = None) -> FeatureVector:
    """Create a FeatureVector with optional features."""
    return FeatureVector(features=features or {"token": 1.0})


# ---------------------------------------------------------------------------
# Add examples
# ---------------------------------------------------------------------------


class TestAddExample:
    """Test adding examples to memory."""

    def test_add_returns_learned_example(self) -> None:
        """add() returns a LearnedExample with correct fields."""
        mem = ExampleMemory()
        ex = mem.add("hello", "greeting", _vec())
        assert isinstance(ex, LearnedExample)
        assert ex.input_text == "hello"
        assert ex.output == "greeting"

    def test_add_assigns_increasing_ids(self) -> None:
        """Each added example gets a unique, incrementing ID."""
        mem = ExampleMemory()
        ids = [mem.add(f"input{i}", f"out{i}", _vec()).id for i in range(5)]
        assert ids == [0, 1, 2, 3, 4]

    def test_add_increments_count(self) -> None:
        """count() increases after each add."""
        mem = ExampleMemory()
        assert mem.count() == 0
        mem.add("a", "b", _vec())
        assert mem.count() == 1
        mem.add("c", "d", _vec())
        assert mem.count() == 2

    def test_add_with_metadata(self) -> None:
        """Metadata is stored on the example."""
        mem = ExampleMemory()
        ex = mem.add("a", "b", _vec(), metadata={"source": "test"})
        assert ex.metadata == {"source": "test"}

    def test_add_with_custom_weight(self) -> None:
        """Custom initial weight is respected."""
        mem = ExampleMemory()
        ex = mem.add("a", "b", _vec(), weight=3.0)
        assert ex.weight == 3.0


# ---------------------------------------------------------------------------
# Get by ID
# ---------------------------------------------------------------------------


class TestGetById:
    """Test retrieving examples by ID."""

    def test_get_existing(self) -> None:
        """get() returns the example with matching ID."""
        mem = ExampleMemory()
        added = mem.add("hello", "world", _vec())
        retrieved = mem.get(added.id)
        assert retrieved is added

    def test_get_nonexistent(self) -> None:
        """get() returns None for an ID that does not exist."""
        mem = ExampleMemory()
        assert mem.get(999) is None

    def test_get_after_multiple_adds(self) -> None:
        """get() correctly retrieves from a set of examples."""
        mem = ExampleMemory()
        examples = [mem.add(f"in{i}", f"out{i}", _vec()) for i in range(10)]
        for ex in examples:
            assert mem.get(ex.id) is ex


# ---------------------------------------------------------------------------
# Update weight
# ---------------------------------------------------------------------------


class TestUpdateWeight:
    """Test weight update mechanics."""

    def test_positive_delta_increases_weight(self) -> None:
        """A positive delta increases the weight."""
        mem = ExampleMemory()
        ex = mem.add("a", "b", _vec(), weight=1.0)
        mem.update_weight(ex.id, 0.5)
        assert ex.weight == pytest.approx(1.5)

    def test_negative_delta_decreases_weight(self) -> None:
        """A negative delta decreases the weight."""
        mem = ExampleMemory()
        ex = mem.add("a", "b", _vec(), weight=2.0)
        mem.update_weight(ex.id, -0.5)
        assert ex.weight == pytest.approx(1.5)

    def test_weight_floor(self) -> None:
        """Weight cannot drop below 0.1."""
        mem = ExampleMemory()
        ex = mem.add("a", "b", _vec(), weight=0.2)
        mem.update_weight(ex.id, -0.5)
        assert ex.weight == pytest.approx(0.1)

    def test_increments_feedback_count(self) -> None:
        """update_weight increments feedback_count."""
        mem = ExampleMemory()
        ex = mem.add("a", "b", _vec())
        mem.update_weight(ex.id, 0.1)
        mem.update_weight(ex.id, -0.1)
        assert ex.feedback_count == 2

    def test_positive_delta_increments_correct_count(self) -> None:
        """Positive delta increments correct_count."""
        mem = ExampleMemory()
        ex = mem.add("a", "b", _vec())
        mem.update_weight(ex.id, 0.1)
        assert ex.correct_count == 1

    def test_nonexistent_id(self) -> None:
        """update_weight returns False for unknown ID."""
        mem = ExampleMemory()
        assert mem.update_weight(999, 0.5) is False


# ---------------------------------------------------------------------------
# Record feedback
# ---------------------------------------------------------------------------


class TestRecordFeedback:
    """Test feedback recording behavior."""

    def test_correct_feedback_increases_weight(self) -> None:
        """Correct feedback increases weight by 0.05."""
        mem = ExampleMemory()
        ex = mem.add("a", "b", _vec(), weight=1.0)
        mem.record_feedback(ex.id, correct=True)
        assert ex.weight == pytest.approx(1.05)

    def test_incorrect_feedback_decreases_weight(self) -> None:
        """Incorrect feedback decreases weight by 0.1."""
        mem = ExampleMemory()
        ex = mem.add("a", "b", _vec(), weight=1.0)
        mem.record_feedback(ex.id, correct=False)
        assert ex.weight == pytest.approx(0.9)

    def test_weight_ceiling(self) -> None:
        """Weight cannot exceed 5.0 on correct feedback."""
        mem = ExampleMemory()
        ex = mem.add("a", "b", _vec(), weight=4.98)
        mem.record_feedback(ex.id, correct=True)
        assert ex.weight == pytest.approx(5.0)

    def test_weight_floor_on_incorrect(self) -> None:
        """Weight cannot drop below 0.3 on incorrect feedback."""
        mem = ExampleMemory()
        ex = mem.add("a", "b", _vec(), weight=0.35)
        mem.record_feedback(ex.id, correct=False)
        assert ex.weight == pytest.approx(0.3)

    def test_accuracy_property(self) -> None:
        """accuracy returns correct_count / feedback_count."""
        mem = ExampleMemory()
        ex = mem.add("a", "b", _vec())
        mem.record_feedback(ex.id, correct=True)
        mem.record_feedback(ex.id, correct=True)
        mem.record_feedback(ex.id, correct=False)
        assert ex.accuracy == pytest.approx(2 / 3)

    def test_accuracy_zero_feedback(self) -> None:
        """accuracy returns 0.0 when no feedback recorded."""
        ex = LearnedExample(id=0, input_text="a", output="b", vector=_vec())
        assert ex.accuracy == pytest.approx(0.0)

    def test_nonexistent_id(self) -> None:
        """record_feedback returns False for unknown ID."""
        mem = ExampleMemory()
        assert mem.record_feedback(999, correct=True) is False


# ---------------------------------------------------------------------------
# Save / Load persistence
# ---------------------------------------------------------------------------


class TestPersistence:
    """Test save/load round-trip for ExampleMemory."""

    def test_save_load_round_trip(self) -> None:
        """Saved memory loads back with identical examples."""
        mem = ExampleMemory()
        mem.add("hello", "greeting", _vec({"hello": 1.0, "world": 0.5}))
        mem.add("goodbye", "farewell", _vec({"goodbye": 1.0}))
        mem.record_feedback(0, correct=True)
        mem.record_feedback(1, correct=False)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "memory.json"
            mem.save(path)
            loaded = ExampleMemory.load(path)

        assert loaded.count() == mem.count()
        for orig, loaded_ex in zip(mem.get_all(), loaded.get_all(), strict=True):
            assert orig.id == loaded_ex.id
            assert orig.input_text == loaded_ex.input_text
            assert orig.output == loaded_ex.output
            assert orig.weight == pytest.approx(loaded_ex.weight)
            assert orig.feedback_count == loaded_ex.feedback_count

    def test_save_creates_parent_dirs(self) -> None:
        """save() creates intermediate directories if needed."""
        mem = ExampleMemory()
        mem.add("a", "b", _vec())
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sub" / "dir" / "memory.json"
            mem.save(path)
            assert path.exists()

    def test_load_returns_empty_memory(self) -> None:
        """Loading an empty memory yields a valid empty memory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "empty.json"
            ExampleMemory().save(path)
            loaded = ExampleMemory.load(path)
        assert loaded.count() == 0


# ---------------------------------------------------------------------------
# Clear and remove
# ---------------------------------------------------------------------------


class TestClearAndRemove:
    """Test clearing all examples and removing individual ones."""

    def test_clear(self) -> None:
        """clear() removes all examples and resets ID counter."""
        mem = ExampleMemory()
        mem.add("a", "b", _vec())
        mem.add("c", "d", _vec())
        mem.clear()
        assert mem.count() == 0
        assert mem.get_all() == []

    def test_remove_existing(self) -> None:
        """remove() deletes an example by ID and returns True."""
        mem = ExampleMemory()
        ex = mem.add("a", "b", _vec())
        assert mem.remove(ex.id) is True
        assert mem.count() == 0
        assert mem.get(ex.id) is None

    def test_remove_nonexistent(self) -> None:
        """remove() returns False for an unknown ID."""
        mem = ExampleMemory()
        assert mem.remove(999) is False

    def test_remove_does_not_affect_others(self) -> None:
        """Removing one example leaves others intact."""
        mem = ExampleMemory()
        a = mem.add("a", "a_out", _vec())
        b = mem.add("b", "b_out", _vec())
        c = mem.add("c", "c_out", _vec())
        mem.remove(b.id)
        assert mem.count() == 2
        assert mem.get(a.id) is not None
        assert mem.get(c.id) is not None

    def test_get_all_returns_copy(self) -> None:
        """get_all() returns a list copy, not the internal list."""
        mem = ExampleMemory()
        mem.add("a", "b", _vec())
        all_ex = mem.get_all()
        all_ex.clear()
        assert mem.count() == 1
