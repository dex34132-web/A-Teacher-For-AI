"""Adversarial safety tests for V2.1 retrieval scoring.

These tests verify that quality/recency bonuses cannot override relevance.
High-quality but irrelevant memories must NOT dominate retrieval results.
"""

from __future__ import annotations

from core.learner.feature_extractor import FeatureExtractor, FeatureVector
from core.learner.hybrid_memory import HybridMemory
from core.learner.retrieval_scorer import (
    ScorerConfig,
    retrieval_score,
)

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _fv(texts: list[str]) -> FeatureVector:
    """Extract features from text for test vectors."""
    ext = FeatureExtractor(use_idf=False)
    combined = " ".join(texts)
    return ext.fit(combined)


def _make_learner_with_scorer():
    """Create a HybridSimilarityLearner with V2.1 scoring enabled."""
    from core.learner.learner_v2 import HybridSimilarityLearner

    return HybridSimilarityLearner(
        k=3,
        scorer_config=ScorerConfig(
            quality_weight=0.3,
            recency_weight=0.2,
            diversity_threshold=0.9,
        ),
    )


class TestAdversarialSafety:
    """High-quality irrelevant memories must not override relevant ones."""

    def test_perfect_quality_irrelevant_not_ranked_higher(self):
        """A memory with 100% success but low similarity must rank below
        a relevant memory with average success rate."""
        scorer_cfg = ScorerConfig(quality_weight=0.3, recency_weight=0.2)

        # Relevant memory with average quality
        relevant = retrieval_score(
            relevance=0.7,
            quality=0.5,
            recency=0.5,
            quality_weight=scorer_cfg.quality_weight,
            recency_weight=scorer_cfg.recency_weight,
        )

        # Irrelevant memory with perfect quality
        irrelevant = retrieval_score(
            relevance=0.1,
            quality=1.0,
            recency=1.0,
            quality_weight=scorer_cfg.quality_weight,
            recency_weight=scorer_cfg.recency_weight,
        )

        # Relevant must score higher despite lower quality
        assert relevant > irrelevant, (
            f"Relevant ({relevant:.4f}) should beat irrelevant ({irrelevant:.4f})"
        )

    def test_high_quality_cannot_overcome_zero_similarity(self):
        """Zero relevance means zero score, regardless of quality."""
        s = retrieval_score(
            relevance=0.0,
            quality=1.0,
            recency=1.0,
            quality_weight=1.0,  # Even extreme weight
            recency_weight=1.0,
        )
        assert s == 0.0

    def test_near_irrelevant_with_perfect_quality_still_low(self):
        """A barely relevant memory (similarity 0.05) with perfect quality
        should still score very low."""
        s = retrieval_score(
            relevance=0.05,
            quality=1.0,
            recency=1.0,
            quality_weight=0.3,
            recency_weight=0.2,
        )
        # 0.05 * (1 + 0.3 + 0.2) = 0.075
        assert s < 0.1

    def test_quality_weight_bounded(self):
        """Default quality weight (0.1) limits quality impact to ~10%."""
        base = retrieval_score(
            relevance=0.5,
            quality=0.0,
            recency=0.0,
            quality_weight=0.0,
            recency_weight=0.0,
        )
        boosted = retrieval_score(
            relevance=0.5,
            quality=1.0,
            recency=0.0,
            quality_weight=0.1,
            recency_weight=0.0,
        )
        # Max boost: 0.5 * 0.1 * 1.0 = 0.05 (10% relative increase)
        assert boosted - base < 0.06

    def test_recency_weight_bounded(self):
        """Default recency weight (0.05) limits recency impact to ~5%."""
        base = retrieval_score(
            relevance=0.5,
            quality=0.0,
            recency=0.0,
            quality_weight=0.0,
            recency_weight=0.0,
        )
        boosted = retrieval_score(
            relevance=0.5,
            quality=0.0,
            recency=1.0,
            quality_weight=0.0,
            recency_weight=0.05,
        )
        assert boosted - base < 0.03

    def test_multiple_high_quality_irrelevant_dont_pollute(self):
        """Multiple irrelevant memories with perfect quality should all
        score below a relevant mediocre memory."""
        scorer_cfg = ScorerConfig(quality_weight=0.3, recency_weight=0.2)
        relevant_score = retrieval_score(
            relevance=0.6, quality=0.5, recency=0.5,
            quality_weight=scorer_cfg.quality_weight,
            recency_weight=scorer_cfg.recency_weight,
        )
        for i in range(5):
            irrelevant = retrieval_score(
                relevance=0.05 + i * 0.01,  # 0.05 to 0.09
                quality=1.0,
                recency=1.0,
                quality_weight=scorer_cfg.quality_weight,
                recency_weight=scorer_cfg.recency_weight,
            )
            assert relevant_score > irrelevant, (
                f"Irrelevant #{i} ({irrelevant:.4f}) beat relevant ({relevant_score:.4f})"
            )

    def test_extreme_quality_weight_still_respects_relevance(self):
        """Even with extreme quality_weight=0.5, relevance dominates."""
        scores = []
        for relevance in [0.1, 0.3, 0.5, 0.7, 0.9]:
            s = retrieval_score(
                relevance=relevance,
                quality=1.0,
                recency=1.0,
                quality_weight=0.5,
                recency_weight=0.2,
            )
            scores.append((relevance, s))

        # Scores must be monotonically increasing with relevance
        for i in range(1, len(scores)):
            assert scores[i][1] > scores[i - 1][1], (
                f"Score at relevance {scores[i][0]} ({scores[i][1]:.4f}) "
                f"should be > score at {scores[i-1][0]} ({scores[i-1][1]:.4f})"
            )


