"""Unit tests for V2.2 conflict detection and resolution."""

from __future__ import annotations

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
from core.learner.hybrid_memory import HybridExample

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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
    )


# ---------------------------------------------------------------------------
# Output similarity
# ---------------------------------------------------------------------------


class TestOutputSimilarity:
    def test_identical_strings(self):
        assert _output_similarity("hello", "hello") == 1.0

    def test_same_words_different_order(self):
        sim = _output_similarity("hello world", "world hello")
        assert sim == 1.0  # Jaccard is order-independent

    def test_completely_different(self):
        sim = _output_similarity("foo bar", "xyz abc")
        assert sim == 0.0

    def test_partial_overlap(self):
        sim = _output_similarity("foo bar baz", "foo qux")
        # intersection={foo}, union={foo,bar,baz,qux} = 1/4 = 0.25
        assert abs(sim - 0.25) < 0.01

    def test_empty_strings(self):
        assert _output_similarity("", "") == 1.0

    def test_one_empty(self):
        assert _output_similarity("hello", "") == 0.0

    def test_case_insensitive(self):
        assert _output_similarity("Hello World", "hello world") == 1.0


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------


class TestConflictDetection:
    def test_no_conflict_identical_output(self):
        candidates = [
            (1, 0.9, "use sorted()"),
            (2, 0.8, "use sorted()"),
        ]
        examples = {
            1: _example(1, "sort list", "use sorted()"),
            2: _example(2, "sort array", "use sorted()"),
        }
        conflicts = detect_conflicts(candidates, examples)
        assert len(conflicts) == 0

    def test_conflict_different_output_same_input(self):
        candidates = [
            (1, 0.9, "use sorted()"),
            (2, 0.85, "use list.sort()"),
        ]
        examples = {
            1: _example(1, "sort a list", "use sorted()"),
            2: _example(2, "sort a list", "use list.sort()"),
        }
        conflicts = detect_conflicts(candidates, examples)
        assert len(conflicts) == 1
        assert conflicts[0].state == ConflictState.CONFIRMED
        assert conflicts[0].strength > 0.8

    def test_no_conflict_different_input(self):
        candidates = [
            (1, 0.9, "open()"),
            (2, 0.8, "reverse"),
        ]
        examples = {
            1: _example(1, "open a file", "open()"),
            2: _example(2, "reverse a string", "reverse"),
        }
        conflicts = detect_conflicts(candidates, examples)
        # Different contexts — may or may not conflict depending on similarity
        # These inputs are quite different, so likely no conflict
        assert len(conflicts) == 0 or conflicts[0].state == ConflictState.POSSIBLE

    def test_possible_conflict_similar_input(self):
        candidates = [
            (1, 0.9, "use X"),
            (2, 0.85, "use Y"),
        ]
        examples = {
            1: _example(1, "sort a list of items", "use X"),
            2: _example(2, "sort a list", "use Y"),
        }
        conflicts = detect_conflicts(candidates, examples)
        # Very similar inputs — should detect conflict
        assert len(conflicts) >= 1
        assert conflicts[0].state in (ConflictState.POSSIBLE, ConflictState.CONFIRMED)

    def test_single_candidate_no_conflict(self):
        candidates = [(1, 0.9, "use sorted()")]
        examples = {1: _example(1, "sort list", "use sorted()")}
        conflicts = detect_conflicts(candidates, examples)
        assert len(conflicts) == 0

    def test_empty_candidates(self):
        conflicts = detect_conflicts([], {})
        assert len(conflicts) == 0

    def test_three_way_conflict(self):
        candidates = [
            (1, 0.9, "A"),
            (2, 0.85, "B"),
            (3, 0.8, "C"),
        ]
        examples = {
            1: _example(1, "task X", "A"),
            2: _example(2, "task X", "B"),
            3: _example(3, "task X", "C"),
        }
        conflicts = detect_conflicts(candidates, examples)
        # Three different outputs for same input — multiple conflicts
        assert len(conflicts) >= 1


# ---------------------------------------------------------------------------
# Evidence gathering
# ---------------------------------------------------------------------------


class TestEvidenceGathering:
    def test_gather_evidence_basic(self):
        conflict = Conflict(
            involved_ids=[1, 2],
            outputs=["A", "B"],
            state=ConflictState.CONFIRMED,
            strength=0.9,
        )
        examples = {
            1: _example(1, "x", "A", success_count=5, failure_count=1, weight=2.0),
            2: _example(2, "x", "B", success_count=3, failure_count=2, weight=1.5),
        }
        relevance = {1: 0.9, 2: 0.85}
        gather_evidence(conflict, examples, relevance)

        assert len(conflict.evidence) == 2
        assert conflict.evidence[0].success_rate == 5 / 6
        assert conflict.evidence[1].success_rate == 3 / 5

    def test_gather_evidence_neutral_for_untested(self):
        conflict = Conflict(involved_ids=[1], outputs=["A"])
        examples = {1: _example(1, "x", "A")}
        gather_evidence(conflict, examples, {1: 0.9})
        assert conflict.evidence[0].success_rate == 0.5

    def test_gather_evidence_with_recency(self):
        conflict = Conflict(involved_ids=[1], outputs=["A"])
        examples = {1: _example(1, "x", "A")}
        recency = {1: 0.8}
        gather_evidence(conflict, examples, {1: 0.9}, recency)
        assert conflict.evidence[0].recency == 0.8


# ---------------------------------------------------------------------------
# Evidence comparison
# ---------------------------------------------------------------------------


