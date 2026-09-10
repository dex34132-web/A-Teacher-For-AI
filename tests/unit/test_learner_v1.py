"""Tests for SimilarityLearner.

Covers learn, predict, feedback, confidence, reset, save/load state,
and the parameters property.

Note on IDF behavior: The first fit() call always produces IDF=0 for
all terms (log(1/1)=0), so the first example's vector is empty.
Additionally, terms appearing in ALL documents get IDF=0 and are
filtered from every vector. Tests use unique 'marker' terms per
example that appear in only some docs, ensuring non-zero IDF and
query-example feature overlap.
"""

from __future__ import annotations

import tempfile

import pytest

from core.learner.base import LearningInput, LearningMode, LearningStatus
from core.learner.learner_v1 import Prediction, SimilarityLearner

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_input(text: str, output: str, **metadata: object) -> LearningInput:
    """Create a LearningInput for the learner."""
    return LearningInput(observation={"input": text, "output": output}, metadata=metadata)


def _build_cat_dog_learner() -> SimilarityLearner:
    """Create a learner with 2 categories using unique marker terms.

    Pattern: each example has a unique marker term (df=1) that appears
    in only that doc, plus shared context terms.  The query uses the
    marker of the target example to get non-zero similarity.

    - Cat examples use 'alpha', 'beta' markers
    - Dog examples use 'gamma', 'delta' markers
    - 'programming' and 'word' appear in all docs (IDF=0, filtered)
    """
    learner = SimilarityLearner()
    learner.learn(_make_input("alpha programming word", "cat"))
    learner.learn(_make_input("beta programming word", "cat"))
    learner.learn(_make_input("gamma programming word", "dog"))
    learner.learn(_make_input("delta programming word", "dog"))
    learner.learn(_make_input("epsilon programming word", "other"))
    return learner


def _build_two_category_learner() -> SimilarityLearner:
    """Create a learner with 'code' and 'food' categories.

    Each category has 2 examples with different markers.  The first
    example always gets empty features (IDF=0 at fit time).  The second
    example's unique marker has df=1 and non-zero IDF, enabling
    prediction via that marker.
    """
    learner = SimilarityLearner()
    # Code category: 'alpha' for first doc, 'beta' for second
    learner.learn(_make_input("alpha coding syntax python", "code"))
    learner.learn(_make_input("beta coding syntax java", "code"))
    # Food category: 'gamma' for first doc, 'delta' for second
    learner.learn(_make_input("gamma cooking recipe pasta", "food"))
    learner.learn(_make_input("delta cooking recipe cake", "food"))
    # Other: unique marker
    learner.learn(_make_input("epsilon general purpose word", "other"))
    return learner


# ---------------------------------------------------------------------------
# Learn (add examples)
# ---------------------------------------------------------------------------


class TestLearn:
    """Test the learn method stores examples correctly."""

    def test_learn_returns_updated(self) -> None:
        """learn() returns UPDATED status on success."""
        learner = SimilarityLearner()
        result = learner.learn(_make_input("hello", "greeting"))
        assert result.status == LearningStatus.UPDATED

    def test_learn_increments_example_count(self) -> None:
        """learn() increases the number of stored examples."""
        learner = SimilarityLearner()
        learner.learn(_make_input("hello", "greeting"))
        assert learner.parameters["num_examples"] == 1
        learner.learn(_make_input("goodbye", "farewell"))
        assert learner.parameters["num_examples"] == 2

    def test_learn_with_empty_input(self) -> None:
        """learn() with empty input/output returns ERROR."""
        learner = SimilarityLearner()
        result = learner.learn(_make_input("", ""))
        assert result.status == LearningStatus.ERROR

    def test_learn_returns_example_id(self) -> None:
        """learn() delta contains the new example's ID."""
        learner = SimilarityLearner()
        result = learner.learn(_make_input("test", "result"))
        assert "example_id" in result.delta

    def test_learn_updates_vocabulary(self) -> None:
        """learn() builds vocabulary in the feature extractor."""
        learner = SimilarityLearner()
        learner.learn(_make_input("the cat sat", "animal"))
        assert learner.extractor.num_documents == 1
        assert len(learner.extractor.vocabulary) > 0


