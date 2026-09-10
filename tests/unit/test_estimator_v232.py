"""Unit tests for V2.3.2 confidence estimator."""

from __future__ import annotations

from core.learner.calibration.estimator import (
    ConfidenceEstimatorConfig,
    _bayesian_strength,
    _compute_agreement,
    _compute_conflict_penalty,
    _compute_failure_penalty,
    _compute_novelty_penalty,
    estimate_confidence_v232,
)

# ---------------------------------------------------------------------------
# Bayesian evidence strength (V2.3.2)
# ---------------------------------------------------------------------------


class TestBayesianEvidenceV232:
    def test_no_evidence_returns_prior(self):
        result = _bayesian_strength(0.5, 0, 0, prior_strength=2.0)
        assert result == 0.5

    def test_all_success_converges_to_one(self):
        result = _bayesian_strength(0.5, 100, 0, prior_strength=2.0)
        assert result > 0.95

    def test_all_failure_converges_to_zero(self):
        result = _bayesian_strength(0.5, 0, 100, prior_strength=2.0)
        assert result < 0.05

    def test_mixed_evidence_blends(self):
        result = _bayesian_strength(0.5, 5, 5, prior_strength=2.0)
        assert 0.4 < result < 0.6

    def test_lower_prior_strength_converges_faster(self):
        fast = _bayesian_strength(0.5, 10, 0, prior_strength=1.0)
        slow = _bayesian_strength(0.5, 10, 0, prior_strength=4.0)
        assert fast > slow

    def test_result_bounded(self):
        for s in range(0, 21):
            for f in range(0, 21):
                result = _bayesian_strength(0.5, s, f, prior_strength=2.0)
                assert 0.0 <= result <= 1.0


# ---------------------------------------------------------------------------
# Agreement (V2.3.2)
# ---------------------------------------------------------------------------


class TestAgreementV232:
    def test_zero_weight_returns_zero(self):
        assert _compute_agreement(0.0, 1.0, 3, 5) == 0.0

    def test_zero_count_returns_zero(self):
        assert _compute_agreement(1.0, 1.0, 0, 0) == 0.0

    def test_full_agreement(self):
        result = _compute_agreement(1.0, 1.0, 5, 5)
        assert result == 1.0

    def test_no_agreement(self):
        result = _compute_agreement(0.5, 1.0, 1, 2)
        assert result == 0.0

    def test_majority_agreement(self):
        result = _compute_agreement(0.7, 1.0, 3, 5)
        assert result > 0.5

    def test_below_threshold_returns_zero(self):
        result = _compute_agreement(0.5, 1.0, 1, 2)
        assert result == 0.0


# ---------------------------------------------------------------------------
# Conflict penalty (V2.3.2)
# ---------------------------------------------------------------------------


class TestConflictPenaltyV232:
    def test_no_runner_up(self):
        result = _compute_conflict_penalty(1.0, 0.0, 0.50)
        assert result == 0.0

    def test_equal_split(self):
        result = _compute_conflict_penalty(1.0, 1.0, 0.50)
        assert result > 0.3

    def test_dominant_winner(self):
        result = _compute_conflict_penalty(1.0, 0.1, 0.50)
        assert result < 0.1

    def test_bounded_by_max(self):
        result = _compute_conflict_penalty(1.0, 1.0, 0.50)
        assert result <= 0.50


# ---------------------------------------------------------------------------
# Failure penalty (V2.3.2)
# ---------------------------------------------------------------------------


class TestFailurePenaltyV232:
    def test_no_failures(self):
        result = _compute_failure_penalty(10, 0, 0.30)
        assert result == 0.0

    def test_dominant_failures(self):
        result = _compute_failure_penalty(0, 10, 0.30)
        assert result > 0.2

    def test_majority_successes(self):
        result = _compute_failure_penalty(8, 2, 0.30)
        assert result < 0.1

    def test_bounded(self):
        result = _compute_failure_penalty(100, 100, 0.30)
        assert result <= 0.30


# ---------------------------------------------------------------------------
# Novelty penalty (V2.3.2)
# ---------------------------------------------------------------------------


class TestNoveltyPenaltyV232:
    def test_high_similarity_no_penalty(self):
        result = _compute_novelty_penalty(0.8, 0.3, 0.15)
        assert result == 0.0

    def test_low_similarity_gets_penalty(self):
        result = _compute_novelty_penalty(0.1, 0.3, 0.15)
        assert result > 0.0

    def test_zero_similarity_max_penalty(self):
        result = _compute_novelty_penalty(0.0, 0.3, 0.15)
        assert result == 0.15

    def test_bounded(self):
        result = _compute_novelty_penalty(0.0, 0.3, 0.15)
        assert result <= 0.15


# ---------------------------------------------------------------------------
# Full estimator (V2.3.2)
# ---------------------------------------------------------------------------