class TestEvidenceComparison:
    def test_clear_winner_resolved(self):
        conflict = Conflict(
            involved_ids=[1, 2],
            outputs=["A", "B"],
            state=ConflictState.CONFIRMED,
            strength=0.9,
        )
        conflict.evidence = [
            Evidence(1, "A", relevance=0.9, success_rate=0.9,
                     success_count=18, failure_count=2, weight=3.0, recency=0.9),
            Evidence(2, "B", relevance=0.85, success_rate=0.5,
                     success_count=5, failure_count=5, weight=1.0, recency=0.5),
        ]
        compare_evidence(conflict)
        assert conflict.state == ConflictState.RESOLVED
        assert conflict.selected_output == "A"
        assert conflict.winner_id == 1

    def test_close_scores_unresolved(self):
        conflict = Conflict(
            involved_ids=[1, 2],
            outputs=["A", "B"],
            state=ConflictState.CONFIRMED,
            strength=0.9,
        )
        conflict.evidence = [
            Evidence(1, "A", relevance=0.9, success_rate=0.8,
                     success_count=8, failure_count=2, weight=2.0, recency=0.8),
            Evidence(2, "B", relevance=0.88, success_rate=0.8,
                     success_count=8, failure_count=2, weight=2.0, recency=0.8),
        ]
        compare_evidence(conflict)
        assert conflict.state == ConflictState.UNRESOLVED
        assert conflict.confidence_penalty > 0.3

    def test_relevance_dominates(self):
        """Higher relevance should win even with fewer uses."""
        conflict = Conflict(
            involved_ids=[1, 2],
            outputs=["A", "B"],
            state=ConflictState.CONFIRMED,
            strength=0.9,
        )
        conflict.evidence = [
            Evidence(1, "A", relevance=0.95, success_rate=0.7,
                     success_count=7, failure_count=3, weight=1.5, recency=0.7),
            Evidence(2, "B", relevance=0.5, success_rate=0.95,
                     success_count=19, failure_count=1, weight=4.0, recency=0.9),
        ]
        compare_evidence(conflict)
        # A should win despite fewer uses, because relevance is much higher
        assert conflict.selected_output == "A"

    def test_insufficient_samples_penalized(self):
        """Memories with few uses should not dominate."""
        conflict = Conflict(
            involved_ids=[1, 2],
            outputs=["A", "B"],
            state=ConflictState.CONFIRMED,
            strength=0.9,
        )
        conflict.evidence = [
            Evidence(1, "A", relevance=0.9, success_rate=1.0,
                     success_count=1, failure_count=0, weight=1.0, recency=0.8),
            Evidence(2, "B", relevance=0.85, success_rate=0.8,
                     success_count=20, failure_count=5, weight=2.0, recency=0.7),
        ]
        compare_evidence(conflict)
        # B should win — A has only 1 use (insufficient samples)
        assert conflict.selected_output == "B"


# ---------------------------------------------------------------------------
# Evidence score
# ---------------------------------------------------------------------------


class TestEvidenceScore:
    def test_score_range(self):
        ev = Evidence(1, "A", relevance=1.0, success_rate=1.0,
                       success_count=100, failure_count=0, weight=5.0, recency=1.0)
        score = _evidence_score(ev)
        assert 0.0 <= score <= 1.0

    def test_zero_relevance_gives_zero_score(self):
        ev = Evidence(1, "A", relevance=0.0, success_rate=1.0,
                       success_count=100, failure_count=0, weight=5.0, recency=1.0)
        score = _evidence_score(ev)
        assert score == 0.0

    def test_high_relevance_high_score(self):
        ev = Evidence(1, "A", relevance=0.9, success_rate=0.9,
                       success_count=18, failure_count=2, weight=3.0, recency=0.9)
        score = _evidence_score(ev)
        assert score > 0.5

    def test_success_count_diminishing_returns(self):
        ev1 = Evidence(1, "A", relevance=0.8, success_rate=0.9,
                        success_count=10, failure_count=1, weight=2.0, recency=0.8)
        ev2 = Evidence(2, "A", relevance=0.8, success_rate=0.9,
                        success_count=100, failure_count=11, weight=2.0, recency=0.8)
        s1 = _evidence_score(ev1)
        s2 = _evidence_score(ev2)
        # Both should be close — diminishing returns
        assert abs(s1 - s2) < 0.15


# ---------------------------------------------------------------------------
# Conflict config
# ---------------------------------------------------------------------------


class TestConflictConfig:
    def test_default_values(self):
        config = ConflictConfig()
        assert config.input_similarity_threshold == 0.75
        assert config.output_equality_threshold == 0.0
        assert config.evidence_margin == 0.1
        assert config.context_similarity_threshold == 0.9
        assert config.min_evidence_samples == 3

    def test_custom_values(self):
        config = ConflictConfig(
            input_similarity_threshold=0.8,
            evidence_margin=0.2,
            min_evidence_samples=5,
        )
        assert config.input_similarity_threshold == 0.8
        assert config.evidence_margin == 0.2
        assert config.min_evidence_samples == 5


# ---------------------------------------------------------------------------
# Conflict dataclass
# ---------------------------------------------------------------------------


class TestConflictDataclass:
    def test_initial_state(self):
        c = Conflict(involved_ids=[1, 2], outputs=["A", "B"])
        assert c.state == ConflictState.NONE
        assert c.strength == 0.0
        assert c.selected_output is None
        assert c.confidence_penalty == 0.0

    def test_resolved_conflict(self):
        c = Conflict(
            involved_ids=[1, 2],
            outputs=["A", "B"],
            state=ConflictState.RESOLVED,
            selected_output="A",
            winner_id=1,
            confidence_penalty=0.1,
        )
        assert c.state == ConflictState.RESOLVED
        assert c.selected_output == "A"
