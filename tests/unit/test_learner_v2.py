"""Tests for HybridSimilarityLearner (V2).

Tests the hybrid learner with and without semantic encoder,
ensuring V1 fallback works correctly.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from core.learner.base import LearningInput, LearningMode, LearningStatus
from core.learner.learner_v2 import HybridSimilarityLearner
from core.learner.semantic_encoder import SemanticEncoder

# ---------------------------------------------------------------------------
# Stub encoder for deterministic testing
# ---------------------------------------------------------------------------


class StubSemanticEncoder(SemanticEncoder):
    """Deterministic encoder based on character overlap for testing."""

    def __init__(self, dim: int = 4) -> None:
        self._dim = dim

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [self.encode_single(t) for t in texts]

    def encode_single(self, text: str) -> list[float]:
        vec = [0.0] * self._dim
        for i, ch in enumerate(text.lower()):
            vec[i % self._dim] += ord(ch) % 10
        # Normalize
        norm = sum(x * x for x in vec) ** 0.5
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec

    @property
    def dimension(self) -> int:
        return self._dim


# ---------------------------------------------------------------------------
# V2 Learner basic tests (no semantic encoder)
# ---------------------------------------------------------------------------


class TestHybridLearnerV1Fallback:
    """Test that V2 degrades to V1 behavior without semantic encoder."""

    def test_init_without_encoder(self):
        learner = HybridSimilarityLearner()
        assert learner.has_semantic is False
        assert learner.encoder is None

    def test_mode_is_online(self):
        learner = HybridSimilarityLearner()
        assert learner.mode == LearningMode.ONLINE

    def test_parameters(self):
        learner = HybridSimilarityLearner(k=3)
        params = learner.parameters
        assert params["k"] == 3
        assert params["has_semantic_encoder"] is False
        assert params["semantic_dimension"] is None

    def test_learn(self):
        learner = HybridSimilarityLearner()
        result = learner.learn(LearningInput(
            observation={"input": "hello", "output": "greeting"},
        ))
        assert result.status == LearningStatus.UPDATED
        assert result.delta["has_semantic"] is False
        assert learner.memory.count() == 1

    def test_predict_empty_memory(self):
        learner = HybridSimilarityLearner()
        pred = learner.predict("hello")
        assert pred.output == ""
        assert pred.confidence == 0.0

    def test_predict_after_training(self):
        learner = HybridSimilarityLearner()
        for text, out in [("create list", "list"), ("create dict", "dict")]:
            learner.learn(LearningInput(observation={"input": text, "output": out}))
        pred = learner.predict("create list")
        assert pred.output == "list"
        assert pred.confidence > 0.0

    def test_feedback(self):
        learner = HybridSimilarityLearner()
        learner.learn(LearningInput(observation={"input": "hello", "output": "greeting"}))
        pred = learner.predict("hello")
        changes = learner.feedback("hello", pred.output, correct=True)
        assert changes["correct"] is True

    def test_reset(self):
        learner = HybridSimilarityLearner()
        learner.learn(LearningInput(observation={"input": "x", "output": "y"}))
        learner.reset()
        assert learner.memory.count() == 0
        assert learner.parameters["total_predictions"] == 0

    def test_empty_input_error(self):
        learner = HybridSimilarityLearner()
        result = learner.learn(LearningInput(observation={"input": "", "output": ""}))
        assert result.status == LearningStatus.ERROR


# ---------------------------------------------------------------------------
# V2 Learner with semantic encoder
# ---------------------------------------------------------------------------


class TestHybridLearnerWithSemantic:
    """Test V2 with a semantic encoder present."""

    def test_init_with_encoder(self):
        enc = StubSemanticEncoder(dim=4)
        learner = HybridSimilarityLearner(semantic_encoder=enc)
        assert learner.has_semantic is True
        assert learner.encoder is enc

    def test_parameters_with_encoder(self):
        enc = StubSemanticEncoder(dim=4)
        learner = HybridSimilarityLearner(semantic_encoder=enc)
        params = learner.parameters
        assert params["has_semantic_encoder"] is True
        assert params["semantic_dimension"] == 4

    def test_learn_stores_semantic(self):
        enc = StubSemanticEncoder(dim=4)
        learner = HybridSimilarityLearner(semantic_encoder=enc)
        learner.learn(LearningInput(
            observation={"input": "hello", "output": "greeting"},
        ))
        ex = learner.memory.get_hybrid(0)
        assert ex.semantic_vector is not None
        assert len(ex.semantic_vector) == 4

    def test_predict_uses_semantic(self):
        enc = StubSemanticEncoder(dim=4)
        learner = HybridSimilarityLearner(semantic_encoder=enc)
        for text, out in [("create list", "list"), ("create dict", "dict")]:
            learner.learn(LearningInput(observation={"input": text, "output": out}))
        pred = learner.predict("create list")
        assert pred.output in ("list", "dict")
        assert pred.confidence > 0.0

    def test_feedback_adds_correction_with_semantic(self):
        enc = StubSemanticEncoder(dim=4)
        learner = HybridSimilarityLearner(semantic_encoder=enc)
        learner.learn(LearningInput(observation={"input": "x", "output": "wrong"}))
        learner.predict("x")
        changes = learner.feedback("x", "wrong", correct=False, actual_output="correct")
        assert "new_example_id" in changes
        assert learner.memory.count() == 2

    def test_correction_has_semantic_vector(self):
        enc = StubSemanticEncoder(dim=4)
        learner = HybridSimilarityLearner(semantic_encoder=enc)
        learner.learn(LearningInput(observation={"input": "x", "output": "wrong"}))
        learner.feedback("x", "wrong", correct=False, actual_output="right")
        ex = learner.memory.get_hybrid(1)
        assert ex.semantic_vector is not None

    def test_custom_weights(self):
        enc = StubSemanticEncoder(dim=4)
        learner = HybridSimilarityLearner(
            semantic_encoder=enc,
            lexical_weight=0.7,
            semantic_weight=0.3,
        )
        params = learner.parameters
        assert params["lexical_weight"] == pytest.approx(0.7)
        assert params["semantic_weight"] == pytest.approx(0.3)


# ---------------------------------------------------------------------------
# V2 Learner persistence tests
# ---------------------------------------------------------------------------


class TestHybridLearnerPersistence:
    """Test save/load of V2 learner."""

    def test_save_load_without_encoder(self):
        learner = HybridSimilarityLearner(k=3)
        learner.learn(LearningInput(observation={"input": "hello", "output": "greeting"}))

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "learner_state"
            learner.save_state(str(path))

            loaded = HybridSimilarityLearner.load_state(str(path))

        assert loaded._k == 3
        assert loaded.memory.count() == 1

    def test_save_load_with_encoder(self):
        enc = StubSemanticEncoder(dim=4)
        learner = HybridSimilarityLearner(semantic_encoder=enc)
        learner.learn(LearningInput(observation={"input": "hello", "output": "greeting"}))

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "learner_state"
            learner.save_state(str(path))

            enc2 = StubSemanticEncoder(dim=4)
            loaded = HybridSimilarityLearner.load_state(str(path), semantic_encoder=enc2)

        assert loaded.has_semantic is True
        ex = loaded.memory.get_hybrid(0)
        assert ex.semantic_vector is not None

    def test_loaded_learner_can_predict(self):
        enc = StubSemanticEncoder(dim=4)
        learner = HybridSimilarityLearner(semantic_encoder=enc)
        learner.learn(LearningInput(observation={"input": "hello", "output": "greeting"}))

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "learner_state"
            learner.save_state(str(path))

            enc2 = StubSemanticEncoder(dim=4)
            loaded = HybridSimilarityLearner.load_state(str(path), semantic_encoder=enc2)

        pred = loaded.predict("hello")
        assert pred.output == "greeting"

    def test_loaded_learner_can_feedback(self):
        enc = StubSemanticEncoder(dim=4)
        learner = HybridSimilarityLearner(semantic_encoder=enc)
        learner.learn(LearningInput(observation={"input": "x", "output": "y"}))

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "learner_state"
            learner.save_state(str(path))

            enc2 = StubSemanticEncoder(dim=4)
            loaded = HybridSimilarityLearner.load_state(str(path), semantic_encoder=enc2)

        changes = loaded.feedback("x", "y", correct=True)
        assert changes["correct"] is True
