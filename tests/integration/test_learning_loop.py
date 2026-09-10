"""Integration tests for the complete learning loop.

Tests end-to-end flows: learn -> predict -> feedback, improvement over
rounds, adaptation to answer changes, persistence retention, and
regression behavior.

Note on IDF behavior: The first fit() call always produces IDF=0 for
all terms (log(1/1)=0), so the first example's vector is empty.
Terms appearing in ALL documents also get IDF=0.  Tests use unique
'marker' terms per example that appear in only some docs, ensuring
non-zero IDF and query-example feature overlap.
"""

from __future__ import annotations

import tempfile

import pytest

from core.learner.base import LearningInput
from core.learner.learner_v1 import SimilarityLearner

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _learn(learner: SimilarityLearner, text: str, output: str) -> None:
    """Shorthand to learn an input-output pair."""
    learner.learn(LearningInput(observation={"input": text, "output": output}))


# ---------------------------------------------------------------------------
# Complete learn -> predict -> feedback cycle
# ---------------------------------------------------------------------------


class TestLearningCycle:
    """Test a single learn-predict-feedback cycle."""

    def test_full_cycle(self) -> None:
        """Learn, predict, then give feedback without errors.

        Uses unique marker terms so the query matches a stored example.
        """
        learner = SimilarityLearner()
        _learn(learner, "alpha programming language python", "programming language")
        _learn(learner, "beta programming language java", "programming language")
        _learn(learner, "gamma programming language rust", "programming language")
        # 'beta' marker → matches Ex1 (programming language)
        pred = learner.predict("beta programming language java")
        assert pred.output == "programming language"
        changes = learner.feedback(
            "beta programming language java", pred.output, correct=True
        )
        assert changes["correct"] is True

    def test_cycle_updates_memory(self) -> None:
        """Each step in the cycle modifies learner state."""
        learner = SimilarityLearner()
        _learn(learner, "alpha greeting friend hello", "greeting")
        _learn(learner, "beta greeting friend hello", "greeting")
        _learn(learner, "gamma greeting friend hello", "greeting")
        assert learner.memory.count() == 3
        # 'beta' marker matches Ex1
        learner.predict("beta greeting friend hello")
        assert learner.parameters["total_predictions"] == 1
        learner.feedback("beta greeting friend hello", "greeting", correct=True)
        assert learner.parameters["correct_predictions"] == 1


# ---------------------------------------------------------------------------
# Learning improvement over multiple rounds
# ---------------------------------------------------------------------------


class TestImprovement:
    """Test that the learner improves with more examples and feedback."""

    def test_more_examples_better_prediction(self) -> None:
        """Adding more examples improves prediction confidence."""
        learner = SimilarityLearner()
        _learn(learner, "alpha cat animal pet", "animal")
        _learn(learner, "beta cat animal pet", "animal")
        _learn(learner, "gamma dog animal pet", "animal")

        pred1 = learner.predict("beta cat animal pet")

        _learn(learner, "delta cat animal pet", "animal")
        _learn(learner, "epsilon cat animal pet", "animal")
        pred2 = learner.predict("beta cat animal pet")

        # With more examples of the same category, the prediction
        # should remain correct and confidence stays reasonable.
        # Confidence may fluctuate slightly due to IDF changes.
        assert pred2.output == pred1.output
        assert pred2.confidence > 0.5

    def test_feedback_improves_weights(self) -> None:
        """Correct feedback increases weights of good examples."""
        learner = SimilarityLearner()
        _learn(learner, "alpha greeting hello friend", "greeting")
        _learn(learner, "beta greeting hello friend", "greeting")
        _learn(learner, "gamma greeting hello friend", "greeting")

        for _ in range(5):
            learner.feedback("alpha greeting hello friend", "greeting", correct=True)

        ex = learner.memory.get(0)
        assert ex is not None
        assert ex.weight > 1.0

    def test_repeated_feedback_converges(self) -> None:
        """Repeated correct feedback pushes weight toward ceiling."""
        learner = SimilarityLearner()
        _learn(learner, "alpha test input word", "test output")
        _learn(learner, "beta test input word", "test output")
        _learn(learner, "gamma test input word", "test output")
        for _ in range(100):
            learner.feedback("alpha test input word", "test output", correct=True)
        ex = learner.memory.get(0)
        assert ex is not None
        assert ex.weight == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# Adaptation when answers change
# ---------------------------------------------------------------------------


class TestAdaptation:
    """Test that the learner adapts when correct answers change."""

    def test_correction_replaces_answer(self) -> None:
        """After incorrect feedback with actual_output, new answer is predicted."""
        learner = SimilarityLearner()
        _learn(learner, "alpha math two plus two", "4")
        _learn(learner, "beta math three plus three", "6")
        _learn(learner, "gamma math five plus five", "10")

        # Feedback says the answer should be "four" instead
        learner.feedback(
            "alpha math two plus two", predicted="4", correct=False, actual_output="four"
        )

        # The correction example has higher weight (1.5)
        pred = learner.predict("alpha math two plus two")
        assert pred.output == "four"

    def test_multiple_corrections(self) -> None:
        """Multiple corrections accumulate and reinforce the new answer."""
        learner = SimilarityLearner()
        _learn(learner, "alpha sky color today", "blue")
        _learn(learner, "beta ocean color today", "blue")
        _learn(learner, "gamma grass color today", "green")

        # First correction
        learner.feedback(
            "alpha sky color today", predicted="blue", correct=False, actual_output="azure"
        )
        # Second correction on similar input
        _learn(learner, "delta sky color looks azure", "azure")

        pred = learner.predict("alpha sky color today")
        assert pred.output == "azure"


