"""FastEmbed-based semantic encoder.

Uses BAAI/bge-small-en-v1.5 via the fastembed library (ONNX Runtime).
Model: 384-dimensional vectors, ~33MB quantized ONNX model.
Performance: ~1000 docs/sec on CPU after model load.

Requirements:
    pip install fastembed

Graceful fallback:
    If fastembed is not installed, FastEmbedEncoder raises ImportError
    with a clear message. The V2 learner falls back to V1 (TF-IDF only)
    when no semantic encoder is available.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from core.learner.semantic_encoder import SemanticEncoder

if TYPE_CHECKING:
    pass


class FastEmbedEncoder(SemanticEncoder):
    """Semantic encoder using FastEmbed (BAAI/bge-small-en-v1.5).

    This encoder produces 384-dimensional dense vectors that capture
    semantic meaning beyond lexical overlap. It uses ONNX Runtime for
    fast inference without requiring PyTorch.

    Usage:
        encoder = FastEmbedEncoder()
        vectors = encoder.encode(["hello world", "how are you"])
        single = encoder.encode_single("hello world")
        dim = encoder.dimension  # 384

    The model is downloaded on first use and cached in ~/.cache/huggingface/.
    Subsequent loads are fast (~0.1s).
    """

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5") -> None:
        """Initialize the FastEmbed encoder.

        Args:
            model_name: HuggingFace model name. Default is bge-small-en-v1.5.

        Raises:
            ImportError: If fastembed is not installed.
        """
        try:
            from fastembed import TextEmbedding
        except ImportError:
            raise ImportError(
                "fastembed is required for FastEmbedEncoder. "
                "Install it with: pip install fastembed"
            ) from None

        self._model_name = model_name
        self._model = TextEmbedding(model_name=model_name)
        self._dimension: int | None = None

    @property
    def dimension(self) -> int:
        """Return the vector dimensionality (384 for bge-small-en-v1.5)."""
        if self._dimension is None:
            # Encode a dummy text to discover dimension
            test = list(self._model.embed(["test"]))
            self._dimension = len(test[0])
        return self._dimension

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Encode a batch of texts into dense vectors.

        Args:
            texts: List of input texts.

        Returns:
            List of 384-dimensional vectors.
        """
        if not texts:
            return []
        embeddings = self._model.embed(texts)
        return [list(vec) for vec in embeddings]

    def encode_single(self, text: str) -> list[float]:
        """Encode a single text into a dense vector.

        Args:
            text: Input text.

        Returns:
            384-dimensional vector.
        """
        return self.encode([text])[0]
