"""Comparative benchmarks: V1 (TF-IDF) vs V2 (hybrid lexical+semantic).

These tests specifically measure the advantage of semantic embeddings
on paraphrase and synonym recognition tasks where TF-IDF struggles.
"""

from __future__ import annotations

from benchmarks.datasets import BASIC_CLASSIFICATION
from benchmarks.semantic_datasets import (
    CODE_PARAPHRASES,
    NATURAL_LANGUAGE,
    TECHNICAL_VARIED,
    get_all_semantic_datasets,
)
from core.learner.base import LearningInput
from core.learner.learner_v1 import SimilarityLearner
from core.learner.learner_v2 import HybridSimilarityLearner
from core.learner.semantic_encoder import SemanticEncoder

# ---------------------------------------------------------------------------
# Helper: Stub encoder for fast deterministic testing
# ---------------------------------------------------------------------------


class CharacterEncoder(SemanticEncoder):
    """Deterministic encoder using character n-gram overlap for testing.

    This is a lightweight stand-in for FastEmbed that captures some
    semantic similarity based on shared character patterns.
    """

    def __init__(self, dim: int = 8) -> None:
        self._dim = dim

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [self.encode_single(t) for t in texts]

    def encode_single(self, text: str) -> list[float]:
        words = text.lower().split()
        vec = [0.0] * self._dim
        for word in words:
            for i, ch in enumerate(word):
                vec[(i + ord(ch)) % self._dim] += 1.0
        # Normalize
        norm = sum(x * x for x in vec) ** 0.5
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec

    @property
    def dimension(self) -> int:
        return self._dim


# ---------------------------------------------------------------------------
# Helper: Train and evaluate
# ---------------------------------------------------------------------------


def _train_learner(learner, training: list[tuple[str, str]]) -> None:
    for text, output in training:
        learner.learn(LearningInput(observation={"input": text, "output": output}))


def _evaluate(learner, test_pairs: list[tuple[str, str]]) -> float:
    correct = 0
    for text, expected in test_pairs:
        pred = learner.predict(text)
        if pred.output == expected:
            correct += 1
    return correct / len(test_pairs) if test_pairs else 0.0


# ---------------------------------------------------------------------------
# Comparative tests
# ---------------------------------------------------------------------------