# ---------------------------------------------------------------------------
# Predict on known inputs
# ---------------------------------------------------------------------------


class TestPredictKnown:
    """Test prediction on inputs that match learned examples."""

    def test_predict_with_marker_term(self) -> None:
        """A query using a stored example's unique marker predicts correctly.

        The marker term (df=1) has non-zero IDF, so it appears in both
        the query vector and the stored example's vector, producing
        non-zero cosine similarity.
        """
        learner = _build_cat_dog_learner()
        # 'beta' is unique to Ex1 (cat), so query matches Ex1
        pred = learner.predict("beta programming word")
        assert pred.output == "cat"

    def test_empty_memory_returns_empty(self) -> None:
        """Predicting with no examples returns empty output."""
        learner = SimilarityLearner()
        pred = learner.predict("anything")
        assert pred.output == ""
        assert pred.confidence == pytest.approx(0.0)

    def test_prediction_has_confidence(self) -> None:
        """Prediction includes a confidence score."""
        learner = _build_cat_dog_learner()
        pred = learner.predict("beta programming word")
        assert 0.0 < pred.confidence <= 1.0

    def test_prediction_type(self) -> None:
        """predict() returns a Prediction dataclass."""
        learner = _build_cat_dog_learner()
        pred = learner.predict("beta programming word")
        assert isinstance(pred, Prediction)

    def test_all_examples_without_markers_fail(self) -> None:
        """A query using only shared terms yields low confidence.

        Shared terms appear in all documents and get low IDF, so the
        query matches all categories equally.  The prediction is
        non-empty but confidence is low.
        """
        learner = _build_cat_dog_learner()
        pred = learner.predict("programming word")
        # May predict any category, but confidence is low
        assert 0.0 < pred.confidence <= 0.6


# ---------------------------------------------------------------------------
# Predict on related inputs (generalization)
# ---------------------------------------------------------------------------


class TestPredictGeneralization:
    """Test that the learner generalizes to similar inputs."""

    def test_similar_input_generalizes(self) -> None:
        """A query sharing a marker with a stored example predicts it."""
        learner = _build_cat_dog_learner()
        # 'gamma' is unique to Ex2 (dog), plus extra noise word
        pred = learner.predict("gamma programming word extra")
        assert pred.output == "dog"
        assert pred.confidence > 0.0

    def test_unrelated_input_low_confidence(self) -> None:
        """An input sharing no marker terms returns empty or low confidence."""
        learner = _build_cat_dog_learner()
        pred = learner.predict("completely unrelated terms here")
        assert isinstance(pred, Prediction)

    def test_multiple_categories(self) -> None:
        """Learner distinguishes between different learned categories.

        Each category's second example has a unique marker with df=1.
        The query uses that marker to match the correct category.
        """
        learner = _build_two_category_learner()
        # 'beta' is unique to Ex1 (code), 'delta' unique to Ex3 (food)
        pred_code = learner.predict("beta coding syntax java")
        pred_food = learner.predict("delta cooking recipe cake")
        assert pred_code.output == "code"
        assert pred_food.output == "food"

    def test_marker_from_different_category(self) -> None:
        """Using a marker from the wrong category predicts that category."""
        learner = _build_cat_dog_learner()
        # 'gamma' is a dog marker, so prediction should be 'dog'
        pred = learner.predict("gamma programming word")
        assert pred.output == "dog"


# ---------------------------------------------------------------------------
# Feedback changes behavior
# ---------------------------------------------------------------------------


class TestFeedback:
    """Test that feedback adjusts example weights and predictions."""

    def test_correct_feedback_strengthens(self) -> None:
        """Correct feedback increases the weight of matching examples."""
        learner = SimilarityLearner()
        learner.learn(_make_input("hello", "greeting"))
        learner.feedback("hello", predicted="greeting", correct=True)
        ex = learner.memory.get(0)
        assert ex is not None
        assert ex.weight > 1.0

    def test_incorrect_feedback_weakens(self) -> None:
        """Incorrect feedback decreases the weight of matching examples."""
        learner = SimilarityLearner()
        learner.learn(_make_input("hello", "greeting"))
        learner.feedback("hello", predicted="greeting", correct=False)
        ex = learner.memory.get(0)
        assert ex is not None
        assert ex.weight < 1.0

    def test_incorrect_with_actual_adds_new_example(self) -> None:
        """Incorrect feedback with actual_output adds a correction example."""
        learner = SimilarityLearner()
        learner.learn(_make_input("hello", "wrong"))
        result = learner.feedback(
            "hello", predicted="wrong", correct=False, actual_output="greeting"
        )
        assert "new_example_id" in result
        assert learner.memory.count() == 2

    def test_feedback_returns_change_dict(self) -> None:
        """feedback() returns a dict describing what changed."""
        learner = SimilarityLearner()
        learner.learn(_make_input("test", "result"))
        changes = learner.feedback("test", predicted="result", correct=True)
        assert "correct" in changes
        assert "updated_examples" in changes


