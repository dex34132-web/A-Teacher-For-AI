"""Tests for HybridMemory.

Tests the extended memory that stores both TF-IDF and semantic vectors.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from core.learner.feature_extractor import FeatureVector
from core.learner.hybrid_memory import HybridExample, HybridMemory

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _make_vector(features: dict[str, float] | None = None) -> FeatureVector:
    return FeatureVector(features=features or {"test": 1.0})


# ---------------------------------------------------------------------------
# HybridExample tests
# ---------------------------------------------------------------------------


class TestHybridExample:
    """Test the HybridExample dataclass."""

    def test_creation(self):
        vec = _make_vector()
        ex = HybridExample(id=0, input_text="hello", output="greeting", lexical_vector=vec)
        assert ex.id == 0
        assert ex.input_text == "hello"
        assert ex.output == "greeting"
        assert ex.semantic_vector is None
        assert ex.weight == 1.0

    def test_accuracy_no_feedback(self):
        vec = _make_vector()
        ex = HybridExample(id=0, input_text="x", output="y", lexical_vector=vec)
        assert ex.accuracy == 0.0

    def test_accuracy_with_feedback(self):
        vec = _make_vector()
        ex = HybridExample(
            id=0, input_text="x", output="y", lexical_vector=vec,
            feedback_count=10, correct_count=7,
        )
        assert ex.accuracy == 0.7


# ---------------------------------------------------------------------------
# HybridMemory tests
# ---------------------------------------------------------------------------


class TestHybridMemory:
    """Test HybridMemory operations."""

    def test_add_without_semantic(self):
        mem = HybridMemory()
        vec = _make_vector({"a": 1.0})
        ex = mem.add(input_text="hello", output="greeting", vector=vec)
        assert ex.id == 0
        assert ex.semantic_vector is None
        assert ex.lexical_vector == vec

    def test_add_with_semantic(self):
        mem = HybridMemory()
        vec = _make_vector()
        sem = [0.1, 0.2, 0.3]
        ex = mem.add(input_text="hello", output="greeting", vector=vec, semantic_vector=sem)
        assert ex.semantic_vector == [0.1, 0.2, 0.3]

    def test_get_hybrid(self):
        mem = HybridMemory()
        vec = _make_vector()
        sem = [1.0, 2.0]
        mem.add(input_text="test", output="out", vector=vec, semantic_vector=sem)
        ex = mem.get_hybrid(0)
        assert ex is not None
        assert ex.semantic_vector == [1.0, 2.0]

    def test_get_hybrid_missing(self):
        mem = HybridMemory()
        assert mem.get_hybrid(999) is None

    def test_get_all_hybrid(self):
        mem = HybridMemory()
        vec = _make_vector()
        mem.add(input_text="a", output="1", vector=vec, semantic_vector=[1.0])
        mem.add(input_text="b", output="2", vector=vec)
        all_ex = mem.get_all_hybrid()
        assert len(all_ex) == 2
        assert all_ex[0].semantic_vector == [1.0]
        assert all_ex[1].semantic_vector is None

    def test_set_semantic_vector(self):
        mem = HybridMemory()
        vec = _make_vector()
        mem.add(input_text="x", output="y", vector=vec)
        result = mem.set_semantic_vector(0, [5.0, 6.0])
        assert result is True
        ex = mem.get_hybrid(0)
        assert ex.semantic_vector == [5.0, 6.0]

    def test_set_semantic_vector_missing(self):
        mem = HybridMemory()
        result = mem.set_semantic_vector(999, [1.0])
        assert result is False

    def test_has_semantic_vectors(self):
        mem = HybridMemory()
        vec = _make_vector()
        assert mem.has_semantic_vectors() is False
        mem.add(input_text="x", output="y", vector=vec, semantic_vector=[1.0])
        assert mem.has_semantic_vectors() is True

    def test_remove_cleans_semantic(self):
        mem = HybridMemory()
        vec = _make_vector()
        mem.add(input_text="x", output="y", vector=vec, semantic_vector=[1.0])
        assert mem.remove(0) is True
        assert mem.has_semantic_vectors() is False

    def test_clear_cleans_semantic(self):
        mem = HybridMemory()
        vec = _make_vector()
        mem.add(input_text="x", output="y", vector=vec, semantic_vector=[1.0])
        mem.clear()
        assert mem.has_semantic_vectors() is False
        assert mem.count() == 0

    def test_add_multiple(self):
        mem = HybridMemory()
        vec = _make_vector()
        for i in range(5):
            mem.add(input_text=f"in_{i}", output=f"out_{i}", vector=vec, semantic_vector=[float(i)])
        assert mem.count() == 5
        ex = mem.get_hybrid(3)
        assert ex.semantic_vector == [3.0]


# ---------------------------------------------------------------------------
# HybridMemory persistence tests
# ---------------------------------------------------------------------------


class TestHybridMemoryPersistence:
    """Test save/load with semantic vectors."""

    def test_save_load_with_semantics(self):
        mem = HybridMemory()
        vec = _make_vector({"a": 1.0, "b": 2.0})
        mem.add(input_text="hello", output="greeting", vector=vec, semantic_vector=[0.1, 0.2, 0.3])
        mem.add(input_text="world", output="earth", vector=vec)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "mem.json"
            mem.save(path)
            loaded = HybridMemory.load(path)

        assert loaded.count() == 2
        ex0 = loaded.get_hybrid(0)
        assert ex0.semantic_vector == [0.1, 0.2, 0.3]
        ex1 = loaded.get_hybrid(1)
        assert ex1.semantic_vector is None

    def test_load_v1_format(self):
        """Test loading V1 format (no semantic vectors)."""
        v1_data = {
            "next_id": 2,
            "examples": [
                {
                    "id": 0,
                    "input_text": "hello",
                    "output": "greeting",
                    "vector": {"a": 1.0},
                    "norm": 1.0,
                    "weight": 1.0,
                    "feedback_count": 0,
                    "correct_count": 0,
                    "metadata": {},
                },
                {
                    "id": 1,
                    "input_text": "world",
                    "output": "earth",
                    "vector": {"b": 2.0},
                    "norm": 2.0,
                    "weight": 1.0,
                    "feedback_count": 0,
                    "correct_count": 0,
                    "metadata": {},
                },
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "mem.json"
            path.write_text(json.dumps(v1_data), encoding="utf-8")
            loaded = HybridMemory.load(path)

        assert loaded.count() == 2
        assert loaded.get_hybrid(0).semantic_vector is None
        assert loaded.get_hybrid(1).semantic_vector is None

    def test_save_inherits_from_parent(self):
        """Test that HybridMemory.save includes parent fields."""
        mem = HybridMemory()
        vec = _make_vector({"x": 1.0})
        ex = mem.add(input_text="test", output="out", vector=vec, weight=0.8)
        # Modify the underlying LearnedExample directly (HybridExample is a copy)
        base_ex = mem.get(ex.id)
        base_ex.feedback_count = 3
        base_ex.correct_count = 2

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "mem.json"
            mem.save(path)
            data = json.loads(path.read_text(encoding="utf-8"))

        ex_data = data["examples"][0]
        assert ex_data["weight"] == 0.8
        assert ex_data["feedback_count"] == 3
        assert ex_data["correct_count"] == 2

    def test_roundtrip_preserves_ids(self):
        mem = HybridMemory()
        vec = _make_vector()
        mem.add(input_text="a", output="1", vector=vec, semantic_vector=[1.0])
        mem.add(input_text="b", output="2", vector=vec, semantic_vector=[2.0])

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "mem.json"
            mem.save(path)
            loaded = HybridMemory.load(path)

        assert loaded._next_id == 2
        assert loaded.get_hybrid(0).id == 0
        assert loaded.get_hybrid(1).id == 1