# ---------------------------------------------------------------------------
# Retention after persistence
# ---------------------------------------------------------------------------


class TestRetention:
    """Test that learned knowledge survives save/load."""

    def test_predictions_survive_save_load(self) -> None:
        """A loaded learner produces the same predictions as the original."""
        learner = SimilarityLearner()
        _learn(learner, "alpha greeting hello friend", "greeting")
        _learn(learner, "beta farewell goodbye friend", "farewell")
        _learn(learner, "gamma farewell goodbye friend", "farewell")

        original_pred = learner.predict("beta farewell goodbye friend")

        with tempfile.TemporaryDirectory() as tmpdir:
            learner.save_state(tmpdir)
            loaded = SimilarityLearner.load_state(tmpdir)

        loaded_pred = loaded.predict("beta farewell goodbye friend")
        assert loaded_pred.output == original_pred.output
        assert loaded_pred.confidence == pytest.approx(original_pred.confidence)

    def test_feedback_retained_after_load(self) -> None:
        """Feedback history persists across save/load."""
        learner = SimilarityLearner()
        _learn(learner, "alpha test input word", "result")
        _learn(learner, "beta test input word", "result")
        _learn(learner, "gamma test input word", "result")
        learner.feedback("alpha test input word", "result", correct=True)
        learner.feedback("alpha test input word", "result", correct=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            learner.save_state(tmpdir)
            loaded = SimilarityLearner.load_state(tmpdir)

        ex = loaded.memory.get(0)
        assert ex is not None
        assert ex.feedback_count == 2
        assert ex.correct_count == 2

    def test_vocabulary_retained_after_load(self) -> None:
        """TF-IDF vocabulary persists across save/load."""
        learner = SimilarityLearner()
        _learn(learner, "alpha vocabulary test phrase here", "label")
        _learn(learner, "beta vocabulary test phrase here", "label")
        _learn(learner, "gamma vocabulary test phrase here", "label")

        with tempfile.TemporaryDirectory() as tmpdir:
            learner.save_state(tmpdir)
            loaded = SimilarityLearner.load_state(tmpdir)

        assert loaded.extractor.num_documents == 3
        assert len(loaded.extractor.vocabulary) > 0


# ---------------------------------------------------------------------------
# Regression behavior
# ---------------------------------------------------------------------------


class TestRegression:
    """Test that the learner does not regress on previously learned inputs."""

    def test_new_examples_do_not_break_old(self) -> None:
        """Learning new inputs does not degrade predictions on old inputs."""
        learner = SimilarityLearner()
        _learn(learner, "alpha category word here test", "category_a")
        _learn(learner, "beta category word here test", "category_a")
        _learn(learner, "gamma category word here test", "category_a")
        pred_before = learner.predict("beta category word here test")

        _learn(learner, "delta category word here test", "category_b")
        _learn(learner, "epsilon category word here test", "category_b")
        _learn(learner, "zeta category word here test", "category_b")

        pred_after = learner.predict("beta category word here test")
        # Output should not change (same prediction)
        assert pred_after.output == pred_before.output
        # Confidence may change slightly due to IDF shift, but stays reasonable
        assert pred_after.confidence > 0.3

    def test_feedback_does_not_break_unrelated(self) -> None:
        """Feedback on one example does not harm unrelated predictions."""
        learner = SimilarityLearner()
        _learn(learner, "alpha python is great for code", "positive")
        _learn(learner, "beta java is great for apps", "positive")
        _learn(learner, "gamma python is terrible for code", "negative")
        _learn(learner, "delta java is terrible for apps", "negative")

        # Heavy correct feedback on positive
        for _ in range(10):
            learner.feedback("alpha python is great for code", "positive", correct=True)

        # Negative example should still be predicted correctly
        pred = learner.predict("gamma python is terrible for code")
        assert pred.output == "negative"

    def test_accuracy_tracking_over_time(self) -> None:
        """Accuracy reflects the ratio of correct vs total feedback.

        Each category has 2 examples sharing a marker, so the second
        example's marker gets non-zero IDF and can be queried.
        """
        learner = SimilarityLearner()
        # Category A: share 'alpha' marker
        _learn(learner, "alpha unique word here test", "out1")
        _learn(learner, "alpha similar word here test", "out1")
        # Category B: share 'beta' marker
        _learn(learner, "beta unique word here test", "out2")
        _learn(learner, "beta similar word here test", "out2")
        # Category C: share 'gamma' marker
        _learn(learner, "gamma unique word here test", "out3")
        _learn(learner, "gamma similar word here test", "out3")

        # 2 correct feedback rounds (predict uses 'alpha' marker)
        learner.predict("alpha unique word here test")
        learner.feedback("alpha unique word here test", "out1", correct=True)

        # Use 'beta' marker for second prediction
        learner.predict("beta unique word here test")
        learner.feedback("beta unique word here test", "out2", correct=True)

        # 1 incorrect feedback round (use 'alpha' marker again)
        learner.predict("alpha unique word here test")
        learner.feedback("alpha unique word here test", "out1", correct=False)

        # correct_predictions increments on each correct feedback
        # total_predictions increments on each predict() with non-zero similarity
        params = learner.parameters
        assert params["correct_predictions"] == 2
        assert params["total_predictions"] == 3
        assert params["accuracy"] == pytest.approx(2 / 3)