class TestFeedbackCannotPoison:
    """Feedback that targets wrong memories should not harm good ones."""

    def test_incorrect_feedback_weakens_target(self):
        """Feedback marking a memory as incorrect decreases its weight."""
        mem = HybridMemory()
        fv = _fv(["hello"])
        ex = mem.add(input_text="hello", output="world", vector=fv, weight=2.0)
        mem.record_feedback(ex.id, correct=False)
        stored = mem.get_hybrid(ex.id)
        assert stored.weight < 2.0

    def test_correct_feedback_strengthens_target(self):
        """Feedback marking a memory as correct increases its weight."""
        mem = HybridMemory()
        fv = _fv(["hello"])
        ex = mem.add(input_text="hello", output="world", vector=fv, weight=1.0)
        mem.record_feedback(ex.id, correct=True)
        stored = mem.get_hybrid(ex.id)
        assert stored.weight > 1.0

    def test_feedback_on_one_does_not_affect_others(self):
        """Feedback on one memory should not change other memories' weights."""
        mem = HybridMemory()
        fv1 = _fv(["hello"])
        fv2 = _fv(["goodbye"])
        ex1 = mem.add(input_text="hello", output="world", vector=fv1, weight=2.0)
        ex2 = mem.add(input_text="goodbye", output="universe", vector=fv2, weight=3.0)
        mem.record_feedback(ex1.id, correct=False)
        stored2 = mem.get_hybrid(ex2.id)
        assert stored2.weight == 3.0


class TestDiversitySafety:
    """Diversity mechanism should not remove genuinely different memories."""

    def test_different_content_not_removed(self):
        """Memories with different content but similar scores should all survive."""
        from core.learner.retrieval_scorer import diversify_top_k

        items = [
            (0, 0.9, 0.0),
            (1, 0.85, 0.3),  # Low pairwise sim
            (2, 0.80, 0.4),  # Low pairwise sim
        ]
        result = diversify_top_k(items, k=5, similarity_threshold=0.9)
        assert len(result) == 3  # All different, all kept

    def test_only_near_duplicates_removed(self):
        """Only memories with high pairwise similarity are removed."""
        from core.learner.retrieval_scorer import diversify_top_k

        items = [
            (0, 0.9, 0.0),
            (1, 0.88, 0.95),  # Near-duplicate of 0
            (2, 0.82, 0.92),  # Near-duplicate of 0
            (3, 0.78, 0.2),  # Different from 0
        ]
        result = diversify_top_k(items, k=10, similarity_threshold=0.9)
        result_ids = [r[0] for r in result]
        assert 0 in result_ids
        assert 1 not in result_ids  # Near-duplicate removed
        assert 2 not in result_ids  # Near-duplicate removed
        assert 3 in result_ids  # Different, kept

    def test_diversity_disabled_preserves_all(self):
        """When diversity_threshold=1.0, nothing is removed."""
        from core.learner.retrieval_scorer import diversify_top_k

        items = [
            (0, 0.9, 0.99),
            (1, 0.85, 0.99),
            (2, 0.80, 0.99),
        ]
        result = diversify_top_k(items, k=5, similarity_threshold=1.0)
        assert len(result) == 3