class TestEstimateConfidenceV232:
    def test_zero_evidence(self):
        result = estimate_confidence_v232(
            similarity=0.5, success_count=0, failure_count=0,
            supporting_weight=0.5, total_weight=0.5,
            supporting_count=1, total_count=1,
            outputs=["a"], output_similarities=[0.5],
        )
        assert 0.0 <= result.confidence <= 1.0
        assert result.components["evidence_strength"] == 0.5

    def test_strong_evidence_high_confidence(self):
        result = estimate_confidence_v232(
            similarity=0.9, success_count=20, failure_count=0,
            supporting_weight=1.8, total_weight=2.0,
            supporting_count=5, total_count=5,
            outputs=["a"] * 5, output_similarities=[0.9] * 5,
        )
        assert result.confidence > 0.8

    def test_conflict_reduces_confidence(self):
        no_conflict = estimate_confidence_v232(
            similarity=0.8, success_count=10, failure_count=0,
            supporting_weight=1.6, total_weight=1.6,
            supporting_count=4, total_count=4,
            outputs=["a"] * 4, output_similarities=[0.8] * 4,
        )
        with_conflict = estimate_confidence_v232(
            similarity=0.8, success_count=10, failure_count=0,
            supporting_weight=0.8, total_weight=1.6,
            supporting_count=2, total_count=4,
            outputs=["a", "a", "b", "b"], output_similarities=[0.8] * 4,
        )
        assert with_conflict.confidence < no_conflict.confidence

    def test_failures_reduce_confidence(self):
        no_fail = estimate_confidence_v232(
            similarity=0.8, success_count=10, failure_count=0,
            supporting_weight=1.6, total_weight=1.6,
            supporting_count=4, total_count=4,
            outputs=["a"] * 4, output_similarities=[0.8] * 4,
        )
        with_fail = estimate_confidence_v232(
            similarity=0.8, success_count=2, failure_count=8,
            supporting_weight=1.6, total_weight=1.6,
            supporting_count=4, total_count=4,
            outputs=["a"] * 4, output_similarities=[0.8] * 4,
        )
        assert with_fail.confidence < no_fail.confidence

    def test_low_similarity_reduces_confidence(self):
        high = estimate_confidence_v232(
            similarity=0.9, success_count=10, failure_count=0,
            supporting_weight=1.8, total_weight=2.0,
            supporting_count=5, total_count=5,
            outputs=["a"] * 5, output_similarities=[0.9] * 5,
        )
        low = estimate_confidence_v232(
            similarity=0.3, success_count=10, failure_count=0,
            supporting_weight=0.6, total_weight=0.8,
            supporting_count=5, total_count=5,
            outputs=["a"] * 5, output_similarities=[0.3] * 5,
        )
        assert low.confidence < high.confidence

    def test_monotonicity_with_success(self):
        prev = 0.0
        for s in [0, 5, 10, 20, 50]:
            result = estimate_confidence_v232(
                similarity=0.7, success_count=s, failure_count=0,
                supporting_weight=1.4, total_weight=1.4,
                supporting_count=2, total_count=2,
                outputs=["a"] * 2, output_similarities=[0.7] * 2,
            )
            assert result.confidence >= prev
            prev = result.confidence

    def test_confidence_bounded(self):
        for sim in [0.0, 0.3, 0.5, 0.7, 0.9, 1.0]:
            result = estimate_confidence_v232(
                similarity=sim, success_count=50, failure_count=0,
                supporting_weight=2.0, total_weight=2.0,
                supporting_count=5, total_count=5,
                outputs=["a"] * 5, output_similarities=[sim] * 5,
            )
            assert 0.0 <= result.confidence <= 1.0

    def test_custom_config(self):
        config = ConfidenceEstimatorConfig(
            prior_strength=1.0,
            agreement_weight=0.30,
            max_conflict_penalty=0.60,
            failure_dominance_penalty=0.40,
        )
        result = estimate_confidence_v232(
            similarity=0.8, success_count=10, failure_count=0,
            supporting_weight=1.6, total_weight=1.6,
            supporting_count=4, total_count=4,
            outputs=["a"] * 4, output_similarities=[0.8] * 4,
            config=config,
        )
        assert 0.0 <= result.confidence <= 1.0
        assert result.components["agreement_bonus"] > 0

    def test_has_all_components(self):
        result = estimate_confidence_v232(
            similarity=0.8, success_count=10, failure_count=2,
            supporting_weight=1.6, total_weight=2.0,
            supporting_count=4, total_count=5,
            outputs=["a", "a", "a", "a", "b"], output_similarities=[0.8] * 5,
        )
        expected_keys = {
            "similarity", "evidence_strength", "evidence_quality",
            "base_confidence", "agreement", "agreement_bonus",
            "conflict_penalty", "novelty_penalty", "failure_penalty",
            "success_count", "failure_count", "total_uses",
            "supporting_count", "total_count", "conflict_count",
        }
        assert expected_keys <= set(result.components.keys())

    def test_zero_total_weight(self):
        result = estimate_confidence_v232(
            similarity=0.5, success_count=0, failure_count=0,
            supporting_weight=0.0, total_weight=0.0,
            supporting_count=0, total_count=0,
            outputs=[], output_similarities=[],
        )
        assert result.confidence <= 0.5
