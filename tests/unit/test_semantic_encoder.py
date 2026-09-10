"""Tests for SemanticEncoder interface and FastEmbed implementation.

Tests the abstract interface, cosine similarity function, and the
concrete FastEmbedEncoder. FastEmbed tests are skipped if fastembed
is not installed.
"""

from __future__ import annotations

import math

import pytest

from core.learner.semantic_encoder import SemanticEncoder, dense_cosine_similarity

# ---------------------------------------------------------------------------
# Concrete test encoder for interface testing
# ---------------------------------------------------------------------------


class StubEncoder(SemanticEncoder):
    """Minimal encoder for testing the interface."""

    def __init__(self, dim: int = 4) -> None:
        self._dim = dim

    def encode(self, texts: list[str]) -> list[list[float]]:
        results = []
        for text in texts:
            results.append([float(len(text))] * self._dim)
        return results

    def encode_single(self, text: str) -> list[float]:
        return [float(len(text))] * self._dim

    @property
    def dimension(self) -> int:
        return self._dim


# ---------------------------------------------------------------------------
# SemanticEncoder interface tests
# ---------------------------------------------------------------------------


class TestSemanticEncoderInterface:
    """Test the SemanticEncoder abstract interface."""

    def test_implements_interface(self):
        encoder = StubEncoder()
        assert isinstance(encoder, SemanticEncoder)

    def test_encode_returns_list_of_lists(self):
        encoder = StubEncoder(dim=3)
        result = encoder.encode(["hello", "world"])
        assert len(result) == 2
        assert len(result[0]) == 3
        assert len(result[1]) == 3

    def test_encode_single_returns_list(self):
        encoder = StubEncoder(dim=3)
        result = encoder.encode_single("hello")
        assert isinstance(result, list)
        assert len(result) == 3

    def test_dimension_property(self):
        encoder = StubEncoder(dim=7)
        assert encoder.dimension == 7

    def test_encode_empty_list(self):
        encoder = StubEncoder()
        result = encoder.encode([])
        assert result == []

    def test_encode_preserves_count(self):
        encoder = StubEncoder(dim=2)
        texts = ["a", "bb", "ccc", "dddd"]
        result = encoder.encode(texts)
        assert len(result) == len(texts)


# ---------------------------------------------------------------------------
# dense_cosine_similarity tests
# ---------------------------------------------------------------------------


class TestDenseCosineSimilarity:
    """Test the dense cosine similarity function."""

    def test_identical_vectors(self):
        a = [1.0, 2.0, 3.0]
        assert dense_cosine_similarity(a, a) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert dense_cosine_similarity(a, b) == pytest.approx(0.0)

    def test_opposite_vectors(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert dense_cosine_similarity(a, b) == pytest.approx(-1.0)

    def test_known_value(self):
        a = [1.0, 1.0]
        b = [1.0, 0.0]
        expected = 1.0 / math.sqrt(2)
        assert dense_cosine_similarity(a, b) == pytest.approx(expected)

    def test_zero_vector(self):
        a = [0.0, 0.0]
        b = [1.0, 1.0]
        assert dense_cosine_similarity(a, b) == 0.0

    def test_both_zero_vectors(self):
        a = [0.0, 0.0]
        b = [0.0, 0.0]
        assert dense_cosine_similarity(a, b) == 0.0

    def test_dimension_mismatch_raises(self):
        a = [1.0, 2.0]
        b = [1.0, 2.0, 3.0]
        with pytest.raises(ValueError, match="dimensions mismatch"):
            dense_cosine_similarity(a, b)

    def test_unit_vectors(self):
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        assert dense_cosine_similarity(a, b) == pytest.approx(0.0)

    def test_scaled_vectors(self):
        a = [1.0, 2.0]
        b = [2.0, 4.0]
        assert dense_cosine_similarity(a, b) == pytest.approx(1.0)

    def test_symmetry(self):
        a = [1.0, 2.0, 3.0]
        b = [4.0, 5.0, 6.0]
        assert dense_cosine_similarity(a, b) == pytest.approx(
            dense_cosine_similarity(b, a)
        )


# ---------------------------------------------------------------------------
# FastEmbedEncoder tests (skipped if fastembed not installed)
# ---------------------------------------------------------------------------


def _has_fastembed() -> bool:
    try:
        import fastembed  # noqa: F401
        return True
    except ImportError:
        return False


@pytest.mark.skipif(not _has_fastembed(), reason="fastembed not installed")
class TestFastEmbedEncoder:
    """Test the FastEmbed encoder (requires fastembed)."""

    def test_import(self):
        from core.learner.fastembed_encoder import FastEmbedEncoder
        assert FastEmbedEncoder is not None

    def test_creates_encoder(self):
        from core.learner.fastembed_encoder import FastEmbedEncoder
        encoder = FastEmbedEncoder()
        assert isinstance(encoder, SemanticEncoder)

    def test_dimension(self):
        from core.learner.fastembed_encoder import FastEmbedEncoder
        encoder = FastEmbedEncoder()
        assert encoder.dimension == 384

    def test_encode_single(self):
        import numpy as np

        from core.learner.fastembed_encoder import FastEmbedEncoder
        encoder = FastEmbedEncoder()
        vec = encoder.encode_single("hello world")
        assert isinstance(vec, list)
        assert len(vec) == 384
        # Values should be numeric (float, int, or numpy float)
        assert all(isinstance(x, (float, int, np.floating)) for x in vec)

    def test_encode_batch(self):
        from core.learner.fastembed_encoder import FastEmbedEncoder
        encoder = FastEmbedEncoder()
        texts = ["hello", "world", "test"]
        vecs = encoder.encode(texts)
        assert len(vecs) == 3
        assert all(len(v) == 384 for v in vecs)

    def test_encode_empty(self):
        from core.learner.fastembed_encoder import FastEmbedEncoder
        encoder = FastEmbedEncoder()
        vecs = encoder.encode([])
        assert vecs == []

    def test_similar_texts_high_similarity(self):
        from core.learner.fastembed_encoder import FastEmbedEncoder
        encoder = FastEmbedEncoder()
        a = encoder.encode_single("add item to a list")
        b = encoder.encode_single("append element to array")
        sim = dense_cosine_similarity(a, b)
        assert sim > 0.7, f"Expected high similarity for paraphrases, got {sim}"

    def test_different_texts_low_similarity(self):
        from core.learner.fastembed_encoder import FastEmbedEncoder
        encoder = FastEmbedEncoder()
        a = encoder.encode_single("add item to a list")
        b = encoder.encode_single("what is the capital of France")
        sim = dense_cosine_similarity(a, b)
        assert sim < 0.5, f"Expected low similarity for unrelated, got {sim}"

    def test_identical_text_perfect_similarity(self):
        from core.learner.fastembed_encoder import FastEmbedEncoder
        encoder = FastEmbedEncoder()
        a = encoder.encode_single("hello world")
        sim = dense_cosine_similarity(a, a)
        assert sim == pytest.approx(1.0)
