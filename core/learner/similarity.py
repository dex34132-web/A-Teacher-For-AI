"""Similarity computation between feature vectors.

Provides cosine similarity for sparse feature vectors.  IDF is applied
dynamically during comparison so that stored vectors remain consistent
as the vocabulary grows.
"""

from __future__ import annotations

from core.learner.feature_extractor import FeatureExtractor, FeatureVector


def cosine_similarity(
    a: FeatureVector,
    b: FeatureVector,
    extractor: FeatureExtractor | None = None,
) -> float:
    """Compute cosine similarity between two sparse feature vectors.

    If an ``extractor`` is provided, IDF weighting is applied to each
    shared feature before computing the dot product.  This means stored
    vectors (which contain raw TF) are compared using the *current*
    vocabulary's IDF, keeping comparisons consistent as the corpus grows.

    Formula (with IDF):
        weighted_sim = sum(a[t] * idf(t) * b[t] * idf(t)) /
                       (||a_weighted|| * ||b_weighted||)

    Args:
        a: First feature vector (raw TF).
        b: Second feature vector (raw TF).
        extractor: Optional extractor for IDF weighting.

    Returns:
        Cosine similarity score in [0, 1] for non-negative weights.
    """
    if not a.features or not b.features:
        return 0.0

    # Find shared features
    shared = set(a.features.keys()) & set(b.features.keys())
    if not shared:
        return 0.0

    # Compute weighted dot product
    dot_product = 0.0
    for term in shared:
        idf = extractor.weight_for(term) if extractor else 1.0
        dot_product += a.features[term] * idf * b.features[term] * idf

    # Compute weighted norms
    norm_a_sq = 0.0
    for term, tf in a.features.items():
        idf = extractor.weight_for(term) if extractor else 1.0
        norm_a_sq += (tf * idf) ** 2

    norm_b_sq = 0.0
    for term, tf in b.features.items():
        idf = extractor.weight_for(term) if extractor else 1.0
        norm_b_sq += (tf * idf) ** 2

    norm_a = float(norm_a_sq ** 0.5)
    norm_b = float(norm_b_sq ** 0.5)

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return float(dot_product / (norm_a * norm_b))


def weighted_similarity(
    query: FeatureVector,
    candidates: list[tuple[FeatureVector, float]],
    extractor: FeatureExtractor | None = None,
) -> list[tuple[int, float]]:
    """Compute similarity between a query and weighted candidates.

    Args:
        query: The query feature vector (raw TF).
        candidates: List of (feature_vector, weight) tuples.
        extractor: Optional extractor for IDF weighting.

    Returns:
        List of (index, weighted_score) tuples sorted by score descending.
    """
    scores: list[tuple[int, float]] = []

    for i, (vec, weight) in enumerate(candidates):
        sim = cosine_similarity(query, vec, extractor)
        weighted_score = sim * weight
        scores.append((i, weighted_score))

    scores.sort(key=lambda x: x[1], reverse=True)
    return scores
