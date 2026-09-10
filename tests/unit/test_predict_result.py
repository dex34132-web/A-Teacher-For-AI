"""Unit tests for PredictResult (V2.2 conflict-aware prediction wrapper)."""

from __future__ import annotations

from core.learner.conflict import Conflict, ConflictState
from core.learner.learner_v1 import Prediction
from core.learner.predict_result import PredictResult


class TestPredictResult:
    def test_basic_prediction(self):
        pred = Prediction(output="hello", confidence=0.8, similarities=[])
        result = PredictResult(prediction=pred)
        assert result.output == "hello"
        assert result.confidence == 0.8
        assert result.base_confidence == 0.8
        assert result.has_conflict is False
        assert result.is_resolved is True
        assert result.is_unresolved is False

    def test_conflict_reduces_confidence(self):
        pred = Prediction(output="hello", confidence=0.8, similarities=[])
        result = PredictResult(
            prediction=pred,
            conflicts=[],
            overall_conflict_state=ConflictState.UNRESOLVED,
            conflict_confidence_penalty=0.4,
        )
        assert result.confidence == 0.8 * (1.0 - 0.4)
        assert result.base_confidence == 0.8

    def test_has_conflict_property(self):
        pred = Prediction(output="hello", confidence=0.8, similarities=[])
        conflict = Conflict(
            involved_ids=[1, 2],
            outputs=["A", "B"],
            state=ConflictState.UNRESOLVED,
            confidence_penalty=0.3,
        )
        result = PredictResult(
            prediction=pred,
            conflicts=[conflict],
            overall_conflict_state=ConflictState.UNRESOLVED,
            conflict_confidence_penalty=0.3,
        )
        assert result.has_conflict is True
        assert result.is_unresolved is True

    def test_resolved_conflict(self):
        pred = Prediction(output="A", confidence=0.8, similarities=[])
        conflict = Conflict(
            involved_ids=[1, 2],
            outputs=["A", "B"],
            state=ConflictState.RESOLVED,
            selected_output="A",
            winner_id=1,
            confidence_penalty=0.1,
        )
        result = PredictResult(
            prediction=pred,
            conflicts=[conflict],
            overall_conflict_state=ConflictState.RESOLVED,
            conflict_confidence_penalty=0.1,
        )
        assert result.is_resolved is True
        assert result.is_unresolved is False

    def test_conflicting_outputs(self):
        pred = Prediction(output="A", confidence=0.8, similarities=[])
        conflict = Conflict(
            involved_ids=[1, 2],
            outputs=["A", "B"],
            state=ConflictState.CONFIRMED,
        )
        result = PredictResult(
            prediction=pred,
            conflicts=[conflict],
            overall_conflict_state=ConflictState.CONFIRMED,
        )
        assert "A" in result.conflicting_outputs
        assert "B" in result.conflicting_outputs

    def test_conflicting_ids(self):
        pred = Prediction(output="A", confidence=0.8, similarities=[])
        conflict = Conflict(
            involved_ids=[1, 2, 3],
            outputs=["A", "B"],
            state=ConflictState.CONFIRMED,
        )
        result = PredictResult(
            prediction=pred,
            conflicts=[conflict],
            overall_conflict_state=ConflictState.CONFIRMED,
        )
        assert set(result.conflicting_ids) == {1, 2, 3}

    def test_max_conflict_strength(self):
        pred = Prediction(output="A", confidence=0.8, similarities=[])
        c1 = Conflict(involved_ids=[1, 2], outputs=["A", "B"], strength=0.7)
        c2 = Conflict(involved_ids=[3, 4], outputs=["C", "D"], strength=0.9)
        result = PredictResult(
            prediction=pred,
            conflicts=[c1, c2],
            overall_conflict_state=ConflictState.CONFIRMED,
        )
        assert result.max_conflict_strength == 0.9

    def test_to_legacy(self):
        pred = Prediction(output="hello", confidence=0.8, similarities=[])
        result = PredictResult(prediction=pred)
        assert result.to_legacy() is pred

    def test_summary_no_conflict(self):
        pred = Prediction(output="hello", confidence=0.8, similarities=[])
        result = PredictResult(prediction=pred)
        s = result.summary()
        assert s["output"] == "hello"
        assert s["has_conflict"] is False
        assert s["conflict_state"] == "none"

    def test_summary_with_conflict(self):
        pred = Prediction(output="A", confidence=0.8, similarities=[])
        conflict = Conflict(
            involved_ids=[1, 2],
            outputs=["A", "B"],
            state=ConflictState.UNRESOLVED,
            strength=0.85,
            confidence_penalty=0.4,
        )
        result = PredictResult(
            prediction=pred,
            conflicts=[conflict],
            overall_conflict_state=ConflictState.UNRESOLVED,
            conflict_confidence_penalty=0.4,
            selected_conflict=conflict,
        )
        s = result.summary()
        assert s["has_conflict"] is True
        assert s["num_conflicts"] == 1
        assert "A" in s["conflicting_outputs"]
        assert "B" in s["conflicting_outputs"]

    def test_empty_output(self):
        pred = Prediction(output="", confidence=0.0, similarities=[])
        result = PredictResult(prediction=pred)
        assert result.output == ""
        assert result.confidence == 0.0

    def test_similarities_delegated(self):
        pred = Prediction(
            output="hello",
            confidence=0.8,
            similarities=[("text1", 0.9), ("text2", 0.7)],
        )
        result = PredictResult(prediction=pred)
        assert result.similarities == [("text1", 0.9), ("text2", 0.7)]

    def test_confidence_floor_at_zero(self):
        pred = Prediction(output="A", confidence=0.1, similarities=[])
        result = PredictResult(
            prediction=pred,
            conflict_confidence_penalty=0.9,
        )
        assert result.confidence <= 0.01  # Near zero

    def test_confidence_cap_at_one(self):
        pred = Prediction(output="A", confidence=0.9, similarities=[])
        result = PredictResult(
            prediction=pred,
            conflict_confidence_penalty=-0.5,  # Negative penalty
        )
        assert result.confidence == 1.0
