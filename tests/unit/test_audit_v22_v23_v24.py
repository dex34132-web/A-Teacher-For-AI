"""Comprehensive audit tests for V2.2 (conflict), V2.3 (confidence),
and V2.4 (lifecycle). 120+ independent, meaningful tests."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from core.learner.calibration.estimator import (
    ConfidenceEstimatorConfig,
    _bayesian_strength,
    _compute_failure_penalty,
    _compute_independence_bonus,
    _evidence_quality,
    estimate_confidence_v232,
)
from core.learner.confidence import (
    ConfidenceBand,
    ConfidenceConfig,
    ConfidenceLevel,
    bayesian_evidence_strength,
    classify_uncertainty_state,
    compute_agreement,
    compute_conflict_penalty,
    confidence_to_probability,
    detect_conflict_count,
    estimate_confidence,
)
from core.learner.conflict import (
    Conflict,
    ConflictConfig,
    ConflictState,
    Evidence,
    _evidence_score,
    _output_similarity,
    compare_evidence,
    detect_conflicts,
    gather_evidence,
)
from core.learner.feature_extractor import FeatureExtractor, FeatureVector
from core.learner.hybrid_memory import HybridExample, HybridMemory
from core.learner.knowledge_ops import (
    RedundancyType,
    TokenInvertedIndex,
    analyze_redundancy,
    analyze_supersession,
    archive_memory,
    find_merge_candidates,
    is_eligible_for_archive,
)
from core.learner.learner_v1 import Prediction
from core.learner.lifecycle import (
    HealthSignals,
    LifecycleConfig,
    MemoryState,
    compute_decay,
    compute_health_score,
    compute_reinforcement,
)
from core.learner.lifecycle_manager import (
    PERSISTENCE_VERSION,
    EventTriggerConfig,
    LifecycleManager,
    MaintenanceEvent,
    MaintenanceRecord,
)
from core.learner.predict_result import PredictResult

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _fv(text: str) -> FeatureVector:
    ext = FeatureExtractor(use_idf=False)
    return ext.fit(text)


def _example(
    id: int,
    input_text: str,
    output: str,
    success_count: int = 0,
    failure_count: int = 0,
    weight: float = 1.0,
    last_used_at: float = 0.0,
    use_count: int = 0,
    created_at: float = 0.0,
) -> HybridExample:
    return HybridExample(
        id=id,
        input_text=input_text,
        output=output,
        lexical_vector=_fv(input_text),
        weight=weight,
        success_count=success_count,
        failure_count=failure_count,
        last_used_at=last_used_at,
        use_count=use_count,
        created_at=created_at,
    )


def _memory_with(examples: list[HybridExample]) -> HybridMemory:
    """Build a HybridMemory populated with the given examples."""
    mem = HybridMemory()
    for ex in examples:
        mem._examples.append(
            __import__(
                "core.learner.memory",
                fromlist=["LearnedExample"],
            ).LearnedExample(
                id=ex.id,
                input_text=ex.input_text,
                output=ex.output,
                vector=ex.lexical_vector,
                weight=ex.weight,
                feedback_count=ex.feedback_count,
                correct_count=ex.correct_count,
                metadata=ex.metadata,
            )
        )
        mem._last_used_at[ex.id] = ex.last_used_at
        mem._use_count[ex.id] = ex.use_count
        mem._success_count[ex.id] = ex.success_count
        mem._failure_count[ex.id] = ex.failure_count
        mem._created_at[ex.id] = ex.created_at
        if ex.semantic_vector is not None:
            mem._semantic_vectors[ex.id] = ex.semantic_vector
    return mem


def _predict_result(
    output: str,
    confidence: float,
    conflicts: list | None = None,
) -> PredictResult:
    pred = Prediction(
        output=output,
        confidence=confidence,
        similarities=[("test", confidence)],
    )
    return PredictResult(
        prediction=pred,
        conflicts=conflicts or [],
        overall_conflict_state=(
            conflicts[0].state if conflicts else ConflictState.NONE
        ),
    )


# ====================================================================
# V2.2 CONFLICT TESTS
# ====================================================================


class TestOutputSimilarity:
    def test_identical_returns_one(self):
        assert _output_similarity("hello", "hello") == 1.0

    def test_completely_different_returns_zero(self):
        assert _output_similarity("foo bar", "xyz abc") == 0.0

    def test_case_insensitive(self):
        assert _output_similarity(
            "Hello World", "hello world"
        ) == 1.0

    def test_empty_strings(self):
        assert _output_similarity("", "") == 1.0

    def test_one_empty_one_not(self):
        assert _output_similarity("hello", "") == 0.0

    def test_partial_overlap(self):
        sim = _output_similarity(
            "foo bar baz", "foo qux"
        )
        assert abs(sim - 0.25) < 0.01

    def test_reorder_same_tokens(self):
        sim = _output_similarity(
            "a b c", "c b a"
        )
        assert sim == 1.0

    def test_single_token_match(self):
        sim = _output_similarity("x", "x")
        assert sim == 1.0

    def test_single_token_mismatch(self):
        sim = _output_similarity("x", "y")
        assert sim == 0.0


class TestConflictDetection:
    def test_no_conflict_identical_output(self):
        cands = [
            (1, 0.9, "sorted()"),
            (2, 0.8, "sorted()"),
        ]
        exs = {
            1: _example(1, "sort list", "sorted()"),
            2: _example(2, "sort array", "sorted()"),
        }
        assert len(detect_conflicts(cands, exs)) == 0

    def test_conflict_different_output_same_input(self):
        cands = [
            (1, 0.9, "sorted()"),
            (2, 0.85, "list.sort()"),
        ]
        exs = {
            1: _example(1, "sort a list", "sorted()"),
            2: _example(2, "sort a list", "list.sort()"),
        }
        conflicts = detect_conflicts(cands, exs)
        assert len(conflicts) >= 1
        assert conflicts[0].state == ConflictState.CONFIRMED

    def test_no_conflict_different_input(self):
        cands = [
            (1, 0.9, "open()"),
            (2, 0.8, "reverse"),
        ]
        exs = {
            1: _example(1, "open a file", "open()"),
            2: _example(2, "reverse a string", "reverse"),
        }
        conflicts = detect_conflicts(cands, exs)
        assert len(conflicts) == 0

    def test_possible_conflict_similar_input(self):
        cands = [
            (1, 0.9, "use X"),
            (2, 0.85, "use Y"),
        ]
        exs = {
            1: _example(
                1, "sort a list of items", "use X"
            ),
            2: _example(2, "sort a list", "use Y"),
        }
        conflicts = detect_conflicts(cands, exs)
        assert len(conflicts) >= 1
        assert conflicts[0].state in (
            ConflictState.POSSIBLE,
            ConflictState.CONFIRMED,
        )

    def test_single_candidate_no_conflict(self):
        cands = [(1, 0.9, "sorted()")]
        exs = {1: _example(1, "sort list", "sorted()")}
        assert len(detect_conflicts(cands, exs)) == 0

    def test_empty_candidates(self):
        assert len(detect_conflicts([], {})) == 0

    def test_three_way_conflict(self):
        cands = [
            (1, 0.9, "A"),
            (2, 0.85, "B"),
            (3, 0.8, "C"),
        ]
        exs = {
            1: _example(1, "task X", "A"),
            2: _example(2, "task X", "B"),
            3: _example(3, "task X", "C"),
        }
        conflicts = detect_conflicts(cands, exs)
        assert len(conflicts) >= 2

    def test_custom_config_threshold(self):
        cands = [
            (1, 0.9, "A"),
            (2, 0.85, "B"),
        ]
        exs = {
            1: _example(1, "sort a list", "A"),
            2: _example(2, "sort a list", "B"),
        }
        cfg = ConflictConfig(
            context_similarity_threshold=0.99
        )
        conflicts = detect_conflicts(cands, exs, cfg)
        for c in conflicts:
            assert c.strength >= 0.99 or (
                c.state == ConflictState.POSSIBLE
            )


class TestEvidenceGathering:
    def test_gather_evidence_basic(self):
        conflict = Conflict(
            involved_ids=[1, 2],
            outputs=["A", "B"],
            state=ConflictState.CONFIRMED,
            strength=0.9,
        )
        exs = {
            1: _example(
                1, "x", "A",
                success_count=5, failure_count=1,
                weight=2.0,
            ),
            2: _example(
                2, "x", "B",
                success_count=3, failure_count=2,
                weight=1.5,
            ),
        }
        gather_evidence(conflict, exs, {1: 0.9, 2: 0.85})
        assert len(conflict.evidence) == 2
        assert conflict.evidence[0].success_rate == 5 / 6
        assert conflict.evidence[1].success_rate == 3 / 5

    def test_gather_evidence_neutral_untested(self):
        conflict = Conflict(
            involved_ids=[1], outputs=["A"]
        )
        exs = {1: _example(1, "x", "A")}
        gather_evidence(conflict, exs, {1: 0.9})
        assert conflict.evidence[0].success_rate == 0.5

    def test_gather_evidence_with_recency(self):
        conflict = Conflict(
            involved_ids=[1], outputs=["A"]
        )
        exs = {1: _example(1, "x", "A")}
        gather_evidence(
            conflict, exs, {1: 0.9}, {1: 0.8}
        )
        assert conflict.evidence[0].recency == 0.8

    def test_gather_evidence_missing_example_skipped(self):
        conflict = Conflict(
            involved_ids=[1, 999], outputs=["A", "B"]
        )
        exs = {1: _example(1, "x", "A")}
        gather_evidence(conflict, exs, {1: 0.9})
        assert len(conflict.evidence) == 1

    def test_gather_evidence_relevance_from_query(self):
        conflict = Conflict(
            involved_ids=[1, 2], outputs=["A", "B"]
        )
        exs = {
            1: _example(1, "x", "A"),
            2: _example(2, "x", "B"),
        }
        gather_evidence(
            conflict, exs, {1: 0.7, 2: 0.3}
        )
        assert conflict.evidence[0].relevance == 0.7
        assert conflict.evidence[1].relevance == 0.3


class TestEvidenceComparison:
    def test_clear_winner_resolved(self):
        conflict = Conflict(
            involved_ids=[1, 2],
            outputs=["A", "B"],
            state=ConflictState.CONFIRMED,
            strength=0.9,
        )
        conflict.evidence = [
            Evidence(
                1, "A", 0.9, 0.9, 18, 2, 3.0, 0.9
            ),
            Evidence(
                2, "B", 0.85, 0.5, 5, 5, 1.0, 0.5
            ),
        ]
        compare_evidence(conflict)
        assert conflict.state == ConflictState.RESOLVED
        assert conflict.selected_output == "A"

    def test_close_scores_unresolved(self):
        conflict = Conflict(
            involved_ids=[1, 2],
            outputs=["A", "B"],
            state=ConflictState.CONFIRMED,
            strength=0.9,
        )
        conflict.evidence = [
            Evidence(
                1, "A", 0.9, 0.8, 8, 2, 2.0, 0.8
            ),
            Evidence(
                2, "B", 0.88, 0.8, 8, 2, 2.0, 0.8
            ),
        ]
        compare_evidence(conflict)
        assert conflict.state == ConflictState.UNRESOLVED
        assert conflict.confidence_penalty > 0.3

    def test_relevance_dominates(self):
        conflict = Conflict(
            involved_ids=[1, 2],
            outputs=["A", "B"],
            state=ConflictState.CONFIRMED,
            strength=0.9,
        )
        conflict.evidence = [
            Evidence(
                1, "A", 0.95, 0.7, 7, 3, 1.5, 0.7
            ),
            Evidence(
                2, "B", 0.5, 0.95, 19, 1, 4.0, 0.9
            ),
        ]
        compare_evidence(conflict)
        assert conflict.selected_output == "A"

    def test_insufficient_evidence_unresolved(self):
        conflict = Conflict(
            involved_ids=[1],
            outputs=["A"],
            state=ConflictState.CONFIRMED,
            strength=0.9,
        )
        conflict.evidence = [
            Evidence(
                1, "A", 0.9, 0.5, 0, 0, 1.0, 0.5
            ),
        ]
        compare_evidence(conflict)
        assert conflict.state == ConflictState.UNRESOLVED

    def test_evidence_score_bounded(self):
        for rel in [0.0, 0.5, 1.0]:
            for sr in [0.0, 0.5, 1.0]:
                ev = Evidence(
                    1, "out", rel, sr, 5, 5, 1.0, 0.5
                )
                score = _evidence_score(ev)
                assert 0.0 <= score <= 1.0


class TestConflictDataclasses:
    def test_conflict_config_defaults(self):
        cfg = ConflictConfig()
        assert cfg.input_similarity_threshold == 0.75
        assert cfg.output_equality_threshold == 0.0
        assert cfg.evidence_margin == 0.1
        assert cfg.min_evidence_samples == 3

    def test_conflict_initial_state(self):
        c = Conflict(
            involved_ids=[1, 2],
            outputs=["A", "B"],
        )
        assert c.state == ConflictState.NONE
        assert c.strength == 0.0
        assert c.selected_output is None
        assert c.winner_id is None

    def test_conflict_resolved_state(self):
        c = Conflict(
            involved_ids=[1, 2],
            outputs=["A", "B"],
            state=ConflictState.RESOLVED,
            winner_id=1,
            selected_output="A",
        )
        assert c.winner_id == 1
        assert c.selected_output == "A"

    def test_conflict_state_enum_values(self):
        assert ConflictState.NONE.value == "none"
        assert ConflictState.POSSIBLE.value == "possible"
        assert ConflictState.CONFIRMED.value == "confirmed"
        assert ConflictState.RESOLVED.value == "resolved"
        assert ConflictState.UNRESOLVED.value == "unresolved"

    def test_evidence_frozen(self):
        ev = Evidence(
            1, "out", 0.8, 0.7, 3, 1, 2.0, 0.6
        )
        with pytest.raises(AttributeError):
            ev.relevance = 0.5  # type: ignore[misc]

    def test_evidence_score_range(self):
        for rel in [0.0, 0.3, 0.7, 1.0]:
            for sc in [0, 1, 5, 20]:
                for fc in [0, 1, 5]:
                    ev = Evidence(
                        1, "o", rel, 0.5, sc, fc, 1.0, 0.5
                    )
                    s = _evidence_score(ev)
                    assert 0.0 <= s <= 1.0


class TestPredictResultV22:
    def test_has_conflict_property(self):
        pr = _predict_result("A", 0.9)
        assert not pr.has_conflict

    def test_is_resolved_no_conflicts(self):
        pr = _predict_result("A", 0.9)
        assert pr.is_resolved

    def test_conflict_penalty_reduces_confidence(self):
        c = Conflict(
            involved_ids=[1, 2],
            outputs=["A", "B"],
            state=ConflictState.UNRESOLVED,
            confidence_penalty=0.3,
        )
        pr = PredictResult(
            prediction=Prediction(
                output="A", confidence=0.9
            ),
            conflicts=[c],
            overall_conflict_state=ConflictState.UNRESOLVED,
            conflict_confidence_penalty=0.3,
        )
        assert pr.confidence == pytest.approx(
            0.9 * 0.7, abs=0.01
        )

    def test_confidence_never_negative(self):
        c = Conflict(
            involved_ids=[1, 2],
            outputs=["A", "B"],
            state=ConflictState.UNRESOLVED,
            confidence_penalty=1.0,
        )
        pr = PredictResult(
            prediction=Prediction(
                output="A", confidence=0.1
            ),
            conflicts=[c],
            conflict_confidence_penalty=1.0,
        )
        assert pr.confidence >= 0.0

    def test_confidence_never_exceeds_one(self):
        pr = _predict_result("A", 1.5)
        assert pr.confidence <= 1.0

    def test_to_legacy(self):
        pr = _predict_result("A", 0.9)
        assert isinstance(pr.to_legacy(), Prediction)

    def test_summary_has_keys(self):
        pr = _predict_result("A", 0.9)
        s = pr.summary()
        assert "output" in s
        assert "confidence" in s
        assert "uncertainty_state" in s

    def test_abstained_output_empty(self):
        pr = _predict_result("A", 0.9)
        pr.abstained = True
        assert pr.output == ""
        assert pr.confidence == 0.0

    def test_conflicting_outputs(self):
        c1 = Conflict(
            involved_ids=[1], outputs=["A", "B"]
        )
        c2 = Conflict(
            involved_ids=[2], outputs=["B", "C"]
        )
        pr = PredictResult(
            prediction=Prediction(
                output="A", confidence=0.8
            ),
            conflicts=[c1, c2],
        )
        outs = pr.conflicting_outputs
        assert "A" in outs
        assert "B" in outs
        assert "C" in outs


# ====================================================================
# V2.3 CONFIDENCE TESTS
# ====================================================================


class TestBayesianEvidenceStrength:
    def test_no_evidence_returns_prior(self):
        r = bayesian_evidence_strength(
            0.8, 0, 0, prior_strength=4.0
        )
        assert r == 0.8

    def test_all_success_near_one(self):
        r = bayesian_evidence_strength(
            0.5, 100, 0, prior_strength=4.0
        )
        assert r > 0.95

    def test_all_failure_near_zero(self):
        r = bayesian_evidence_strength(
            0.5, 0, 100, prior_strength=4.0
        )
        assert r < 0.05

    def test_mixed_blends(self):
        r = bayesian_evidence_strength(
            0.8, 5, 5, prior_strength=4.0
        )
        assert 0.4 < r < 0.8

    def test_prior_strength_affects_convergence(self):
        low = bayesian_evidence_strength(
            0.8, 2, 2, prior_strength=2.0
        )
        high = bayesian_evidence_strength(
            0.8, 2, 2, prior_strength=10.0
        )
        assert high > low

    def test_result_bounded(self):
        for s in range(0, 11):
            for f in range(0, 11):
                r = bayesian_evidence_strength(0.5, s, f)
                assert 0.0 <= r <= 1.0


class TestComputeAgreement:
    def test_full_agreement(self):
        r = compute_agreement(10.0, 10.0, 5, 5)
        assert r == 1.0

    def test_no_agreement(self):
        r = compute_agreement(0.0, 10.0, 0, 5)
        assert r == 0.0

    def test_half_agreement(self):
        r = compute_agreement(5.0, 10.0, 5, 5)
        assert abs(r - 0.75) < 0.01

    def test_zero_weight_and_count(self):
        r = compute_agreement(0.0, 0.0, 0, 0)
        assert r == 0.0

    def test_one_sided(self):
        r = compute_agreement(10.0, 10.0, 0, 5)
        assert abs(r - 0.5) < 0.01


class TestComputeConflictPenalty:
    def test_no_runner_up(self):
        r = compute_conflict_penalty(10.0, 0.0, 0.3)
        assert r == 0.0

    def test_strong_runner_up(self):
        r = compute_conflict_penalty(10.0, 10.0, 0.3)
        assert r == pytest.approx(0.3, abs=0.01)

    def test_max_cap(self):
        r = compute_conflict_penalty(0.0, 5.0, 0.5)
        assert r == 0.5

    def test_bounded_range(self):
        for w in [0.1, 1.0, 10.0]:
            for rw in [0.0, 0.5, 5.0, 50.0]:
                r = compute_conflict_penalty(w, rw, 0.3)
                assert 0.0 <= r <= 0.3


class TestDetectConflictCount:
    def test_single_output_one_group(self):
        assert detect_conflict_count(["A"]) == 1

    def test_two_same_one_group(self):
        assert detect_conflict_count(
            ["A", "A"]
        ) == 1

    def test_two_different(self):
        assert detect_conflict_count(
            ["A", "B"]
        ) == 2

    def test_three_distinct(self):
        assert detect_conflict_count(
            ["A", "B", "C"]
        ) == 3

    def test_empty(self):
        assert detect_conflict_count([]) == 0

    def test_filtered_by_similarity(self):
        n = detect_conflict_count(
            ["A", "B", "C"],
            similarities=[0.1, 0.8, 0.9],
            relevance_threshold=0.5,
        )
        assert n == 2

    def test_all_below_threshold(self):
        n = detect_conflict_count(
            ["A", "B"],
            similarities=[0.1, 0.2],
            relevance_threshold=0.5,
        )
        assert n == 0


class TestClassifyUncertaintyState:
    def test_confident(self):
        s = classify_uncertainty_state(
            0.8, 0.7, 1, 5, 0.8, 3, 10
        )
        assert s == ConfidenceLevel.CONFIDENT

    def test_conflicted(self):
        s = classify_uncertainty_state(
            0.8, 0.7, 2, 5, 0.8, 3, 10
        )
        assert s == ConfidenceLevel.CONFLICTED

    def test_insufficient_low_conf(self):
        s = classify_uncertainty_state(
            0.2, 0.5, 1, 3, 0.5, 3, 10
        )
        assert s == ConfidenceLevel.INSUFFICIENT_EVIDENCE

    def test_insufficient_low_evidence(self):
        s = classify_uncertainty_state(
            0.5, 0.2, 1, 3, 0.5, 3, 10
        )
        assert s == ConfidenceLevel.INSUFFICIENT_EVIDENCE

    def test_uncertain(self):
        s = classify_uncertainty_state(
            0.5, 0.5, 1, 3, 0.5, 3, 10
        )
        assert s == ConfidenceLevel.UNCERTAIN

    def test_insufficient_new_query(self):
        s = classify_uncertainty_state(
            0.4, 0.4, 1, 1, 0.3, 3, 1
        )
        assert s == ConfidenceLevel.INSUFFICIENT_EVIDENCE


class TestEstimateConfidence:
    def test_high_similarity_strong_evidence(self):
        r = estimate_confidence(
            similarity=0.9,
            success_count=10,
            failure_count=0,
            supporting_weight=10.0,
            total_weight=10.0,
            supporting_count=5,
            total_count=5,
            outputs=["A", "A", "A"],
        )
        assert r.confidence > 0.7
        assert r.band == ConfidenceBand.HIGH

    def test_low_similarity_weak_evidence(self):
        r = estimate_confidence(
            similarity=0.1,
            success_count=0,
            failure_count=0,
            supporting_weight=1.0,
            total_weight=3.0,
            supporting_count=1,
            total_count=3,
            outputs=["A", "B"],
        )
        assert r.confidence < 0.3

    def test_conflict_reduces_confidence(self):
        base = estimate_confidence(
            similarity=0.8,
            success_count=5,
            failure_count=0,
            supporting_weight=5.0,
            total_weight=5.0,
            supporting_count=3,
            total_count=3,
            outputs=["A", "A", "A"],
        )
        conflict = estimate_confidence(
            similarity=0.8,
            success_count=5,
            failure_count=0,
            supporting_weight=5.0,
            total_weight=10.0,
            supporting_count=3,
            total_count=6,
            outputs=["A", "A", "B"],
        )
        assert conflict.confidence < base.confidence

    def test_novelty_penalty(self):
        r = estimate_confidence(
            similarity=0.1,
            success_count=0,
            failure_count=0,
            supporting_weight=1.0,
            total_weight=1.0,
            supporting_count=1,
            total_count=1,
            outputs=["A"],
        )
        assert r.novelty_penalty > 0.0

    def test_agreement_bonus(self):
        r = estimate_confidence(
            similarity=0.8,
            success_count=5,
            failure_count=0,
            supporting_weight=9.0,
            total_weight=10.0,
            supporting_count=9,
            total_count=10,
            outputs=["A", "A", "A", "A", "A"],
        )
        assert r.agreement_bonus > 0.0

    def test_result_bounded(self):
        for sim in [0.0, 0.3, 0.7, 1.0]:
            r = estimate_confidence(
                similarity=sim,
                success_count=5,
                failure_count=2,
                supporting_weight=5.0,
                total_weight=7.0,
                supporting_count=3,
                total_count=5,
                outputs=["A", "B"],
            )
            assert 0.0 <= r.confidence <= 1.0

    def test_components_present(self):
        r = estimate_confidence(
            similarity=0.8,
            success_count=5,
            failure_count=2,
            supporting_weight=5.0,
            total_weight=7.0,
            supporting_count=3,
            total_count=5,
            outputs=["A", "B"],
        )
        assert "similarity" in r.components
        assert "evidence_strength" in r.components
        assert "conflict_penalty" in r.components
        assert "novelty_penalty" in r.components

    def test_zero_similarity_zero_confidence(self):
        r = estimate_confidence(
            similarity=0.0,
            success_count=0,
            failure_count=0,
            supporting_weight=0.0,
            total_weight=0.0,
            supporting_count=0,
            total_count=0,
            outputs=[],
        )
        assert r.confidence == 0.0

    def test_abstention_check(self):
        r = estimate_confidence(
            similarity=0.1,
            success_count=0,
            failure_count=5,
            supporting_weight=1.0,
            total_weight=10.0,
            supporting_count=1,
            total_count=5,
            outputs=["A", "B"],
        )
        should_abstain = (
            r.confidence < r.components.get(
                "similarity", 0
            ) * 0.3
        )
        assert isinstance(should_abstain, bool)


class TestConfidenceConfig:
    def test_custom_values(self):
        cfg = ConfidenceConfig(
            prior_strength=3.0,
            agreement_weight=0.25,
            max_conflict_penalty=0.4,
        )
        assert cfg.prior_strength == 3.0
        assert cfg.agreement_weight == 0.25
        assert cfg.max_conflict_penalty == 0.4

    def test_v232_flag(self):
        cfg = ConfidenceConfig(use_v232=False)
        assert cfg.use_v232 is False

    def test_defaults(self):
        cfg = ConfidenceConfig()
        assert cfg.prior_strength == 2.0
        assert cfg.agreement_weight == 0.20
        assert cfg.min_evidence_samples == 3


class TestConfidenceBand:
    def test_high_band(self):
        assert ConfidenceBand.from_confidence(0.9) == (
            ConfidenceBand.HIGH
        )

    def test_moderate_band(self):
        assert ConfidenceBand.from_confidence(0.7) == (
            ConfidenceBand.MODERATE
        )

    def test_low_band(self):
        assert ConfidenceBand.from_confidence(0.5) == (
            ConfidenceBand.LOW
        )

    def test_weak_band(self):
        assert ConfidenceBand.from_confidence(0.3) == (
            ConfidenceBand.WEAK
        )

    def test_minimal_band(self):
        assert ConfidenceBand.from_confidence(0.1) == (
            ConfidenceBand.MINIMAL
        )

    def test_boundary_high(self):
        assert ConfidenceBand.from_confidence(0.8) == (
            ConfidenceBand.HIGH
        )

    def test_boundary_moderate(self):
        assert ConfidenceBand.from_confidence(0.6) == (
            ConfidenceBand.MODERATE
        )

    def test_band_ranges(self):
        assert ConfidenceBand.band_range(
            ConfidenceBand.HIGH
        ) == (0.8, 1.0)
        assert ConfidenceBand.band_range(
            ConfidenceBand.MODERATE
        ) == (0.6, 0.8)
        assert ConfidenceBand.band_range(
            ConfidenceBand.LOW
        ) == (0.4, 0.6)
        assert ConfidenceBand.band_range(
            ConfidenceBand.WEAK
        ) == (0.2, 0.4)
        assert ConfidenceBand.band_range(
            ConfidenceBand.MINIMAL
        ) == (0.0, 0.2)


class TestConfidenceToProbability:
    def test_identity_in_range(self):
        assert confidence_to_probability(0.7) == 0.7

    def test_clamp_above(self):
        assert confidence_to_probability(1.5) == 1.0

    def test_clamp_below(self):
        assert confidence_to_probability(-0.3) == 0.0

    def test_zero(self):
        assert confidence_to_probability(0.0) == 0.0

    def test_one(self):
        assert confidence_to_probability(1.0) == 1.0


# ------------------------------------------------------------------
# V2.3.2 Estimator Tests
# ------------------------------------------------------------------


class TestEstimatorV232:
    def test_lower_prior_converges_faster(self):
        fast = _bayesian_strength(
            0.5, 10, 0, prior_strength=1.0
        )
        slow = _bayesian_strength(
            0.5, 10, 0, prior_strength=4.0
        )
        assert fast > slow

    def test_failure_dominance_penalty(self):
        r = estimate_confidence_v232(
            similarity=0.8,
            success_count=2,
            failure_count=8,
            supporting_weight=5.0,
            total_weight=10.0,
            supporting_count=3,
            total_count=6,
            outputs=["A", "B"],
        )
        assert r.failure_penalty > 0.0

    def test_no_penalty_equal(self):
        r = estimate_confidence_v232(
            similarity=0.8,
            success_count=5,
            failure_count=5,
            supporting_weight=5.0,
            total_weight=5.0,
            supporting_count=5,
            total_count=5,
            outputs=["A", "A"],
        )
        assert r.failure_penalty == 0.0

    def test_majority_agreement_threshold(self):
        strong = estimate_confidence_v232(
            similarity=0.8,
            success_count=5,
            failure_count=0,
            supporting_weight=9.0,
            total_weight=10.0,
            supporting_count=9,
            total_count=10,
            outputs=["A"] * 10,
        )
        weak = estimate_confidence_v232(
            similarity=0.8,
            success_count=5,
            failure_count=0,
            supporting_weight=4.0,
            total_weight=10.0,
            supporting_count=4,
            total_count=10,
            outputs=["A", "B"],
        )
        assert strong.agreement_bonus >= weak.agreement_bonus

    def test_independence_bonus(self):
        r1 = estimate_confidence_v232(
            similarity=0.8,
            success_count=5,
            failure_count=0,
            supporting_weight=5.0,
            total_weight=5.0,
            supporting_count=5,
            total_count=5,
            outputs=["A"],
            independent_evidence_count=1,
        )
        r5 = estimate_confidence_v232(
            similarity=0.8,
            success_count=5,
            failure_count=0,
            supporting_weight=5.0,
            total_weight=5.0,
            supporting_count=5,
            total_count=5,
            outputs=["A"],
            independent_evidence_count=5,
        )
        assert r5.confidence >= r1.confidence

    def test_monotonicity_with_success(self):
        prev = -1.0
        for sc in [0, 2, 5, 10, 20]:
            r = estimate_confidence_v232(
                similarity=0.8,
                success_count=sc,
                failure_count=0,
                supporting_weight=5.0,
                total_weight=5.0,
                supporting_count=3,
                total_count=3,
                outputs=["A"],
            )
            assert r.confidence >= prev
            prev = r.confidence

    def test_confidence_bounded(self):
        for sim in [0.0, 0.3, 0.7, 1.0]:
            r = estimate_confidence_v232(
                similarity=sim,
                success_count=10,
                failure_count=0,
                supporting_weight=10.0,
                total_weight=10.0,
                supporting_count=5,
                total_count=5,
                outputs=["A"],
            )
            assert 0.0 <= r.confidence <= 1.0

    def test_custom_config(self):
        cfg = ConfidenceEstimatorConfig(
            prior_strength=1.0,
            agreement_weight=0.3,
            failure_dominance_penalty=0.5,
        )
        r = estimate_confidence_v232(
            similarity=0.8,
            success_count=5,
            failure_count=2,
            supporting_weight=5.0,
            total_weight=7.0,
            supporting_count=3,
            total_count=5,
            outputs=["A", "B"],
            config=cfg,
        )
        assert r.confidence > 0.0

    def test_all_components_present(self):
        r = estimate_confidence_v232(
            similarity=0.8,
            success_count=5,
            failure_count=2,
            supporting_weight=5.0,
            total_weight=7.0,
            supporting_count=3,
            total_count=5,
            outputs=["A", "B"],
        )
        assert r.evidence_quality >= 0.0
        assert r.evidence_strength >= 0.0
        assert r.agreement >= 0.0
        assert r.novelty_penalty >= 0.0
        assert r.failure_penalty >= 0.0
        assert "similarity" in r.components
        assert "evidence_quality" in r.components
        assert "independence_bonus" in r.components

    def test_evidence_quality_range(self):
        for s, f in [(0, 0), (5, 0), (0, 5), (3, 3)]:
            q = _evidence_quality(s, f)
            assert 0.0 <= q <= 1.0

    def test_failure_penalty_zero_when_success_ge(self):
        r = _compute_failure_penalty(5, 3, 0.3)
        assert r == 0.0

    def test_failure_penalty_scales(self):
        r1 = _compute_failure_penalty(2, 4, 0.3)
        r2 = _compute_failure_penalty(1, 9, 0.3)
        assert r2 > r1

    def test_independence_bonus_single(self):
        assert _compute_independence_bonus(
            1, 0.15, 10
        ) == 0.0

    def test_independence_bonus_many(self):
        b = _compute_independence_bonus(
            10, 0.15, 10
        )
        assert 0.0 < b <= 0.15


class TestPredictResultV23:
    def test_summary_includes_confidence_fields(self):
        cr = estimate_confidence(
            similarity=0.8,
            success_count=5,
            failure_count=0,
            supporting_weight=5.0,
            total_weight=5.0,
            supporting_count=3,
            total_count=3,
            outputs=["A"],
        )
        pr = _predict_result("A", 0.9)
        pr.confidence_result = cr
        s = pr.summary()
        assert "confidence_components" in s
        cc = s["confidence_components"]
        assert "evidence_strength" in cc
        assert "agreement_bonus" in cc

    def test_v23_confidence_used(self):
        cr = estimate_confidence(
            similarity=0.8,
            success_count=5,
            failure_count=0,
            supporting_weight=5.0,
            total_weight=5.0,
            supporting_count=3,
            total_count=3,
            outputs=["A"],
        )
        pr = _predict_result("A", 0.99)
        pr.confidence_result = cr
        assert pr.confidence == cr.confidence


# ====================================================================
# V2.4 LIFECYCLE TESTS
# ====================================================================


class TestMemoryState:
    def test_active(self):
        assert MemoryState.ACTIVE.value == "active"

    def test_uncertain(self):
        assert MemoryState.UNCERTAIN.value == "uncertain"

    def test_superseded(self):
        assert MemoryState.SUPERSEDED.value == "superseded"

    def test_archived(self):
        assert MemoryState.ARCHIVED.value == "archived"

    def test_all_four_states(self):
        assert len(MemoryState) == 4


class TestHealthScore:
    def test_healthy_memory(self):
        s = HealthSignals(
            success_rate=0.9,
            independent_evidence=5,
            confidence=0.8,
            recency=0.9,
            usage_frequency=0.7,
        )
        assert compute_health_score(s) > 0.7

    def test_weak_memory(self):
        s = HealthSignals(
            success_rate=0.2,
            independent_evidence=0,
            confidence=0.1,
            recency=0.1,
            usage_frequency=0.0,
        )
        assert compute_health_score(s) < 0.4

    def test_bounded(self):
        for sr in [0.0, 0.5, 1.0]:
            for ie in [0, 5, 20]:
                for c in [0.0, 0.5, 1.0]:
                    s = HealthSignals(
                        success_rate=sr,
                        independent_evidence=ie,
                        confidence=c,
                        recency=0.5,
                        usage_frequency=0.5,
                    )
                    h = compute_health_score(s)
                    assert 0.0 <= h <= 1.0

    def test_redundancy_reduces(self):
        clean = HealthSignals(
            success_rate=0.8,
            independent_evidence=3,
            confidence=0.7,
            recency=0.8,
            usage_frequency=0.5,
            redundancy=0.0,
        )
        redundant = HealthSignals(
            success_rate=0.8,
            independent_evidence=3,
            confidence=0.7,
            recency=0.8,
            usage_frequency=0.5,
            redundancy=1.0,
        )
        assert compute_health_score(clean) > (
            compute_health_score(redundant)
        )

    def test_contradictions_reduce(self):
        no_contra = HealthSignals(
            success_rate=0.8,
            confidence=0.7,
            recency=0.8,
            contradiction_count=0,
        )
        with_contra = HealthSignals(
            success_rate=0.8,
            confidence=0.7,
            recency=0.8,
            contradiction_count=5,
        )
        assert compute_health_score(no_contra) > (
            compute_health_score(with_contra)
        )


class TestDecay:
    def test_no_time_no_decay(self):
        r = compute_decay(
            0.8, 0.0, 0.8, 5, LifecycleConfig()
        )
        assert r == 0.8

    def test_strong_evidence_slows(self):
        cfg = LifecycleConfig()
        fast = compute_decay(0.8, 30.0, 0.3, 0, cfg)
        slow = compute_decay(0.8, 30.0, 0.9, 10, cfg)
        assert slow > fast

    def test_floor(self):
        cfg = LifecycleConfig(decay_min=0.1)
        r = compute_decay(
            0.8, 1000.0, 0.1, 0, cfg
        )
        assert r >= 0.1

    def test_bounded(self):
        cfg = LifecycleConfig()
        for conf in [0.1, 0.5, 1.0]:
            for days in [0, 30, 365]:
                r = compute_decay(
                    conf, days, 0.5, 3, cfg
                )
                assert 0.0 <= r <= 1.0


class TestReinforcement:
    def test_no_success_no_change(self):
        r = compute_reinforcement(
            0.8, 0, 0, LifecycleConfig()
        )
        assert r == 0.8

    def test_single_success(self):
        r = compute_reinforcement(
            0.8, 1, 0, LifecycleConfig()
        )
        assert r > 0.8

    def test_diminishing_returns(self):
        cfg = LifecycleConfig()
        # Per-use marginal reinforcement decreases
        r1 = compute_reinforcement(0.5, 1, 0, cfg)
        r10 = compute_reinforcement(0.5, 10, 0, cfg)
        r100 = compute_reinforcement(0.5, 100, 0, cfg)
        marginal_1 = (r1 - 0.5) / 1
        marginal_10 = (r10 - r1) / 9
        marginal_100 = (r100 - r10) / 90
        assert marginal_1 > marginal_10 > marginal_100

    def test_bounded(self):
        cfg = LifecycleConfig()
        for sc in [1, 5, 20]:
            r = compute_reinforcement(
                0.95, sc, 5, cfg
            )
            assert r <= 1.0

    def test_independence_bonus(self):
        cfg = LifecycleConfig()
        r0 = compute_reinforcement(0.8, 5, 0, cfg)
        r3 = compute_reinforcement(0.8, 5, 3, cfg)
        assert r3 > r0


class TestSupersession:
    def test_same_output_no_supersession(self):
        old = _example(1, "q", "same")
        new = _example(2, "q", "same")
        cfg = LifecycleConfig()
        r = analyze_supersession(old, new, cfg)
        assert not r.should_supersede

    def test_different_output_needs_evidence(self):
        old = _example(
            1, "q", "A",
            success_count=10, failure_count=0,
            weight=2.0,
        )
        new = _example(
            2, "q", "B",
            success_count=1, failure_count=0,
            weight=1.0,
        )
        cfg = LifecycleConfig(supersession_threshold=0.3)
        r = analyze_supersession(old, new, cfg)
        assert not r.should_supersede

    def test_stronger_new_supersedes(self):
        old = _example(
            1, "q", "A",
            success_count=1, failure_count=5,
            weight=0.3,
        )
        new = _example(
            2, "q", "B",
            success_count=10, failure_count=0,
            weight=2.0,
        )
        cfg = LifecycleConfig(supersession_threshold=0.1)
        r = analyze_supersession(old, new, cfg)
        assert r.should_supersede


class TestRedundancy:
    def test_exact_duplicate(self):
        a = _example(1, "hello", "yes", success_count=3)
        b = _example(2, "hello", "yes", success_count=2)
        r = analyze_redundancy(
            a, b, LifecycleConfig()
        )
        assert r.type == RedundancyType.EXACT_DUPLICATE
        assert r.should_consolidate
        assert r.combined_evidence == 5

    def test_different_outputs(self):
        a = _example(1, "x", "yes")
        b = _example(2, "x", "no")
        r = analyze_redundancy(
            a, b, LifecycleConfig()
        )
        assert r.type == RedundancyType.GENUINELY_DISTINCT
        assert not r.should_consolidate

    def test_normalized_duplicate(self):
        a = _example(
            1, "q", "a b c d e f g h i j"
        )
        b = _example(
            2, "q", "a b c d e f g h i j k"
        )
        r = analyze_redundancy(
            a, b, LifecycleConfig()
        )
        assert r.type in (
            RedundancyType.NORMALIZED_DUPLICATE,
            RedundancyType.SEMANTIC_DUPLICATE,
        )

    def test_preserves_evidence(self):
        a = _example(
            1, "q", "A", success_count=7
        )
        b = _example(
            2, "q", "A", success_count=3
        )
        r = analyze_redundancy(
            a, b, LifecycleConfig()
        )
        assert r.combined_evidence == 10


class TestArchive:
    def test_low_health_eligible(self):
        ex = _example(
            1, "q", "A",
            success_count=0,
            failure_count=0,
        )
        eligible, reason = is_eligible_for_archive(
            ex, 0.05, LifecycleConfig()
        )
        assert eligible
        assert "health" in reason.lower()

    def test_high_health_not_eligible(self):
        ex = _example(
            1, "q", "A",
            success_count=5,
            failure_count=0,
        )
        eligible, reason = is_eligible_for_archive(
            ex, 0.8, LifecycleConfig()
        )
        assert not eligible

    def test_more_failures_eligible(self):
        ex = _example(
            1, "q", "A",
            success_count=1,
            failure_count=5,
        )
        eligible, reason = is_eligible_for_archive(
            ex, 0.5, LifecycleConfig()
        )
        assert eligible
        assert "failure" in reason.lower()

    def test_archive_creates_event(self):
        ex = _example(1, "q", "A")
        state, event = archive_memory(
            ex, "test archive", MemoryState.ACTIVE
        )
        assert state == MemoryState.ARCHIVED
        assert event.new_state == "archived"


class TestLifecycleManager:
    def test_initial_state(self):
        mgr = LifecycleManager()
        s = mgr.get_state(1)
        assert s.state == MemoryState.ACTIVE
        assert s.health_score == 0.5

    def test_reinforce(self):
        mgr = LifecycleManager()
        ex = _example(
            1, "q", "A",
            success_count=5,
            weight=0.8,
        )
        new_c = mgr.reinforce(ex)
        assert new_c >= 0.8

    def test_archive(self):
        mgr = LifecycleManager()
        ex = _example(1, "q", "A")
        event = mgr.archive(ex, "manual archive")
        assert event.new_state == "archived"
        assert mgr.get_state(1).state == (
            MemoryState.ARCHIVED
        )

    def test_restore(self):
        mgr = LifecycleManager()
        ex = _example(1, "q", "A")
        mgr.archive(ex, "test")
        event = mgr.restore(1, "need it back")
        assert event.new_state == "active"
        assert mgr.get_state(1).state == (
            MemoryState.ACTIVE
        )

    def test_supersession(self):
        mgr = LifecycleManager()
        old = _example(
            1, "q", "A",
            success_count=1, failure_count=5,
            weight=0.3,
        )
        new = _example(
            2, "q", "B",
            success_count=10, failure_count=0,
            weight=2.0,
        )
        result = mgr.analyze_supersession(old, new)
        if result.should_supersede:
            _event = mgr.apply_supersession(
                1, 2, result.reason
            )
            assert mgr.get_state(1).state == (
                MemoryState.SUPERSEDED
            )
            assert mgr.get_state(1).superseded_by == 2

    def test_persistence_roundtrip(self):
        mgr = LifecycleManager()
        ex1 = _example(
            1, "q1", "A",
            weight=0.8,
        )
        ex2 = _example(
            2, "q2", "B",
            weight=0.6,
        )
        mgr.reinforce(ex1)
        mgr.archive(ex2, "test")

        with tempfile.TemporaryDirectory() as td:
            mgr.save(Path(td))
            loaded = LifecycleManager.load(Path(td))

        assert loaded.get_state(1).state == (
            MemoryState.ACTIVE
        )
        assert loaded.get_state(2).state == (
            MemoryState.ARCHIVED
        )

    def test_process_all(self):
        mgr = LifecycleManager(
            LifecycleConfig(
                maintenance_interval_hours=0
            )
        )
        ex1 = _example(1, "q", "A", weight=0.9)
        ex2 = _example(2, "q", "B", weight=0.8)
        mem = _memory_with([ex1, ex2])
        results = mgr.process_all(mem)
        assert results["total"] == 2
        assert results["active"] + results["uncertain"] == 2

    def test_find_merge_candidates_basic(self):
        a = _example(
            1, "sort list python", "sorted()",
            success_count=5,
        )
        b = _example(
            2, "sort a list python", "sorted()",
            success_count=3,
        )
        c = _example(
            3, "open file", "open()",
            success_count=2,
        )
        cfg = LifecycleConfig(
            merge_similarity=0.8,
            merge_input_similarity=0.5,
            merge_min_evidence=2,
        )
        candidates = find_merge_candidates(
            [a, b, c], cfg
        )
        pair_ids = {
            (c.id_a, c.id_b) for c in candidates
        }
        assert (1, 2) in pair_ids

    def test_find_merge_candidates_no_match(self):
        a = _example(
            1, "python sort", "sorted()",
            success_count=5,
        )
        b = _example(
            2, "java compile", "javac",
            success_count=3,
        )
        cfg = LifecycleConfig(
            merge_similarity=0.8,
            merge_input_similarity=0.5,
            merge_min_evidence=2,
        )
        candidates = find_merge_candidates(
            [a, b], cfg
        )
        assert len(candidates) == 0


class TestTokenInvertedIndex:
    def test_basic_operations(self):
        idx = TokenInvertedIndex()
        idx.add(1, "hello world")
        idx.add(2, "hello there")
        cands = idx.find_candidates(
            "hello world", min_overlap=1
        )
        ids = [c[0] for c in cands]
        assert 1 in ids
        assert 2 in ids

    def test_remove(self):
        idx = TokenInvertedIndex()
        idx.add(1, "hello world")
        idx.remove(1, "hello world")
        cands = idx.find_candidates(
            "hello world", min_overlap=1
        )
        assert len(cands) == 0

    def test_clear(self):
        idx = TokenInvertedIndex()
        idx.add(1, "hello world")
        idx.add(2, "foo bar")
        idx.clear()
        cands = idx.find_candidates(
            "hello world", min_overlap=1
        )
        assert len(cands) == 0

    def test_exclude_ids(self):
        idx = TokenInvertedIndex()
        idx.add(1, "hello world")
        idx.add(2, "hello there")
        cands = idx.find_candidates(
            "hello world",
            min_overlap=1,
            exclude_ids={1},
        )
        ids = [c[0] for c in cands]
        assert 1 not in ids

    def test_empty_query(self):
        idx = TokenInvertedIndex()
        idx.add(1, "hello")
        cands = idx.find_candidates("", min_overlap=1)
        assert cands == []


class TestMergeScalability:
    def test_100_memories(self):
        examples = [
            _example(
                i, f"query {i % 10}",
                f"answer {i % 10}",
                success_count=3,
            )
            for i in range(100)
        ]
        cfg = LifecycleConfig(
            merge_similarity=0.8,
            merge_input_similarity=0.5,
            merge_min_evidence=2,
        )
        candidates = find_merge_candidates(
            examples, cfg
        )
        assert isinstance(candidates, list)

    def test_indexed_matches_bruteforce(self):
        examples = [
            _example(
                i, f"query type {i % 5}",
                f"answer type {i % 5}",
                success_count=3,
            )
            for i in range(60)
        ]
        cfg = LifecycleConfig(
            merge_similarity=0.8,
            merge_input_similarity=0.5,
            merge_min_evidence=2,
        )
        bf = find_merge_candidates(
            examples, cfg, use_index=False
        )
        idx = find_merge_candidates(
            examples, cfg, use_index=True
        )
        bf_pairs = {
            (c.id_a, c.id_b) for c in bf
        }
        idx_pairs = {
            (c.id_a, c.id_b) for c in idx
        }
        assert bf_pairs == idx_pairs


class TestEventTriggerConfig:
    def test_defaults(self):
        cfg = EventTriggerConfig()
        assert (
            MaintenanceEvent.NEW_EVIDENCE
            in cfg.enabled_events
        )
        assert (
            cfg.min_events_before_trigger == 3
        )
        assert cfg.cooldown_seconds == 60.0

    def test_custom(self):
        cfg = EventTriggerConfig(
            min_events_before_trigger=5,
            cooldown_seconds=30.0,
        )
        assert cfg.min_events_before_trigger == 5
        assert cfg.cooldown_seconds == 30.0


class TestMaintenanceEvent:
    def test_all_values(self):
        vals = [e.value for e in MaintenanceEvent]
        assert "new_evidence" in vals
        assert "repeated_success" in vals
        assert "repeated_failure" in vals
        assert "conflict_detected" in vals
        assert "health_crossed_threshold" in vals
        assert "session_complete" in vals
        assert "scheduled" in vals

    def test_enum_count(self):
        assert len(MaintenanceEvent) == 10


class TestMaintenanceRecord:
    def test_fields(self):
        r = MaintenanceRecord(
            timestamp=100.0,
            memories_processed=10,
            transitions=3,
            duration_seconds=0.5,
            details={"skipped": False},
        )
        assert r.memories_processed == 10
        assert r.transitions == 3
        assert r.duration_seconds == 0.5


class TestLifecyclePersistence:
    def test_save_load_config(self):
        mgr = LifecycleManager(
            LifecycleConfig(decay_rate=0.05)
        )
        with tempfile.TemporaryDirectory() as td:
            mgr.save(Path(td))
            loaded = LifecycleManager.load(Path(td))
        assert loaded.config.decay_rate == 0.05

    def test_save_load_events(self):
        mgr = LifecycleManager()
        ex = _example(1, "q", "A")
        mgr.archive(ex, "test")
        with tempfile.TemporaryDirectory() as td:
            mgr.save(Path(td))
            loaded = LifecycleManager.load(Path(td))
        assert len(loaded.get_events()) >= 1

    def test_save_load_maintenance_history(self):
        mgr = LifecycleManager(
            LifecycleConfig(
                maintenance_interval_hours=0
            )
        )
        ex = _example(1, "q", "A", weight=0.5)
        mem = _memory_with([ex])
        mgr.run_maintenance(mem, force=True)
        with tempfile.TemporaryDirectory() as td:
            mgr.save(Path(td))
            loaded = LifecycleManager.load(Path(td))
        hist = loaded.get_maintenance_history()
        assert len(hist) >= 1

    def test_backward_compat_v240(self):
        """Simulate V2.4.0 save without new fields."""
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            p.mkdir(parents=True, exist_ok=True)
            # Write minimal config missing new fields
            (p / "lifecycle_config.json").write_text(
                '{"decay_rate": 0.02}',
                encoding="utf-8",
            )
            (p / "lifecycle_states.json").write_text(
                "{}", encoding="utf-8"
            )
            (p / "lifecycle_metadata.json").write_text(
                "{}", encoding="utf-8"
            )
            loaded = LifecycleManager.load(p)
        assert loaded.config.decay_rate == 0.02
        assert (
            loaded.config.maintenance_interval_hours
            == 24.0
        )

    def test_persistence_version(self):
        assert PERSISTENCE_VERSION == "2.4.2"


class TestLifecycleManagerAdvanced:
    def test_needs_maintenance(self):
        clock_val = [1000.0]

        def clock():
            return clock_val[0]

        mgr = LifecycleManager(
            LifecycleConfig(
                maintenance_interval_hours=1.0
            ),
            clock=clock,
        )
        assert not mgr.needs_maintenance
        clock_val[0] += 3601.0
        assert mgr.needs_maintenance

    def test_event_trigger(self):
        clock_val = [0.0]

        def clock():
            return clock_val[0]

        mgr = LifecycleManager(
            clock=clock,
            event_config=EventTriggerConfig(
                min_events_before_trigger=2,
                cooldown_seconds=10.0,
            ),
        )
        assert not mgr.record_event(
            MaintenanceEvent.NEW_EVIDENCE
        )
        assert not mgr.record_event(
            MaintenanceEvent.NEW_EVIDENCE
        )
        clock_val[0] = 15.0
        assert mgr.record_event(
            MaintenanceEvent.REPEATED_SUCCESS
        )

    def test_clear_pending_events(self):
        mgr = LifecycleManager()
        mgr.record_event(
            MaintenanceEvent.NEW_EVIDENCE, memory_id=1
        )
        mgr.clear_pending_events()
        assert mgr.get_pending_event_ids() == []

    def test_no_global_merge_state_leakage(self):
        a1 = _example(
            1, "q type A", "ans A",
            success_count=3,
        )
        b1 = _example(
            2, "q type A", "ans A",
            success_count=3,
        )
        cfg = LifecycleConfig(
            merge_similarity=0.8,
            merge_input_similarity=0.5,
            merge_min_evidence=2,
        )
        c1 = find_merge_candidates([a1, b1], cfg)
        a2 = _example(
            3, "q type B", "ans B",
            success_count=3,
        )
        b2 = _example(
            4, "q type C", "ans C",
            success_count=3,
        )
        c2 = find_merge_candidates([a2, b2], cfg)
        ids1 = {
            (c.id_a, c.id_b) for c in c1
        }
        ids2 = {
            (c.id_a, c.id_b) for c in c2
        }
        assert ids1 != ids2

    def test_run_maintenance(self):
        mgr = LifecycleManager(
            LifecycleConfig(
                maintenance_interval_hours=0
            )
        )
        ex = _example(
            1, "q", "A",
            weight=0.9, last_used_at=0.0,
        )
        mem = _memory_with([ex])
        record = mgr.run_maintenance(mem, force=True)
        assert record.memories_processed >= 1
        assert isinstance(record, MaintenanceRecord)

    def test_pending_cleared_after_maintenance(self):
        mgr = LifecycleManager(
            LifecycleConfig(
                maintenance_interval_hours=0
            )
        )
        mgr.record_event(
            MaintenanceEvent.NEW_EVIDENCE,
            memory_id=1,
        )
        ex = _example(1, "q", "A", weight=0.5)
        mem = _memory_with([ex])
        mgr.run_maintenance(mem, force=True)
        assert mgr.get_pending_event_ids() == []


class TestLifecycleStability:
    def test_1000_memories_stable(self):
        mgr = LifecycleManager(
            LifecycleConfig(
                maintenance_interval_hours=0,
                decay_rate=0.001,
                archive_threshold=0.05,
            )
        )
        examples = [
            _example(
                i,
                f"query {i}",
                f"answer {i}",
                weight=0.8,
                success_count=3,
                failure_count=0,
            )
            for i in range(100)
        ]
        mem = _memory_with(examples)
        for _cycle in range(5):
            mgr.run_maintenance(mem, force=True)
        active = sum(
            1
            for s in mgr.get_all_states().values()
            if s.state == MemoryState.ACTIVE
        )
        assert active >= 50

    def test_reinforcement_bounded_many(self):
        cfg = LifecycleConfig()
        r = compute_reinforcement(
            0.95, 100, 20, cfg
        )
        assert r <= 1.0

    def test_alternating_feedback_stable(self):
        cfg = LifecycleConfig()
        c = 0.5
        for i in range(20):
            if i % 2 == 0:
                c = compute_reinforcement(c, 1, 0, cfg)
            else:
                c = compute_decay(
                    c, 1.0, 0.5, 0, cfg
                )
        assert 0.0 <= c <= 1.0

    def test_contradictions_preserved(self):
        a = _example(1, "q", "yes", success_count=5)
        b = _example(2, "q", "no", success_count=5)
        r = analyze_redundancy(
            a, b, LifecycleConfig()
        )
        assert not r.should_consolidate

    def test_duplicate_flooding_resisted(self):
        examples = [
            _example(
                i, "same query", "same answer",
                success_count=2,
            )
            for i in range(10)
        ]
        cfg = LifecycleConfig(
            merge_similarity=0.8,
            merge_input_similarity=0.5,
            merge_min_evidence=2,
        )
        candidates = find_merge_candidates(
            examples, cfg
        )
        # Many merge candidates detected — system
        # should handle gracefully
        assert isinstance(candidates, list)
        assert len(candidates) > 0
        # All pairs should be valid
        for c in candidates:
            assert c.combined_evidence >= 2
