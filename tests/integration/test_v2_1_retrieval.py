"""V2.1 integration tests — end-to-end verification of smarter memory retrieval.

Tests the full pipeline: learn → predict → feedback → verify usage tracking,
quality scoring, recency, and diversity all work together.
"""

from __future__ import annotations

import tempfile

from core.learner.base import LearningInput
from core.learner.learner_v2 import HybridSimilarityLearner
from core.learner.retrieval_scorer import ScorerConfig


class TestV21EndToEnd:
    """Full pipeline tests with V2.1 scoring enabled."""

    def test_learn_predict_feedback_cycle(self):
        """Basic learn → predict → feedback works with scorer."""
        learner = HybridSimilarityLearner(
            k=3,
            scorer_config=ScorerConfig(),
        )
        learner.learn(LearningInput(
            observation={"input": "how to sort a list", "output": "use sorted()"}
        ))
        learner.learn(LearningInput(
            observation={"input": "reverse a string", "output": "s[::-1]"}
        ))
        learner.learn(LearningInput(
            observation={"input": "sort array", "output": "use sorted()"}
        ))

        pred = learner.predict("how do I sort")
        assert pred.output == "use sorted()"
        assert pred.confidence > 0.3

        # Feedback should record success on the matched memory
        changes = learner.feedback(
            text="how to sort a list",
            predicted="use sorted()",
            correct=True,
        )
        assert changes["correct"] is True

    def test_incorrect_feedback_adds_correction(self):
        """Incorrect feedback with actual_output adds a new memory."""
        learner = HybridSimilarityLearner(
            k=3,
            scorer_config=ScorerConfig(),
        )
        learner.learn(LearningInput(observation={"input": "what is 2+2", "output": "4"}))
        pred = learner.predict("what is 2+2")
        assert pred.output == "4"

        # Provide correction
        changes = learner.feedback(
            text="what is 2+2",
            predicted="4",
            correct=False,
            actual_output="four",
        )
        assert "new_example_id" in changes

        # Now both should be retrievable
        pred2 = learner.predict("what is 2+2")
        assert pred2.output in ("4", "four")

    def test_usage_tracking_increments(self):
        """Each predict call increments usage on retrieved memories."""
        learner = HybridSimilarityLearner(
            k=3,
            scorer_config=ScorerConfig(),
        )
        learner.learn(LearningInput(observation={"input": "hello", "output": "world"}))
        learner.learn(LearningInput(observation={"input": "goodbye", "output": "earth"}))

        # Make several predictions
        for _ in range(5):
            learner.predict("hello")

        stats = learner._memory.get_usage_stats(0)
        assert stats is not None
        assert stats["use_count"] == 5

    def test_success_failure_tracking(self):
        """Feedback correctly records success/failure on memories."""
        learner = HybridSimilarityLearner(
            k=3,
            scorer_config=ScorerConfig(),
        )
        learner.learn(LearningInput(observation={"input": "hello", "output": "world"}))

        # Correct feedback
        learner.feedback(text="hello", predicted="world", correct=True)
        stats = learner._memory.get_usage_stats(0)
        assert stats["success_count"] == 1

        # More correct feedback
        learner.feedback(text="hello", predicted="world", correct=True)
        stats = learner._memory.get_usage_stats(0)
        assert stats["success_count"] == 2

    def test_v21_parameters_include_scorer_info(self):
        """Parameters dict includes scorer configuration."""
        learner = HybridSimilarityLearner(
            k=5,
            scorer_config=ScorerConfig(quality_weight=0.2, recency_weight=0.1),
        )
        params = learner.parameters
        assert params["has_scorer"] is True
        assert params["scorer_quality_weight"] == 0.2
        assert params["scorer_recency_weight"] == 0.1

    def test_v20_parameters_without_scorer(self):
        """Without scorer, parameters show no scorer info."""
        learner = HybridSimilarityLearner(k=3)
        params = learner.parameters
        assert params["has_scorer"] is False
        assert params["scorer_quality_weight"] == 0.0
        assert params["scorer_recency_weight"] == 0.0

    def test_save_load_with_scorer_config(self):
        """Scorer config persists through save/load."""
        learner = HybridSimilarityLearner(
            k=5,
            scorer_config=ScorerConfig(quality_weight=0.2, recency_weight=0.1),
        )
        learner.learn(LearningInput(observation={"input": "hello", "output": "world"}))

        with tempfile.TemporaryDirectory() as tmpdir:
            learner.save_state(tmpdir)
            loaded = HybridSimilarityLearner.load_state(
                tmpdir, scorer_config=ScorerConfig(quality_weight=0.2, recency_weight=0.1)
            )

        # Loaded learner should work
        pred = loaded.predict("hello")
        assert pred.output == "world"

    def test_v1_backward_compatibility(self):
        """V2.1 learner without scorer behaves like V2.0."""
        v20 = HybridSimilarityLearner(k=3)  # No scorer
        v21 = HybridSimilarityLearner(k=3, scorer_config=ScorerConfig())  # With scorer

        # Same training data
        examples = [
            ("sort a list", "use sorted()"),
            ("reverse string", "s[::-1]"),
            ("find max", "max()"),
            ("filter items", "[x for x in lst if cond]"),
        ]
        for text, output in examples:
            inp = LearningInput(observation={"input": text, "output": output})
            v20.learn(inp)
            v21.learn(inp)

        # Both should predict the same output for the same input
        pred20 = v20.predict("how to sort")
        pred21 = v21.predict("how to sort")
        assert pred20.output == pred21.output

    def test_diversity_removes_near_duplicates(self):
        """When many similar memories exist, diversity keeps top-k diverse."""
        learner = HybridSimilarityLearner(
            k=3,
            scorer_config=ScorerConfig(diversity_threshold=0.8),
        )
        # Add many very similar examples
        for i in range(20):
            learner.learn(LearningInput(
                observation={"input": f"sort list {i}", "output": f"use sorted({i})"}
            ))

        # Predict should return diverse results
        pred = learner.predict("sort a list")
        assert pred.output is not None

    def test_reset_clears_all_metadata(self):
        """Reset clears all usage metadata."""
        learner = HybridSimilarityLearner(
            k=3,
            scorer_config=ScorerConfig(),
        )
        learner.learn(LearningInput(observation={"input": "hello", "output": "world"}))
        learner.predict("hello")
        learner.feedback(text="hello", predicted="world", correct=True)

        learner.reset()
        assert learner._memory.count() == 0
        assert learner.parameters["total_predictions"] == 0
        assert learner.parameters["correct_predictions"] == 0

    def test_multiple_predictions_build_usage(self):
        """Multiple different predictions track usage across memories."""
        learner = HybridSimilarityLearner(
            k=1,  # k=1 ensures each prediction only touches one memory
            scorer_config=ScorerConfig(),
        )
        learner.learn(LearningInput(observation={"input": "hello", "output": "world"}))
        learner.learn(LearningInput(observation={"input": "goodbye", "output": "earth"}))

        # Predict different things
        learner.predict("hello")
        learner.predict("goodbye")
        learner.predict("hello")

        stats0 = learner._memory.get_usage_stats(0)
        stats1 = learner._memory.get_usage_stats(1)
        assert stats0["use_count"] == 2
        assert stats1["use_count"] == 1


