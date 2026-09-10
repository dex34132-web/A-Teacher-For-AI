"""Learner V2 — Hybrid lexical + semantic similarity learner.

Extends V1 by combining TF-IDF similarity with dense semantic embeddings.
The key improvement: paraphrases and synonyms that share few lexical
features now get high similarity from the semantic component.

V2.1 adds optional retrieval scoring via RetrievalScorer:
    - Quality signal from success/failure history
    - Recency signal from usage timestamps
    - Diversity mechanism to avoid near-duplicate top-k results
    - Configurable via ScorerConfig (optional, defaults to V2.0 behavior)

V2.2 adds conflict detection and evidence-based resolution:
    - Detects when retrieved memories disagree about the output
    - Compares evidence (success rate, weight, recency) to resolve
    - Preserves conflicting knowledge (never auto-deletes)
    - Reduces confidence when conflicts cannot be resolved
    - Exposes conflict information via PredictResult

V2.3 adds principled confidence estimation:
    - Separates similarity from confidence
    - Bayesian evidence strength (smoothed success rate)
    - Agreement among supporting neighbors
    - Conflict-aware confidence reduction
    - Novelty detection for unseen situations
    - Structured uncertainty states
    - Explainable confidence components

Algorithm:
    1. Encode text with both TF-IDF (lexical) and semantic encoder
    2. Find k-NN using blended similarity:
       blended = lexical_weight * lexical_sim + semantic_weight * semantic_sim
    3. (V2.1) Apply quality/recency bonuses:
       retrieval_score = blended * (1 + q_weight * quality + r_weight * recency)
    4. (V2.1) Apply diversity to top-k results
    5. (V2.3) Estimate confidence from similarity, evidence, agreement, conflict
    6. (V2.2) Detect conflicts among top-k outputs
    7. (V2.2) Gather evidence and attempt resolution
    8. Feedback updates example weights and usage stats
    9. If semantic encoder unavailable, degrades to V1 behavior

Configuration:
    - lexical_weight: Weight for TF-IDF similarity (default: 0.4)
    - semantic_weight: Weight for semantic similarity (default: 0.6)
    - semantic_encoder: Pluggable SemanticEncoder instance (optional)
    - scorer_config: Optional ScorerConfig for V2.1 retrieval scoring
    - conflict_config: Optional ConflictConfig for V2.2 conflict detection
    - confidence_config: Optional ConfidenceConfig for V2.3 confidence estimation
    - All V1 parameters are inherited
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from core.learner.base import Learner, LearningInput, LearningMode, LearningOutput, LearningStatus
from core.learner.confidence import ConfidenceConfig, ConfidenceResult, estimate_confidence
from core.learner.calibration.estimator import estimate_confidence_v232
from core.learner.conflict import (
    Conflict,
    ConflictConfig,
    ConflictState,
    compare_evidence,
    detect_conflicts,
    gather_evidence,
)
from core.learner.feature_extractor import FeatureExtractor, FeatureVector
from core.learner.hybrid_memory import HybridExample, HybridMemory
from core.learner.learner_v1 import Prediction
from core.learner.lifecycle import LifecycleConfig, MemoryState
from core.learner.lifecycle_manager import LifecycleManager
from core.learner.predict_result import PredictResult
from core.learner.retrieval_scorer import (
    ScorerConfig,
    diversify_top_k,
    quality_score,
    recency_score,
    retrieval_score,
)
from core.learner.semantic_encoder import SemanticEncoder, dense_cosine_similarity
from core.learner.similarity import cosine_similarity

# ---------------------------------------------------------------------------
# V2 Learner
# ---------------------------------------------------------------------------


class HybridSimilarityLearner(Learner):
    """Hybrid learner combining lexical (TF-IDF) and semantic similarity.

    This learner wraps V1's TF-IDF approach and adds semantic embeddings.
    When a semantic encoder is provided, similarity is computed as:

        blended_sim = w_lex * tfidf_sim + w_sem * semantic_sim

    V2.1 adds optional retrieval scoring:

        retrieval_score = blended * (1 + q_weight * quality + r_weight * recency)

    When no semantic encoder is available, behavior is identical to V1.
    When no scorer_config is provided, behavior is identical to V2.0.

    The semantic encoder is pluggable — swap FastEmbedEncoder for
    sentence-transformers, API-based, or any custom implementation.
    """

    def __init__(
        self,
        k: int = 5,
        min_confidence: float = 0.1,
        feedback_weight_delta: float = 0.2,
        use_sublinear_tf: bool = False,
        ngram_range: tuple[int, int] = (1, 2),
        lexical_weight: float = 0.4,
        semantic_weight: float = 0.6,
        semantic_encoder: SemanticEncoder | None = None,
        scorer_config: ScorerConfig | None = None,
        conflict_config: ConflictConfig | None = None,
        confidence_config: ConfidenceConfig | None = None,
        lifecycle_config: LifecycleConfig | None = None,
    ) -> None:
        """Initialize the hybrid learner.

        Args:
            k: Number of nearest neighbors.
            min_confidence: Minimum confidence threshold.
            feedback_weight_delta: Weight adjustment per feedback.
            use_sublinear_tf: Use log-scaled TF.
            ngram_range: N-gram range for TF-IDF.
            lexical_weight: Weight for TF-IDF similarity in [0, 1].
            semantic_weight: Weight for semantic similarity in [0, 1].
            semantic_encoder: Pluggable encoder (None = V1 fallback).
            scorer_config: Optional V2.1 retrieval scoring config.
            conflict_config: Optional V2.2 conflict detection config.
            confidence_config: Optional V2.3 confidence estimation config.
            lifecycle_config: Optional V2.4 lifecycle management config.
        """
        self._k = k
        self._min_confidence = min_confidence
        self._feedback_weight_delta = feedback_weight_delta
        self._lexical_weight = lexical_weight
        self._semantic_weight = semantic_weight
        self._scorer_config = scorer_config
        self._conflict_config = conflict_config
        self._confidence_config = confidence_config
        self._lifecycle_config = lifecycle_config

        # Normalize weights
        total = lexical_weight + semantic_weight
        if total > 0:
            self._lexical_weight = lexical_weight / total
            self._semantic_weight = semantic_weight / total

        # Components
        self._extractor = FeatureExtractor(
            use_idf=True,
            sublinear_tf=use_sublinear_tf,
            ngram_range=ngram_range,
        )
        self._memory = HybridMemory()
        self._encoder = semantic_encoder

        # V2.4: Lifecycle manager (optional)
        self._lifecycle = LifecycleManager(config=self._lifecycle_config) if self._lifecycle_config is not None else None

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
            "lexical_weight": self._lexical_weight,
            "semantic_weight": self._semantic_weight,
            "has_semantic_encoder": self._encoder is not None,
            "semantic_dimension": self._encoder.dimension if self._encoder else None,
            "has_scorer": self._scorer_config is not None,
            "scorer_quality_weight": (
                self._scorer_config.quality_weight if self._scorer_config else 0.0
            ),
            "scorer_recency_weight": (
                self._scorer_config.recency_weight if self._scorer_config else 0.0
            ),
            "has_conflict_detection": self._conflict_config is not None,
            "has_confidence_estimation": self._confidence_config is not None,
            "has_lifecycle_management": self._lifecycle is not None,
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
    def memory(self) -> HybridMemory:
        """Access the underlying hybrid memory store."""
        return self._memory

    @property
    def extractor(self) -> FeatureExtractor:
        """Access the underlying feature extractor."""
        return self._extractor

    @property
    def encoder(self) -> SemanticEncoder | None:
        """Access the semantic encoder."""
        return self._encoder

    @property
    def has_semantic(self) -> bool:
        """Check if a semantic encoder is available."""
        return self._encoder is not None

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def learn(self, inp: LearningInput) -> LearningOutput:
        """Learn from a single experience.

        Stores both TF-IDF and semantic vectors when encoder is available.

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

        # Extract TF-IDF features
        vector = self._extractor.fit(input_text)

        # Compute semantic vector if encoder available
        semantic_vec: list[float] | None = None
        if self._encoder is not None:
            semantic_vec = self._encoder.encode_single(input_text)

        # Store in hybrid memory
        example = self._memory.add(
            input_text=input_text,
            output=output,
            vector=vector,
            metadata=inp.metadata,
            semantic_vector=semantic_vec,
        )

        return LearningOutput(
            status=LearningStatus.UPDATED,
            delta={
                "example_id": example.id,
                "num_examples": self._memory.count(),
                "num_features": len(self._extractor.vocabulary),
                "has_semantic": semantic_vec is not None,
            },
        )

    def predict(self, text: str) -> PredictResult:
        """Make a prediction using blended lexical+semantic similarity.

        V2.2: Returns PredictResult with conflict information.
        V2.3: Returns PredictResult with structured confidence estimation.
        V2.3.3: Abstains when confidence is below threshold.

        Args:
            text: The input text to predict.

        Returns:
            PredictResult with output, confidence, and conflict details.
        """
        # Get the base prediction with confidence result
        base_prediction, confidence_result = self._predict_with_confidence(text)
        if not base_prediction.output:
            self._total_predictions += 1
            return PredictResult(prediction=base_prediction)

        # Phase 10: Abstention — don't predict when confidence is too low
        abstained = False
        abstention_reason = ""
        if self._confidence_config is not None and confidence_result is not None:
            # Rule 1: Low confidence
            if confidence_result.confidence < self._confidence_config.abstention_threshold:
                abstained = True
                abstention_reason = (
                    f"confidence {confidence_result.confidence:.3f} < "
                    f"threshold {self._confidence_config.abstention_threshold}"
                )
            # Rule 2: Insufficient evidence with very low similarity
            elif (confidence_result.uncertainty_state == "insufficient_evidence"
                  and confidence_result.similarity < 0.3):
                abstained = True
                abstention_reason = (
                    f"insufficient evidence (sim={confidence_result.similarity:.3f})"
                )
            # Rule 3: Conflicted predictions
            elif confidence_result.uncertainty_state == "conflicted":
                abstained = True
                abstention_reason = (
                    f"conflicted ({confidence_result.conflict_count} distinct outputs)"
                )

        # If conflict detection is disabled, return without conflict info
        if self._conflict_config is None:
            self._total_predictions += 1
            return PredictResult(
                prediction=base_prediction,
                confidence_result=confidence_result,
                abstained=abstained,
                abstention_reason=abstention_reason,
            )

        # Detect conflicts among top-k
        conflicts = self._detect_and_resolve_conflicts(text, base_prediction)

        # Compute overall conflict state and confidence penalty
        overall_state = ConflictState.NONE
        max_penalty = 0.0
        selected_conflict: Conflict | None = None

        if conflicts:
            strongest = max(conflicts, key=lambda c: c.strength)
            selected_conflict = strongest
            max_penalty = max(c.confidence_penalty for c in conflicts)

            states = [c.state for c in conflicts]
            if ConflictState.UNRESOLVED in states:
                overall_state = ConflictState.UNRESOLVED
            elif ConflictState.CONFIRMED in states:
                overall_state = ConflictState.CONFIRMED
            elif ConflictState.POSSIBLE in states:
                overall_state = ConflictState.POSSIBLE

        self._total_predictions += 1

        return PredictResult(
            prediction=base_prediction,
            conflicts=conflicts,
            overall_conflict_state=overall_state,
            conflict_confidence_penalty=max_penalty,
            selected_conflict=selected_conflict,
            confidence_result=confidence_result,
            abstained=abstained,
            abstention_reason=abstention_reason,
        )

    def predict_legacy(self, text: str) -> Prediction:
        """Make a prediction returning the standard Prediction type.

        This is the same as predict() but returns only the base
        Prediction without conflict information. Use this for
        backward compatibility with code that expects Prediction.

        Args:
            text: The input text to predict.

        Returns:
            Prediction with output, confidence, and similar examples.
        """
        return self._predict_base(text)

    def _predict_base(self, text: str) -> Prediction:
        """Internal prediction returning the base Prediction.

        This contains the core prediction logic without conflict detection.
        Used by both predict() and predict_legacy().

        V2.3: Uses principled confidence estimation instead of V1 multi-factor.

        Args:
            text: The input text to predict.

        Returns:
            Prediction with output, confidence, and similar examples.
        """
        prediction, _confidence_result = self._predict_with_confidence(text)
        return prediction

    def _predict_with_confidence(
        self, text: str
    ) -> tuple[Prediction, ConfidenceResult | None]:
        """Internal prediction returning both Prediction and ConfidenceResult.

        V2.3: Returns the structured confidence result alongside the prediction.

        Args:
            text: The input text to predict.

        Returns:
            Tuple of (Prediction, ConfidenceResult or None).
        """
        # TF-IDF features
        query_vector = self._extractor.transform(text)
        if not query_vector.features:
            return Prediction(output="", confidence=0.0), None

        # Semantic vector
        query_semantic: list[float] | None = None
        if self._encoder is not None:
            query_semantic = self._encoder.encode_single(text)

        # Get all examples
        examples = self._memory.get_all_hybrid()
        if not examples:
            return Prediction(output="", confidence=0.0), None

        # Compute blended similarity scores
        scores = self._compute_blended_scores(
            query_vector, query_semantic, examples
        )

        # Apply V2.1 scoring if configured
        if self._scorer_config is not None:
            scores = self._apply_retrieval_scoring(scores, examples)

        # Take top k
        top_k = scores[: self._k]

        if not top_k or top_k[0][1] == 0:
            return Prediction(output="", confidence=0.0), None

        # Record usage on retrieved memories
        for idx, _score in top_k:
            self._memory.record_use(examples[idx].id)

        # Weighted voting
        votes: dict[str, float] = {}
        supporting_sims: dict[str, list[float]] = {}
        similarities: list[tuple[str, float]] = []

        for idx, weighted_score in top_k:
            example = examples[idx]
            blended = self._blended_similarity(
                query_vector, query_semantic, example
            )
            votes[example.output] = votes.get(example.output, 0.0) + weighted_score
            supporting_sims.setdefault(example.output, []).append(blended)
            similarities.append((example.input_text, blended))

        # Find winner
        if not votes:
            return Prediction(output="", confidence=0.0), None

        winner = max(votes, key=votes.get)  # type: ignore[arg-type]
        total_weight = sum(votes.values())
        winner_weight = votes[winner]
        n_support = len(supporting_sims.get(winner, []))
        total_count = len(top_k)

        # Get evidence from the best supporting memory
        best_sims = supporting_sims.get(winner, [])
        best_similarity = max(best_sims) if best_sims else 0.0

        best_success_count = 0
        best_failure_count = 0
        # Phase 9: Count independent memories (unique input+output pairs)
        independent_pairs: set[tuple[str, str]] = set()
        for idx, _score in top_k:
            example = examples[idx]
            if example.output == winner:
                # Track unique (input, output) pairs
                independent_pairs.add((example.input_text, example.output))
                total_evidence = example.success_count + example.failure_count
                best_total = best_success_count + best_failure_count
                if total_evidence > best_total or (
                    total_evidence == best_total
                    and example.success_count > best_success_count
                ):
                    best_success_count = example.success_count
                    best_failure_count = example.failure_count

        independent_evidence_count = len(independent_pairs)

            # V2.3: Estimate confidence
        confidence_result: ConfidenceResult | None = None
        if self._confidence_config is not None:
            # Build output_similarities from actual blended similarities (not weighted scores)
            # This ensures conflict detection uses true similarity to query, not retrieval weight
            all_blended_sims = []
            for idx, _score in top_k:
                example = examples[idx]
                blended = self._blended_similarity(
                    query_vector, query_semantic, example
                )
                all_blended_sims.append(blended)

            if self._confidence_config.use_v232:
                from core.learner.calibration.estimator import ConfidenceEstimatorConfig
                estimator_config = ConfidenceEstimatorConfig(
                    prior_strength=self._confidence_config.prior_strength,
                    agreement_weight=self._confidence_config.agreement_weight,
                    max_conflict_penalty=self._confidence_config.max_conflict_penalty,
                    min_evidence_samples=self._confidence_config.min_evidence_samples,
                    novelty_penalty_threshold=self._confidence_config.novelty_penalty_threshold,
                    novelty_penalty_strength=self._confidence_config.novelty_penalty_strength,
                    failure_dominance_penalty=self._confidence_config.failure_dominance_penalty,
                    agreement_boost_threshold=self._confidence_config.agreement_boost_threshold,
                    agreement_boost_weight=self._confidence_config.agreement_boost_weight,
                    conflict_relevance_threshold=self._confidence_config.conflict_relevance_threshold,
                    independence_bonus_weight=self._confidence_config.independence_bonus_weight,
                    max_independent_evidence=self._confidence_config.max_independent_evidence,
                )
                confidence_result = estimate_confidence_v232(
                    similarity=best_similarity,
                    success_count=best_success_count,
                    failure_count=best_failure_count,
                    supporting_weight=winner_weight,
                    total_weight=total_weight,
                    supporting_count=n_support,
                    total_count=total_count,
                    outputs=[examples[idx].output for idx, _ in top_k],
                    output_similarities=all_blended_sims,
                    independent_evidence_count=independent_evidence_count,
                    config=estimator_config,
                )
            else:
                confidence_result = estimate_confidence(
                    similarity=best_similarity,
                    success_count=best_success_count,
                    failure_count=best_failure_count,
                    supporting_weight=winner_weight,
                    total_weight=total_weight,
                    supporting_count=n_support,
                    total_count=total_count,
                    outputs=[examples[idx].output for idx, _ in top_k],
                    output_similarities=all_blended_sims,
                    config=self._confidence_config,
                )
            confidence = confidence_result.confidence
        else:
            # V1/V2.2 fallback: multi-factor confidence
            vote_share = winner_weight / total_weight if total_weight > 0 else 0.0
            sorted_votes = sorted(votes.values(), reverse=True)
            if len(sorted_votes) >= 2:
                margin = (sorted_votes[0] - sorted_votes[1]) / sorted_votes[0]
            else:
                margin = 1.0
            support_ratio = n_support / total_count if total_count else 0.0
            sims = supporting_sims.get(winner, [])
            avg_sim = sum(sims) / len(sims) if sims else 0.0
            confidence = (
                vote_share * 0.4
                + margin * 0.25
                + support_ratio * 0.2
                + avg_sim * 0.15
            )
            confidence = max(0.0, min(1.0, confidence))

        prediction = Prediction(
            output=winner,
            confidence=confidence,
            similarities=similarities,
        )
        return prediction, confidence_result

    def _detect_and_resolve_conflicts(
        self, text: str, base_prediction: Prediction
    ) -> list[Conflict]:
        """Detect and resolve conflicts among top-k retrieved memories.

        This is the V2.2 conflict detection pipeline:
        1. Re-retrieve top-k with their outputs
        2. Detect which outputs disagree
        3. Gather evidence for each side
        4. Compare evidence and resolve

        Args:
            text: The original query text.
            base_prediction: The base prediction (for early exit checks).

        Returns:
            List of resolved/unresolved conflicts (may be empty).
        """
        if self._conflict_config is None:
            return []

        # Re-retrieve to get the full candidate list with IDs
        query_vector = self._extractor.transform(text)
        if not query_vector.features:
            return []

        query_semantic: list[float] | None = None
        if self._encoder is not None:
            query_semantic = self._encoder.encode_single(text)

        examples = self._memory.get_all_hybrid()
        if not examples:
            return []

        scores = self._compute_blended_scores(query_vector, query_semantic, examples)
        if self._scorer_config is not None:
            scores = self._apply_retrieval_scoring(scores, examples)

        top_k = scores[: self._k]
        if not top_k:
            return []

        # Build candidate list: (example_id, relevance, output)
        examples_dict: dict[int, HybridExample] = {}
        for idx, _score in top_k:
            ex = examples[idx]
            examples_dict[ex.id] = ex

        candidates = [
            (examples[idx].id, score, examples[idx].output)
            for idx, score in top_k
            if score > 0.05  # Skip irrelevant candidates from conflict detection
        ]

        # Detect conflicts
        config = self._conflict_config
        conflicts = detect_conflicts(candidates, examples_dict, config)

        if not conflicts:
            return []

        # Compute recency scores for evidence gathering
        now = time.time()
        recency_scores: dict[int, float] = {}
        if self._scorer_config is not None:
            for idx, _score in top_k:
                ex = examples[idx]
                recency_scores[ex.id] = recency_score(
                    ex, now, self._scorer_config.recency_half_life
                )

        # Build relevance map
        query_relevance: dict[int, float] = {}
        for idx, score in top_k:
            query_relevance[examples[idx].id] = score

        # Gather evidence and resolve each conflict
        for conflict in conflicts:
            gather_evidence(conflict, examples_dict, query_relevance, recency_scores)
            compare_evidence(conflict, config)

        return conflicts

    def feedback(
        self,
        text: str,
        predicted: str,
        correct: bool,
        actual_output: str | None = None,
    ) -> dict[str, Any]:
        """Provide feedback on a prediction.

        V2.1: Also records success/failure on memories that contributed
        to the prediction, enabling quality-based retrieval scoring.

        Args:
            text: The original input text.
            predicted: What was predicted.
            correct: Whether the prediction was correct.
            actual_output: The correct output (if different).

        Returns:
            Dictionary describing what changed.
        """
        self._total_feedback += 1
        changes: dict[str, Any] = {"correct": correct}

        query_vector = self._extractor.transform(text)
        query_semantic: list[float] | None = None
        if self._encoder is not None:
            query_semantic = self._encoder.encode_single(text)

        examples = self._memory.get_all_hybrid()
        scores = self._compute_blended_scores(
            query_vector, query_semantic, examples
        )

        # Apply V2.1 scoring if configured (for consistent ranking)
        if self._scorer_config is not None:
            scores = self._apply_retrieval_scoring(scores, examples)

        updated_ids: list[int] = []
        for idx, _weighted_score in scores[: self._k]:
            example = examples[idx]
            if example.output == predicted:
                if correct:
                    self._memory.record_feedback(example.id, correct=True)
                    # V2.1: Record success for quality tracking
                    self._memory.record_success(example.id)
                    # V2.4: Lifecycle reinforcement on successful use
                    if self._lifecycle is not None:
                        self._lifecycle.reinforce(example)
                else:
                    self._memory.record_feedback(example.id, correct=False)
                    # V2.1: Record failure for quality tracking
                    self._memory.record_failure(example.id)
                updated_ids.append(example.id)

        changes["updated_examples"] = updated_ids

        # Add correction example if incorrect and no duplicate exists
        if not correct and actual_output:
            existing = [
                ex for ex in self._memory.get_all()
                if ex.input_text == text and ex.output == actual_output
            ]
            if not existing:
                vector = self._extractor.fit(text)
                semantic_vec: list[float] | None = None
                if self._encoder is not None:
                    semantic_vec = self._encoder.encode_single(text)
                new_example = self._memory.add(
                    input_text=text,
                    output=actual_output,
                    vector=vector,
                    weight=1.0,
                    semantic_vector=semantic_vec,
                )
                changes["new_example_id"] = new_example.id
                changes["num_examples"] = self._memory.count()

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
        self._memory = HybridMemory()
        self._total_predictions = 0
        self._correct_predictions = 0
        self._total_feedback = 0

    # ------------------------------------------------------------------
    # Similarity computation
    # ------------------------------------------------------------------

    def _blended_similarity(
        self,
        query_lexical: FeatureVector,
        query_semantic: list[float] | None,
        example: HybridExample,
    ) -> float:
        """Compute blended lexical+semantic similarity for one example.

        Args:
            query_lexical: TF-IDF vector of the query.
            query_semantic: Semantic vector of the query (or None).
            example: The example to compare against.

        Returns:
            Blended similarity in [0, 1].
        """
        # Lexical similarity (TF-IDF cosine)
        lex_sim = cosine_similarity(query_lexical, example.lexical_vector, self._extractor)

        # Semantic similarity (dense cosine)
        sem_sim = 0.0
        if (
            query_semantic is not None
            and example.semantic_vector is not None
            and self._encoder is not None
        ):
            sem_sim = dense_cosine_similarity(query_semantic, example.semantic_vector)

        return self._lexical_weight * lex_sim + self._semantic_weight * sem_sim

    def _compute_blended_scores(
        self,
        query_lexical: FeatureVector,
        query_semantic: list[float] | None,
        examples: list[HybridExample],
    ) -> list[tuple[int, float]]:
        """Compute blended similarity for all examples, sorted descending.

        Args:
            query_lexical: TF-IDF vector of the query.
            query_semantic: Semantic vector of the query.
            examples: All examples in memory.

        Returns:
            List of (index, blended_score) sorted by score descending.
        """
        scored: list[tuple[int, float]] = []
        for i, ex in enumerate(examples):
            blended = self._blended_similarity(query_lexical, query_semantic, ex)
            weighted = blended * ex.weight
            scored.append((i, weighted))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def _apply_retrieval_scoring(
        self,
        scores: list[tuple[int, float]],
        examples: list[HybridExample],
    ) -> list[tuple[int, float]]:
        """Apply V2.1 quality/recency scoring and diversity.

        Transforms raw similarity×weight scores into retrieval scores
        that consider memory quality and recency, then applies diversity
        to avoid near-duplicate results.

        Args:
            scores: List of (index, blended_score) from _compute_blended_scores.
            examples: All examples in memory.

        Returns:
            List of (index, retrieval_score) sorted by score descending.
        """
        if not scores or self._scorer_config is None:
            return scores

        config = self._scorer_config
        now = time.time()

        # Compute retrieval scores with quality and recency bonuses
        scored_with_quality: list[tuple[int, float]] = []
        for idx, blended_score in scores:
            example = examples[idx]
            # relevance is the blended_score divided by weight to get raw similarity
            # Actually, we use the blended_score directly as relevance since
            # it already incorporates similarity × weight
            q = quality_score(example)
            r = recency_score(example, now, config.recency_half_life)
            final = retrieval_score(
                blended_score, q, r,
                quality_weight=config.quality_weight,
                recency_weight=config.recency_weight,
            )
            scored_with_quality.append((idx, final))

        # Sort by retrieval score descending
        scored_with_quality.sort(key=lambda x: x[1], reverse=True)

        # Apply diversity if threshold < 1.0
        if config.diversity_threshold < 1.0 and len(scored_with_quality) > 1:
            # Build diversity input: need pairwise similarity for ranking
            diversity_input: list[tuple[int, float, float]] = []
            selected_for_diversity: list[int] = []

            for idx, score in scored_with_quality:
                # Compute max similarity to already-selected examples
                max_sim = 0.0
                for sel_idx in selected_for_diversity:
                    sim = self._pairwise_lexical_similarity(
                        examples[idx], examples[sel_idx]
                    )
                    if sim > max_sim:
                        max_sim = sim
                diversity_input.append((idx, score, max_sim))
                selected_for_diversity.append(idx)

            diversified = diversify_top_k(
                diversity_input,
                k=self._k,
                similarity_threshold=config.diversity_threshold,
            )
            return diversified

        return scored_with_quality

    def _pairwise_lexical_similarity(
        self, a: HybridExample, b: HybridExample
    ) -> float:
        """Compute lexical similarity between two stored examples.

        Uses TF-IDF cosine similarity with the current vocabulary.
        This is fast since vectors are already computed.

        Args:
            a: First example.
            b: Second example.

        Returns:
            Cosine similarity in [0, 1].
        """
        return cosine_similarity(a.lexical_vector, b.lexical_vector, self._extractor)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_state(self, path: str) -> None:
        """Save learner state including semantic encoder config, scorer, and conflict config.

        Args:
            path: Directory path to save to.
        """
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
                "lexical_weight": self._lexical_weight,
                "semantic_weight": self._semantic_weight,
            },
            "encoder": {
                "has_encoder": self._encoder is not None,
                "type": type(self._encoder).__name__ if self._encoder else None,
            },
            "scorer": {
                "has_scorer": self._scorer_config is not None,
                "quality_weight": (
                    self._scorer_config.quality_weight if self._scorer_config else 0.0
                ),
                "recency_weight": (
                    self._scorer_config.recency_weight if self._scorer_config else 0.0
                ),
                "recency_half_life": (
                    self._scorer_config.recency_half_life if self._scorer_config else 0.0
                ),
                "diversity_threshold": (
                    self._scorer_config.diversity_threshold if self._scorer_config else 1.0
                ),
            },
            "conflict": {
                "has_conflict_detection": self._conflict_config is not None,
                "input_similarity_threshold": (
                    self._conflict_config.input_similarity_threshold
                    if self._conflict_config else 0.75
                ),
                "output_equality_threshold": (
                    self._conflict_config.output_equality_threshold
                    if self._conflict_config else 0.0
                ),
                "evidence_margin": (
                    self._conflict_config.evidence_margin
                    if self._conflict_config else 0.1
                ),
                "context_similarity_threshold": (
                    self._conflict_config.context_similarity_threshold
                    if self._conflict_config else 0.9
                ),
                "min_evidence_samples": (
                    self._conflict_config.min_evidence_samples
                    if self._conflict_config else 3
                ),
            },
            "confidence": {
                "has_confidence_estimation": self._confidence_config is not None,
                "prior_strength": (
                    self._confidence_config.prior_strength
                    if self._confidence_config else 4.0
                ),
                "agreement_weight": (
                    self._confidence_config.agreement_weight
                    if self._confidence_config else 0.15
                ),
                "max_conflict_penalty": (
                    self._confidence_config.max_conflict_penalty
                    if self._confidence_config else 0.3
                ),
                "min_evidence_samples": (
                    self._confidence_config.min_evidence_samples
                    if self._confidence_config else 3
                ),
                "novelty_penalty_threshold": (
                    self._confidence_config.novelty_penalty_threshold
                    if self._confidence_config else 0.3
                ),
                "novelty_penalty_strength": (
                    self._confidence_config.novelty_penalty_strength
                    if self._confidence_config else 0.2
                ),
                "independence_bonus_weight": (
                    self._confidence_config.independence_bonus_weight
                    if self._confidence_config else 0.15
                ),
                "max_independent_evidence": (
                    self._confidence_config.max_independent_evidence
                    if self._confidence_config else 10
                ),
                "abstention_threshold": (
                    self._confidence_config.abstention_threshold
                    if self._confidence_config else 0.2
                ),
            },
        }

        save_path.mkdir(parents=True, exist_ok=True)
        (save_path / "extractor.json").write_text(
            json.dumps(state["extractor"], indent=2), encoding="utf-8"
        )
        (save_path / "stats.json").write_text(
            json.dumps(state["stats"], indent=2), encoding="utf-8"
        )
        (save_path / "config.json").write_text(
            json.dumps(state["config"], indent=2), encoding="utf-8"
        )
        (save_path / "encoder.json").write_text(
            json.dumps(state["encoder"], indent=2), encoding="utf-8"
        )
        (save_path / "scorer.json").write_text(
            json.dumps(state["scorer"], indent=2), encoding="utf-8"
        )
        (save_path / "conflict.json").write_text(
            json.dumps(state["conflict"], indent=2), encoding="utf-8"
        )
        (save_path / "confidence.json").write_text(
            json.dumps(state["confidence"], indent=2), encoding="utf-8"
        )

        # HybridMemory.save persists semantic vectors and V2.1 metadata
        self._memory.save(save_path / "memory.json")

        # V2.4: Save lifecycle state if present
        if self._lifecycle is not None:
            self._lifecycle.save(save_path)

    @classmethod
    def load_state(
        cls,
        path: str,
        semantic_encoder: SemanticEncoder | None = None,
        scorer_config: ScorerConfig | None = None,
        conflict_config: ConflictConfig | None = None,
        confidence_config: ConfidenceConfig | None = None,
    ) -> HybridSimilarityLearner:
        """Load learner state from a file.

        Args:
            path: Directory path to load from.
            semantic_encoder: Encoder to use (None = V1 fallback).
            scorer_config: Scorer config to use (None = V2.0 behavior).
            conflict_config: Conflict config to use (None = no conflict detection).
            confidence_config: Confidence config to use (None = V1 fallback).

        Returns:
            Restored HybridSimilarityLearner instance.
        """
        load_path = Path(path)

        config = json.loads((load_path / "config.json").read_text(encoding="utf-8"))

        # Load scorer config from file if available (backward compatible)
        scorer_file = load_path / "scorer.json"
        if scorer_file.exists() and scorer_config is None:
            scorer_data = json.loads(scorer_file.read_text(encoding="utf-8"))
            if scorer_data.get("has_scorer", False):
                scorer_config = ScorerConfig(
                    quality_weight=scorer_data.get("quality_weight", 0.1),
                    recency_weight=scorer_data.get("recency_weight", 0.05),
                    recency_half_life=scorer_data.get("recency_half_life", 86400.0),
                    diversity_threshold=scorer_data.get("diversity_threshold", 0.9),
                )

        # Load conflict config from file if available (backward compatible)
        conflict_file = load_path / "conflict.json"
        if conflict_file.exists() and conflict_config is None:
            conflict_data = json.loads(conflict_file.read_text(encoding="utf-8"))
            if conflict_data.get("has_conflict_detection", False):
                conflict_config = ConflictConfig(
                    input_similarity_threshold=conflict_data.get(
                        "input_similarity_threshold", 0.75
                    ),
                    output_equality_threshold=conflict_data.get(
                        "output_equality_threshold", 0.0
                    ),
                    evidence_margin=conflict_data.get("evidence_margin", 0.1),
                    context_similarity_threshold=conflict_data.get(
                        "context_similarity_threshold", 0.9
                    ),
                    min_evidence_samples=conflict_data.get(
                        "min_evidence_samples", 3
                    ),
                )

        # Load confidence config from file if available (backward compatible)
        confidence_file = load_path / "confidence.json"
        if confidence_file.exists() and confidence_config is None:
            confidence_data = json.loads(confidence_file.read_text(encoding="utf-8"))
            if confidence_data.get("has_confidence_estimation", False):
                confidence_config = ConfidenceConfig(
                    prior_strength=confidence_data.get("prior_strength", 4.0),
                    agreement_weight=confidence_data.get("agreement_weight", 0.15),
                    max_conflict_penalty=confidence_data.get(
                        "max_conflict_penalty", 0.3
                    ),
                    min_evidence_samples=confidence_data.get(
                        "min_evidence_samples", 3
                    ),
                    novelty_penalty_threshold=confidence_data.get(
                        "novelty_penalty_threshold", 0.3
                    ),
                    novelty_penalty_strength=confidence_data.get(
                        "novelty_penalty_strength", 0.2
                    ),
                    independence_bonus_weight=confidence_data.get(
                        "independence_bonus_weight", 0.15
                    ),
                    max_independent_evidence=confidence_data.get(
                        "max_independent_evidence", 10
                    ),
                    abstention_threshold=confidence_data.get(
                        "abstention_threshold", 0.2
                    ),
                )

        learner = cls(
            k=config["k"],
            min_confidence=config["min_confidence"],
            feedback_weight_delta=config.get("feedback_weight_delta", 0.2),
            lexical_weight=config.get("lexical_weight", 0.4),
            semantic_weight=config.get("semantic_weight", 0.6),
            semantic_encoder=semantic_encoder,
            scorer_config=scorer_config,
            conflict_config=conflict_config,
            confidence_config=confidence_config,
        )

        # V2.4: Load lifecycle state if present
        lifecycle_file = load_path / "lifecycle_config.json"
        if lifecycle_file.exists():
            lifecycle_manager = LifecycleManager.load(load_path)
            learner._lifecycle = lifecycle_manager
            learner._lifecycle_config = lifecycle_manager.config

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

        stats = json.loads((load_path / "stats.json").read_text(encoding="utf-8"))
        learner._total_predictions = stats["total_predictions"]
        learner._correct_predictions = stats["correct_predictions"]
        learner._total_feedback = stats.get("total_feedback", 0)

        # HybridMemory.load handles semantic vectors and V2.1 metadata
        learner._memory = HybridMemory.load(load_path / "memory.json")

        return learner