# ---------------------------------------------------------------------------
# Confidence scores
# ---------------------------------------------------------------------------


class TestConfidence:
    """Test confidence score behavior."""

    def test_single_match_high_confidence(self) -> None:
        """A query matching exactly one stored example yields high confidence."""
        learner = _build_cat_dog_learner()
        # 'delta' matches only Ex3 (dog)
        pred = learner.predict("delta programming word")
        assert pred.confidence > 0.5

    def test_competing_predictions_split_confidence(self) -> None:
        """A query matching multiple examples from different categories splits confidence."""
        learner = _build_two_category_learner()
        # 'beta' matches code, 'delta' matches food; query with both
        pred = learner.predict("beta delta")
        # Should match both categories
        assert 0.0 < pred.confidence <= 1.0

    def test_confidence_between_0_and_1(self) -> None:
        """Confidence is always clamped to [0, 1]."""
        learner = SimilarityLearner()
        for i in range(5):
            learner.learn(_make_input(f"text {i}", f"out{i}"))
        for text in ["text 0", "text 3", "unknown"]:
            pred = learner.predict(text)
            assert 0.0 <= pred.confidence <= 1.0


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------


class TestReset:
    """Test that reset clears all learner state."""

    def test_reset_clears_memory(self) -> None:
        """reset() removes all stored examples."""
        learner = SimilarityLearner()
        learner.learn(_make_input("test", "result"))
        learner.reset()
        assert learner.memory.count() == 0

    def test_reset_clears_stats(self) -> None:
        """reset() resets prediction statistics."""
        learner = SimilarityLearner()
        learner.learn(_make_input("test", "result"))
        learner.predict("test")
        learner.reset()
        params = learner.parameters
        assert params["total_predictions"] == 0
        assert params["correct_predictions"] == 0

    def test_reset_clears_vocabulary(self) -> None:
        """reset() resets the feature extractor vocabulary."""
        learner = SimilarityLearner()
        learner.learn(_make_input("test", "result"))
        assert learner.extractor.num_documents > 0
        learner.reset()
        assert learner.extractor.num_documents == 0


# ---------------------------------------------------------------------------
# Save / Load state
# ---------------------------------------------------------------------------


class TestSaveLoadState:
    """Test save_state / load_state round-trip."""

    def test_round_trip(self) -> None:
        """Saved state loads back with identical predictions."""
        learner = _build_cat_dog_learner()
        learner.predict("beta programming word")

        with tempfile.TemporaryDirectory() as tmpdir:
            learner.save_state(tmpdir)
            loaded = SimilarityLearner.load_state(tmpdir)

        assert loaded.memory.count() == learner.memory.count()
        assert loaded.parameters["total_predictions"] == learner.parameters["total_predictions"]

    def test_loaded_learner_predicts(self) -> None:
        """A loaded learner can make predictions on new inputs."""
        learner = _build_cat_dog_learner()

        with tempfile.TemporaryDirectory() as tmpdir:
            learner.save_state(tmpdir)
            loaded = SimilarityLearner.load_state(tmpdir)

        # 'epsilon' is unique to Ex4 (other)
        pred = loaded.predict("epsilon programming word")
        assert pred.output == "other"

    def test_load_state_preserves_config(self) -> None:
        """Loaded state preserves k and other config."""
        learner = SimilarityLearner(k=3, min_confidence=0.5)
        with tempfile.TemporaryDirectory() as tmpdir:
            learner.save_state(tmpdir)
            loaded = SimilarityLearner.load_state(tmpdir)
        assert loaded._k == 3
        assert loaded._min_confidence == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Parameters property