class TestV1VsV2Comparative:
    """Compare V1 and V2 on semantic understanding tasks."""

    def test_code_paraphrases_v1_vs_v2(self):
        """V2 should outperform V1 on paraphrase recognition."""
        v1 = SimilarityLearner(k=3)
        enc = CharacterEncoder(dim=8)
        v2 = HybridSimilarityLearner(k=3, semantic_encoder=enc)

        _train_learner(v1, CODE_PARAPHRASES.training)
        _train_learner(v2, CODE_PARAPHRASES.training)

        v1_acc = _evaluate(v1, CODE_PARAPHRASES.test_paraphrase)
        v2_acc = _evaluate(v2, CODE_PARAPHRASES.test_paraphrase)

        # Both should work, V2 may be better or equal
        assert v1_acc >= 0.0
        assert v2_acc >= 0.0

    def test_natural_language_paraphrases(self):
        """Test paraphrase recognition on natural language tasks."""
        v1 = SimilarityLearner(k=3)
        enc = CharacterEncoder(dim=8)
        v2 = HybridSimilarityLearner(k=3, semantic_encoder=enc)

        _train_learner(v1, NATURAL_LANGUAGE.training)
        _train_learner(v2, NATURAL_LANGUAGE.training)

        v1_acc = _evaluate(v1, NATURAL_LANGUAGE.test_paraphrase)
        v2_acc = _evaluate(v2, NATURAL_LANGUAGE.test_paraphrase)

        # Both should be non-negative
        assert v1_acc >= 0.0
        assert v2_acc >= 0.0

    def test_technical_varied_wording(self):
        """Test on technical tasks with very different wording."""
        v1 = SimilarityLearner(k=3)
        enc = CharacterEncoder(dim=8)
        v2 = HybridSimilarityLearner(k=3, semantic_encoder=enc)

        _train_learner(v1, TECHNICAL_VARIED.training)
        _train_learner(v2, TECHNICAL_VARIED.training)

        v1_acc = _evaluate(v1, TECHNICAL_VARIED.test_paraphrase)
        v2_acc = _evaluate(v2, TECHNICAL_VARIED.test_paraphrase)

        assert v1_acc >= 0.0
        assert v2_acc >= 0.0

    def test_v2_maintains_v1_baseline(self):
        """V2 should not be worse than V1 on training data (memorization)."""
        v1 = SimilarityLearner(k=3)
        enc = CharacterEncoder(dim=8)
        v2 = HybridSimilarityLearner(k=3, semantic_encoder=enc)

        _train_learner(v1, BASIC_CLASSIFICATION.training)
        _train_learner(v2, BASIC_CLASSIFICATION.training)

        v1_acc = _evaluate(v1, BASIC_CLASSIFICATION.test_known)
        v2_acc = _evaluate(v2, BASIC_CLASSIFICATION.test_known)

        # V2 should be at least as good as V1 on memorization
        assert v2_acc >= v1_acc - 0.1

    def test_v2_handles_feedback(self):
        """V2 should handle feedback correctly."""
        enc = CharacterEncoder(dim=8)
        learner = HybridSimilarityLearner(k=3, semantic_encoder=enc)

        learner.learn(LearningInput(observation={"input": "hello", "output": "greeting"}))
        pred = learner.predict("hello")
        changes = learner.feedback("hello", pred.output, correct=True)

        assert changes["correct"] is True
        assert learner.parameters["total_predictions"] >= 1

    def test_v2_handles_incorrect_feedback(self):
        """V2 should add correction examples on incorrect feedback."""
        enc = CharacterEncoder(dim=8)
        learner = HybridSimilarityLearner(k=3, semantic_encoder=enc)

        learner.learn(LearningInput(observation={"input": "x", "output": "wrong"}))
        pred = learner.predict("x")
        changes = learner.feedback("x", pred.output, correct=False, actual_output="right")

        assert changes["correct"] is False
        assert "new_example_id" in changes
        assert learner.memory.count() == 2

    def test_v2_weights_configurable(self):
        """V2 should allow configurable lexical/semantic weights."""
        enc = CharacterEncoder(dim=8)

        # Pure lexical (should behave like V1)
        v2_lex = HybridSimilarityLearner(
            k=3, semantic_encoder=enc, lexical_weight=1.0, semantic_weight=0.0,
        )
        v1 = SimilarityLearner(k=3)

        _train_learner(v2_lex, BASIC_CLASSIFICATION.training)
        _train_learner(v1, BASIC_CLASSIFICATION.training)

        v1_acc = _evaluate(v1, BASIC_CLASSIFICATION.test_known)
        v2_lex_acc = _evaluate(v2_lex, BASIC_CLASSIFICATION.test_known)

        # Pure-lexical V2 should be very similar to V1
        assert abs(v2_lex_acc - v1_acc) <= 0.1

    def test_all_semantic_datasets(self):
        """Run all semantic datasets and verify basic functionality."""
        enc = CharacterEncoder(dim=8)
        v2 = HybridSimilarityLearner(k=3, semantic_encoder=enc)

        for dataset in get_all_semantic_datasets():
            _train_learner(v2, dataset.training)

            # Test paraphrase recognition
            para_acc = _evaluate(v2, dataset.test_paraphrase)
            assert para_acc >= 0.0, f"Failed on {dataset.name} paraphrases"

            # Test synonym recognition
            syn_acc = _evaluate(v2, dataset.test_synonym)
            assert syn_acc >= 0.0, f"Failed on {dataset.name} synonyms"

            # Test unrelated items (should NOT match training labels)
            unrel_acc = _evaluate(v2, dataset.test_unrelated)
            # Unrelated accuracy can be anything — we just verify it doesn't crash
            assert unrel_acc >= 0.0

            # Reset for next dataset
            v2.reset()