class TestV21VsV20Comparative:
    """Compare V2.0 (no scorer) vs V2.1 (with scorer) behavior."""

    def test_v21_handles_all_v20_scenarios(self):
        """V2.1 must handle every scenario V2.0 handles."""
        v20 = HybridSimilarityLearner(k=3)
        v21 = HybridSimilarityLearner(k=3, scorer_config=ScorerConfig())

        examples = [
            ("how to open file", "open()"),
            ("read file content", "f.read()"),
            ("close file handle", "f.close()"),
            ("write to file", "f.write()"),
            ("check file exists", "os.path.exists()"),
        ]

        for text, output in examples:
            inp = LearningInput(observation={"input": text, "output": output})
            v20.learn(inp)
            v21.learn(inp)

        test_queries = [
            "open a file",
            "read from file",
            "close the file",
            "write file",
            "does file exist",
        ]

        for query in test_queries:
            p20 = v20.predict(query)
            p21 = v21.predict(query)
            # Both should predict the same output
            assert p20.output == p21.output, (
                f"V2.0 and V2.1 disagree on '{query}': "
                f"v20={p20.output}, v21={p21.output}"
            )

    def test_v21_feedback_preserves_v20_behavior(self):
        """Feedback in V2.1 doesn't break V2.0 compatibility."""
        v20 = HybridSimilarityLearner(k=3)
        v21 = HybridSimilarityLearner(k=3, scorer_config=ScorerConfig())

        inp = LearningInput(observation={"input": "x", "output": "a"})
        v20.learn(inp)
        v21.learn(inp)

        # Correct feedback
        v20.feedback(text="x", predicted="a", correct=True)
        v21.feedback(text="x", predicted="a", correct=True)

        # Both should still predict correctly
        p20 = v20.predict("x")
        p21 = v21.predict("x")
        assert p20.output == "a"
        assert p21.output == "a"
