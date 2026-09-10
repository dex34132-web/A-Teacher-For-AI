"""Semantic encoding interface and implementations.

Provides a pluggable interface for converting text into dense semantic
vectors. The SemanticEncoder ABC allows swapping between local models
(FastEmbed, sentence-transformers), API-based providers (OpenAI, Cohere),
or custom implementations without touching the learner or memory code.

FastEmbed is the default local implementation:
    - BAAI/bge-small-en-v1.5 (384-dim)
    - ONNX Runtime (no PyTorch)
    - ~33MB model, works offline after first download
    - ~1000 docs/sec on CPU
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------


class SemanticEncoder(ABC):
    """Interface for text-to-vector encoding.

    Every semantic encoder must implement:
    - encode: batch encode texts into dense vectors
    - encode_single: convenience for single text
    - dimension: the vector dimensionality
    """

    @abstractmethod
    def encode(self, texts: list[str]) -> list[list[float]]:
        """Encode a batch of texts into dense vectors.

        Args:
            texts: List of input texts.

        Returns:
            List of dense vectors, one per input text.
        """

    @abstractmethod
    def encode_single(self, text: str) -> list[float]:
        """Encode a single text into a dense vector.

        Args:
            text: Input text.

        Returns:
            Dense vector representation.
        """

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the dimensionality of the output vectors."""


# ---------------------------------------------------------------------------
# Cosine similarity for dense vectors
# ---------------------------------------------------------------------------


def dense_cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two dense vectors.

    Args:
        a: First vector.
        b: Second vector.

    Returns:
        Cosine similarity in [-1, 1].

    Raises:
        ValueError: If vectors have different dimensions or are zero-length.
    """
    if len(a) != len(b):
        raise ValueError(f"Vector dimensions mismatch: {len(a)} vs {len(b)}")

    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)
