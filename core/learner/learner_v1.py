"""Concrete learner implementation - Learner V1.

Implements an online similarity-based learning algorithm using TF-IDF
feature extraction and weighted nearest-neighbor prediction.

This is the first real learning algorithm for the AI Learning Engine.
It demonstrates:
- Feature extraction from text
- Similarity-based retrieval
- Weighted prediction with confidence
- Feedback-driven weight updates
- Incremental learning (one example at a time)
- Generalization to related inputs

Algorithm overview:
    1. Extract TF-IDF features from input text
    2. Find most similar examples in memory
    3. Weight predictions by similarity * example weight
    4. Return prediction with confidence score
    5. On feedback, adjust example weights
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.learner.base import Learner, LearningInput, LearningMode, LearningOutput, LearningStatus
from core.learner.feature_extractor import FeatureExtractor
from core.learner.memory import ExampleMemory
from core.learner.similarity import cosine_similarity, weighted_similarity

# ---------------------------------------------------------------------------
# Prediction result
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Prediction:
    """Result of a prediction.

    Attributes:
        output: The predicted output/label.
        confidence: Confidence score in [0, 1].
        similarities: Top similar examples used for prediction.
    """

    output: str
    confidence: float
    similarities: list[tuple[str, float]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Learner V1
# ---------------------------------------------------------------------------

class SimilarityLearner(Learner):
    """Online similarity-based learner.

    This learner stores input-output pairs as TF-IDF feature vectors.
    When predicting, it finds the most similar stored examples and
    uses weighted voting to produce a prediction.

    Learning happens through:
    1. Adding new examples to memory
    2. Adjusting example weights based on feedback
    3. Incrementally updating TF-IDF statistics

    The learner improves over time because:
    - More examples = better coverage of the input space
    - Feedback weights = more reliable examples are trusted more
    - TF-IDF = meaningful features that capture semantic similarity
    """

    def __init__(
        self,
        k: int = 5,
        min_confidence: float = 0.1,
        feedback_weight_delta: float = 0.2,
        use_sublinear_tf: bool = False,
        ngram_range: tuple[int, int] = (1, 2),
    ) -> None:
        """Initialize the learner.

        Args:
            k: Number of nearest neighbors to consider.
            min_confidence: Minimum confidence threshold for predictions.
            feedback_weight_delta: How much to adjust weights on feedback.
            use_sublinear_tf: Whether to use log-scaled TF.
            ngram_range: N-gram range for feature extraction.
        """
        self._k = k
        self._min_confidence = min_confidence
        self._feedback_weight_delta = feedback_weight_delta

        # Components
        self._extractor = FeatureExtractor(
            use_idf=True,
            sublinear_tf=use_sublinear_tf,
            ngram_range=ngram_range,
        )
        self._memory = ExampleMemory()

        # State
        self._total_predictions: int = 0
        self._correct_predictions: int = 0
        self._total_feedback: int = 0

    @property
    def mode(self) -> LearningMode:
        """Return operating mode."""
        return LearningMode.ONLINE

    @property
    def parameters(self) -> dict[str, Any]:
        """Return serializable parameters."""
        return {
            "k": self._k,
            "min_confidence": self._min_confidence,
            "feedback_weight_delta": self._feedback_weight_delta,
            "total_predictions": self._total_predictions,
            "correct_predictions": self._correct_predictions,
            "accuracy": (
                self._correct_predictions / self._total_predictions
                if self._total_predictions > 0
                else 0.0
            ),
            "num_examples": self._memory.count(),
            "num_features": len(self._extractor.vocabulary),
        }

    @property
    def memory(self) -> ExampleMemory:
        """Access the underlying memory store."""
        return self._memory

    @property
    def extractor(self) -> FeatureExtractor:
        """Access the underlying feature extractor."""
        return self._extractor

    def learn(self, inp: LearningInput) -> LearningOutput:
        """Learn from a single experience.

        The input observation should contain:
            - "input": The input text
            - "output": The expected output/label

        Args:
            inp: The learning input.

        Returns:
            Learning output describing what changed.
        """
        input_text = inp.observation.get("input", "")
        output = inp.observation.get("output", "")

        if not input_text or not output:
            return LearningOutput(
                status=LearningStatus.ERROR,
                diagnostics={"error": "Missing input or output"},
            )

        # Extract features and update vocabulary
        vector = self._extractor.fit(input_text)

        # Store in memory
        example = self._memory.add(
            input_text=input_text,
            output=output,
            vector=vector,
            metadata=inp.metadata,
        )

        return LearningOutput(
            status=LearningStatus.UPDATED,
            delta={
                "example_id": example.id,
                "num_examples": self._memory.count(),
                "num_features": len(self._extractor.vocabulary),
            },
        )

    def predict(self, text: str) -> Prediction:
        """Make a prediction for a new input.

        Finds the k most similar stored examples and uses weighted
        voting to produce a prediction with confidence score.

        Confidence is computed from multiple factors:
        1. Vote share: fraction of total weight going to the winner
        2. Margin: difference between winner and runner-up votes
        3. Support: number of distinct examples supporting the winner
        4. Average similarity of supporting examples

        Args:
            text: The input text to predict.

        Returns:
            Prediction with output, confidence, and similar examples.
        """
        # Extract features without updating vocabulary
        query_vector = self._extractor.transform(text)

        if not query_vector.features:
            return Prediction(output="", confidence=0.0)

        # Get all examples
        examples = self._memory.get_all()
        if not examples:
            return Prediction(output="", confidence=0.0)

        # Compute similarities (IDF applied dynamically)
        candidates = [(ex.vector, ex.weight) for ex in examples]
        scores = weighted_similarity(query_vector, candidates, self._extractor)

        # Take top k
        top_k = scores[: self._k]

        if not top_k or top_k[0][1] == 0:
            return Prediction(output="", confidence=0.0)

        # Weighted voting
        votes: dict[str, float] = {}
        supporting_sims: dict[str, list[float]] = {}
        similarities: list[tuple[str, float]] = []

        for idx, weighted_score in top_k:
            example = examples[idx]
            sim = cosine_similarity(query_vector, example.vector, self._extractor)
            votes[example.output] = votes.get(example.output, 0.0) + weighted_score
            supporting_sims.setdefault(example.output, []).append(sim)
            similarities.append((example.input_text, sim))

        # Find winner
        if not votes:
            return Prediction(output="", confidence=0.0)

        winner = max(votes, key=votes.get)  # type: ignore[arg-type]
        total_weight = sum(votes.values())

        # Factor 1: Vote share (0..1)
        vote_share = votes[winner] / total_weight if total_weight > 0 else 0.0

        # Factor 2: Margin between winner and runner-up
        sorted_votes = sorted(votes.values(), reverse=True)
        if len(sorted_votes) >= 2:
            margin = (sorted_votes[0] - sorted_votes[1]) / sorted_votes[0]
        else:
            margin = 1.0  # Only one category

        # Factor 3: Support count (fraction of top-k supporting winner)
        n_support = len(supporting_sims.get(winner, []))
        support_ratio = n_support / len(top_k) if top_k else 0.0

        # Factor 4: Average similarity of supporting examples
        sims = supporting_sims.get(winner, [])
        avg_sim = sum(sims) / len(sims) if sims else 0.0

        # Combine factors: geometric-mean-like combination
        # All factors in [0, 1]; result is in [0, 1]
        confidence = (
            vote_share * 0.4
            + margin * 0.25
            + support_ratio * 0.2
            + avg_sim * 0.15
        )

        # Clamp
        confidence = max(0.0, min(1.0, confidence))

        self._total_predictions += 1

        return Prediction(
            output=winner,
            confidence=confidence,
            similarities=similarities,
        )

    def feedback(
        self,
        text: str,
        predicted: str,
        correct: bool,
        actual_output: str | None = None,
    ) -> dict[str, Any]:
        """Provide feedback on a prediction.

        This is where actual learning happens. When feedback is received:
        - If correct: Increase the weight of similar examples
        - If incorrect: Decrease weights, optionally add new example

        Args:
            text: The original input text.
            predicted: What was predicted.
            correct: Whether the prediction was correct.
            actual_output: The correct output (if different from predicted).

        Returns:
            Dictionary describing what changed.
        """
        self._total_feedback += 1
        changes: dict[str, Any] = {"correct": correct}

        # Extract features for the input
        query_vector = self._extractor.transform(text)

        # Find similar examples
        examples = self._memory.get_all()
        candidates = [(ex.vector, ex.weight) for ex in examples]
        scores = weighted_similarity(query_vector, candidates, self._extractor)

        # Update weights of similar examples
        updated_ids: list[int] = []
        for idx, _weighted_score in scores[: self._k]:
            example = examples[idx]
            if example.output == predicted:
                if correct:
                    self._memory.record_feedback(example.id, correct=True)
                else:
                    self._memory.record_feedback(example.id, correct=False)
                updated_ids.append(example.id)

        changes["updated_examples"] = updated_ids

        # If incorrect and we have the actual output, add it as a new example
        # but only if we don't already have a correction for this input
        if not correct and actual_output:
            # Check if a correction example already exists for this input
            existing = [
                ex for ex in self._memory.get_all()
                if ex.input_text == text and ex.output == actual_output
            ]
            if not existing:
                vector = self._extractor.fit(text)
                new_example = self._memory.add(
                    input_text=text,
                    output=actual_output,
                    vector=vector,
                    weight=1.0,
                )
                changes["new_example_id"] = new_example.id
                changes["num_examples"] = self._memory.count()

        # Track accuracy
        if correct:
            self._correct_predictions += 1

        return changes

    def reset(self) -> None:
        """Reset the learner to initial state."""
        self._extractor = FeatureExtractor(
            use_idf=self._extractor.use_idf,
            sublinear_tf=self._extractor.sublinear_tf,
            ngram_range=self._extractor.ngram_range,
        )
        self._memory = ExampleMemory()
        self._total_predictions = 0
        self._correct_predictions = 0
        self._total_feedback = 0

    def save_state(self, path: str) -> None:
        """Save learner state to a file.

        Args:
            path: File path to save to.
        """
        import json
        from pathlib import Path

        save_path = Path(path)
        state = {
            "extractor": {
                "params": self._extractor.get_params(),
                "df": self._extractor.vocabulary,
                "num_docs": self._extractor.num_documents,
            },
            "stats": {
                "total_predictions": self._total_predictions,
                "correct_predictions": self._correct_predictions,
                "total_feedback": self._total_feedback,
            },
            "config": {
                "k": self._k,
                "min_confidence": self._min_confidence,
                "feedback_weight_delta": self._feedback_weight_delta,
            },
        }

        # Save extractor state
        save_path.parent.mkdir(parents=True, exist_ok=True)
        (save_path / "extractor.json").write_text(
            json.dumps(state["extractor"], indent=2), encoding="utf-8"
        )
        (save_path / "stats.json").write_text(
            json.dumps(state["stats"], indent=2), encoding="utf-8"
        )
        (save_path / "config.json").write_text(
            json.dumps(state["config"], indent=2), encoding="utf-8"
        )

        # Save memory
        self._memory.save(save_path / "memory.json")

    @classmethod
    def load_state(cls, path: str) -> SimilarityLearner:
        """Load learner state from a file.

        Args:
            path: Directory path to load from.

        Returns:
            Restored SimilarityLearner instance.
        """
        import json
        from pathlib import Path

        load_path = Path(path)

        # Load config
        config = json.loads((load_path / "config.json").read_text(encoding="utf-8"))

        # Create learner with saved config
        learner = cls(
            k=config["k"],
            min_confidence=config["min_confidence"],
            feedback_weight_delta=config.get("feedback_weight_delta", 0.2),
        )

        # Load extractor state
        extractor_data = json.loads(
            (load_path / "extractor.json").read_text(encoding="utf-8")
        )
        params = extractor_data["params"]
        learner._extractor = FeatureExtractor(
            use_idf=params["use_idf"],
            sublinear_tf=params["sublinear_tf"],
            ngram_range=tuple(params["ngram_range"]),
            min_df=params.get("min_df", 1),
        )
        learner._extractor.set_params(
            df=extractor_data["df"],
            num_docs=extractor_data["num_docs"],
        )

        # Load stats
        stats = json.loads((load_path / "stats.json").read_text(encoding="utf-8"))
        learner._total_predictions = stats["total_predictions"]
        learner._correct_predictions = stats["correct_predictions"]
        learner._total_feedback = stats.get("total_feedback", 0)

        # Load memory
        learner._memory = ExampleMemory.load(load_path / "memory.json")

        return learner
