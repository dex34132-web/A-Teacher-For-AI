"""Tests for similarity functions.

Covers cosine similarity with identical, orthogonal, and partially
overlapping vectors, plus weighted_similarity sorting.
"""

from __future__ import annotations

import pytest

from core.learner.feature_extractor import FeatureVector
from core.learner.similarity import cosine_similarity, weighted_similarity

# ---------------------------------------------------------------------------
# Cosine similarity
# ---------------------------------------------------------------------------


class TestCosineSimilarity:
    """Test cosine_similarity between feature vectors."""

    def test_identical_vectors(self) -> None:
        """Identical vectors have cosine similarity of 1.0."""
        vec = FeatureVector(features={"a": 1.0, "b": 2.0})
        assert cosine_similarity(vec, vec) == pytest.approx(1.0)

    def test_orthogonal_vectors(self) -> None:
        """Vectors with no shared features have cosine similarity of 0.0."""
        a = FeatureVector(features={"x": 1.0})
        b = FeatureVector(features={"y": 1.0})
        assert cosine_similarity(a, b) == pytest.approx(0.0)

    def test_partial_overlap(self) -> None:
        """Vectors sharing some features have similarity in (0, 1)."""
        a = FeatureVector(features={"a": 1.0, "b": 1.0})
        b = FeatureVector(features={"b": 1.0, "c": 1.0})
        sim = cosine_similarity(a, b)
        assert 0.0 < sim < 1.0

    def test_empty_vector_returns_zero(self) -> None:
        """An empty feature vector yields similarity 0.0."""
        empty = FeatureVector(features={})
        full = FeatureVector(features={"a": 1.0})
        assert cosine_similarity(empty, full) == pytest.approx(0.0)
        assert cosine_similarity(full, empty) == pytest.approx(0.0)

    def test_both_empty_returns_zero(self) -> None:
        """Two empty vectors yield similarity 0.0."""
        a = FeatureVector(features={})
        b = FeatureVector(features={})
        assert cosine_similarity(a, b) == pytest.approx(0.0)

    def test_scaled_vectors(self) -> None:
        """Scaling a vector does not change cosine similarity."""
        a = FeatureVector(features={"a": 1.0, "b": 2.0})
        b = FeatureVector(features={"a": 1.0, "b": 2.0})
        b_scaled = FeatureVector(features={"a": 3.0, "b": 6.0})
        assert cosine_similarity(a, b) == pytest.approx(cosine_similarity(a, b_scaled))

    def test_symmetric(self) -> None:
        """Cosine similarity is symmetric: sim(a,b) == sim(b,a)."""
        a = FeatureVector(features={"a": 1.0, "b": 3.0})
        b = FeatureVector(features={"b": 2.0, "c": 1.0})
        assert cosine_similarity(a, b) == pytest.approx(cosine_similarity(b, a))


# ---------------------------------------------------------------------------
# Weighted similarity
# ---------------------------------------------------------------------------


class TestWeightedSimilarity:
    """Test weighted_similarity scoring and sorting."""

    def test_sorted_descending(self) -> None:
        """Results are sorted by weighted score in descending order."""
        query = FeatureVector(features={"a": 1.0, "b": 1.0})
        candidates = [
            (FeatureVector(features={"x": 1.0}), 1.0),  # low sim
            (FeatureVector(features={"a": 1.0, "b": 1.0}), 1.0),  # high sim
        ]
        scores = weighted_similarity(query, candidates)
        assert scores[0][0] == 1  # index of highest-scoring candidate
        assert scores[1][0] == 0

    def test_weight_affects_score(self) -> None:
        """Higher candidate weight produces higher weighted score."""
        query = FeatureVector(features={"a": 1.0})
        high_weight = (FeatureVector(features={"a": 1.0}), 5.0)
        low_weight = (FeatureVector(features={"a": 1.0}), 1.0)
        scores = weighted_similarity(query, [low_weight, high_weight])
        assert scores[0][1] > scores[1][1]

    def test_empty_candidates(self) -> None:
        """No candidates returns an empty list."""
        query = FeatureVector(features={"a": 1.0})
        assert weighted_similarity(query, []) == []

    def test_returns_index_and_score(self) -> None:
        """Each result is a (index, score) tuple."""
        query = FeatureVector(features={"a": 1.0})
        candidates = [(FeatureVector(features={"a": 1.0}), 1.0)]
        scores = weighted_similarity(query, candidates)
        assert len(scores) == 1
        idx, score = scores[0]
        assert idx == 0
        assert score == pytest.approx(1.0)

    def test_zero_weight_yields_zero_score(self) -> None:
        """A candidate with weight 0 scores 0 regardless of similarity."""
        query = FeatureVector(features={"a": 1.0})
        candidates = [(FeatureVector(features={"a": 1.0}), 0.0)]
        scores = weighted_similarity(query, candidates)
        assert scores[0][1] == pytest.approx(0.0)