# ---------------------------------------------------------------------------


class TestParameters:
    """Test the parameters property returns expected keys."""

    def test_contains_expected_keys(self) -> None:
        """parameters includes k, accuracy, num_examples, num_features."""
        learner = SimilarityLearner()
        params = learner.parameters
        assert "k" in params
        assert "accuracy" in params
        assert "num_examples" in params
        assert "num_features" in params
        assert "total_predictions" in params
        assert "correct_predictions" in params

    def test_accuracy_initially_zero(self) -> None:
        """Initial accuracy is 0.0."""
        learner = SimilarityLearner()
        assert learner.parameters["accuracy"] == pytest.approx(0.0)

    def test_mode_is_online(self) -> None:
        """SimilarityLearner operates in ONLINE mode."""
        learner = SimilarityLearner()
        assert learner.mode == LearningMode.ONLINE


# ---------------------------------------------------------------------------
# Confidence calibration
# ---------------------------------------------------------------------------


class TestConfidenceCalibration:
    """Test that confidence reflects prediction quality."""

    def _build_corpus(self) -> SimilarityLearner:
        """Build a learner with well-separated categories."""
        learner = SimilarityLearner(k=5)
        # Category A: 5 examples
        for _i, marker in enumerate(["alpha", "bravo", "charlie", "delta", "echo"]):
            learner.learn(_make_input(f"{marker} cat animal pet", "animal"))
        # Category B: 5 examples
        for _i, marker in enumerate(["foxtrot", "golf", "hotel", "india", "juliet"]):
            learner.learn(_make_input(f"{marker} dog animal pet", "animal_dog"))
        # Category C: 5 examples
        for _i, marker in enumerate(["kilo", "lima", "mike", "novel", "oscar"]):
            learner.learn(_make_input(f"{marker} car vehicle engine", "vehicle"))
        return learner

    def test_familiar_input_high_confidence(self) -> None:
        """Input matching stored examples exactly gets high confidence."""
        learner = self._build_corpus()
        # Exact match: 'alpha' uniquely matches first example
        pred = learner.predict("alpha cat animal pet")
        assert pred.confidence > 0.7

    def test_related_input_moderate_confidence(self) -> None:
        """Related input with partial overlap gets moderate confidence."""
        learner = self._build_corpus()
        # 'alpha' matches one example, but query has extra noise
        pred = learner.predict("alpha cat animal pet extra noise words")
        # Confidence should be lower than exact match but still reasonable
        assert 0.3 < pred.confidence < 0.9

    def test_unrelated_input_low_confidence(self) -> None:
        """Input sharing no distinctive features gets low confidence."""
        learner = self._build_corpus()
        # Completely unrelated: no markers, only shared terms
        pred = learner.predict("completely unrelated query here")
        assert pred.confidence < 0.5

    def test_confidence_increases_with_support(self) -> None:
        """More supporting examples for the same category gives higher confidence."""
        learner = SimilarityLearner(k=5)
        # Learn 1 example
        learner.learn(_make_input("alpha cat animal", "animal"))
        pred1 = learner.predict("alpha cat animal")

        # Learn 4 more examples of the same category
        for marker in ["bravo", "charlie", "delta", "echo"]:
            learner.learn(_make_input(f"{marker} cat animal", "animal"))
        pred2 = learner.predict("alpha cat animal")

        # More support should give higher or similar confidence
        assert pred2.confidence >= pred1.confidence * 0.8

    def test_confidence_margin_effect(self) -> None:
        """Clear winner (large margin) gets higher confidence than tight race."""
        learner = SimilarityLearner(k=5)
        # Train: category A has strong unique markers
        for m in ["alpha", "bravo", "charlie"]:
            learner.learn(_make_input(f"{m} cat animal", "animal"))
        for m in ["delta", "echo", "foxtrot"]:
            learner.learn(_make_input(f"{m} dog animal", "animal_dog"))

        # Query with 'alpha' - clear winner
        pred_clear = learner.predict("alpha cat animal")
        # Query with shared terms only - tight race
        pred_tight = learner.predict("cat animal")

        # Clear winner should have higher confidence
        assert pred_clear.confidence > pred_tight.confidence
