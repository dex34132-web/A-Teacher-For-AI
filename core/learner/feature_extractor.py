"""Feature extraction for text inputs.

Converts raw text into numerical feature vectors using TF-IDF weighting.
This is the foundation for similarity-based learning - it transforms
meaningful text into a representation where similar texts are close.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Stop words - minimal set for English
# ---------------------------------------------------------------------------

STOP_WORDS: frozenset[str] = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after", "above", "below",
    "between", "out", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "both",
    "each", "few", "more", "most", "other", "some", "such", "no", "nor",
    "not", "only", "own", "same", "so", "than", "too", "very", "just",
    "don", "now", "and", "but", "or", "if", "while", "that", "this",
    "these", "those", "what", "which", "who", "whom", "it", "its",
    "i", "me", "my", "we", "our", "you", "your", "he", "him", "his",
    "she", "her", "they", "them", "their", "about", "up",
})


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

_WORD_PATTERN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Split text into normalized lowercase tokens.

    Args:
        text: Raw input text.

    Returns:
        List of lowercase alphanumeric tokens.
    """
    return _WORD_PATTERN.findall(text.lower())


def remove_stop_words(tokens: list[str]) -> list[str]:
    """Remove common stop words from token list.

    Args:
        tokens: Input tokens.

    Returns:
        Filtered tokens without stop words.
    """
    return [t for t in tokens if t not in STOP_WORDS]


# ---------------------------------------------------------------------------
# N-grams
# ---------------------------------------------------------------------------

def ngrams(tokens: list[str], n: int) -> list[str]:
    """Generate n-grams from a token list.

    Args:
        tokens: Input tokens.
        n: N-gram size (1 = unigrams, 2 = bigrams, etc.).

    Returns:
        List of n-gram strings joined by underscore.
    """
    if n <= 1:
        return tokens
    return ["_".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


# ---------------------------------------------------------------------------
# Feature vector
# ---------------------------------------------------------------------------

@dataclass
class FeatureVector:
    """Sparse feature vector with TF-IDF weights.

    Attributes:
        features: Mapping from feature name to weight.
        norm: L2 norm of the vector (for cosine similarity).
    """

    features: dict[str, float] = field(default_factory=dict)
    norm: float = 0.0

    def __post_init__(self) -> None:
        """Compute L2 norm after initialization."""
        if not self.norm and self.features:
            self.norm = math.sqrt(sum(w * w for w in self.features.values()))


# ---------------------------------------------------------------------------
# TF-IDF Feature Extractor
# ---------------------------------------------------------------------------

class FeatureExtractor:
    """Extracts TF-IDF features from text.

    This extractor builds a vocabulary from observed documents and computes
    TF-IDF weights. It supports incremental updates - new documents can be
    added without recomputing the entire corpus.

    The TF-IDF formula used:
        tfidf(t, d) = tf(t, d) * idf(t)

    Where:
        tf(t, d) = count(t in d) / len(d)  (term frequency)
        idf(t) = log(N / df(t))             (inverse document frequency)
        N = total documents seen
        df(t) = number of documents containing term t
    """

    def __init__(
        self,
        use_idf: bool = True,
        sublinear_tf: bool = False,
        ngram_range: tuple[int, int] = (1, 1),
        min_df: int = 1,
    ) -> None:
        """Initialize the feature extractor.

        Args:
            use_idf: Whether to use IDF weighting.
            sublinear_tf: Whether to use log-scaled term frequency.
            ngram_range: (min_n, max_n) for n-gram generation.
            min_df: Minimum document frequency to include a term.
        """
        self.use_idf = use_idf
        self.sublinear_tf = sublinear_tf
        self.ngram_range = ngram_range
        self.min_df = min_df

        # Vocabulary: term -> document frequency
        self._df: dict[str, int] = {}
        self._num_docs: int = 0

    @property
    def vocabulary(self) -> dict[str, int]:
        """Return the document frequency for all terms."""
        return dict(self._df)

    @property
    def num_documents(self) -> int:
        """Return the number of documents seen."""
        return self._num_docs

    def _extract_terms(self, text: str) -> list[str]:
        """Extract all terms (including n-grams) from text.

        Args:
            text: Raw input text.

        Returns:
            List of terms.
        """
        tokens = remove_stop_words(tokenize(text))
        terms = []
        for n in range(self.ngram_range[0], self.ngram_range[1] + 1):
            terms.extend(ngrams(tokens, n))
        return terms

    def _compute_tf(self, terms: list[str]) -> dict[str, float]:
        """Compute term frequency for a document.

        Args:
            terms: Tokenized terms.

        Returns:
            Mapping from term to TF weight.
        """
        if not terms:
            return {}

        # Count term occurrences
        counts: dict[str, int] = {}
        for term in terms:
            counts[term] = counts.get(term, 0) + 1

        # Compute TF
        doc_len = len(terms)
        tf: dict[str, float] = {}
        for term, count in counts.items():
            if self.sublinear_tf:
                tf[term] = 1.0 + math.log(count) if count > 0 else 0.0
            else:
                tf[term] = count / doc_len

        return tf

    def _compute_idf(self, term: str) -> float:
        """Compute IDF for a term.

        IDF is computed BEFORE the current document is added to the
        vocabulary, so ``_num_docs`` reflects only prior documents.

        Uses smoothed IDF: ``log(1 + N / (df + 1))``

        - brand-new term (df=0): ``log(1 + N)`` — high weight
        - single-document term (df=1): ``log(1 + N/2)`` — moderate weight
        - corpus-wide term (df=N): ``log(2) ≈ 0.69`` — low weight

        Corpus-wide terms are not zeroed here; instead, the similarity
        function applies a weight threshold to filter them.

        Args:
            term: The term to compute IDF for.

        Returns:
            IDF weight, always > 0 when ``_num_docs > 0``.
        """
        if not self.use_idf or self._num_docs == 0:
            return 1.0

        df = self._df.get(term, 0)
        return math.log(1.0 + self._num_docs / (df + 1))

    def fit(self, text: str) -> FeatureVector:
        """Extract features from text and update vocabulary.

        This method both extracts features AND updates the internal
        vocabulary/IDF statistics. Call this for each new training document.

        Features are stored as raw term frequencies (TF only).  IDF is
        applied lazily during similarity comparison via ``weight_for()``
        so that stored vectors remain consistent as the vocabulary grows.

        Args:
            text: Raw input text.

        Returns:
            Feature vector with raw TF weights.
        """
        terms = self._extract_terms(text)

        # Compute TF only
        tf = self._compute_tf(terms)

        # Update vocabulary AFTER computing features
        unique_terms = set(terms)
        for term in unique_terms:
            self._df[term] = self._df.get(term, 0) + 1
        self._num_docs += 1

        return FeatureVector(features=tf)

    def weight_for(self, term: str) -> float:
        """Return the current IDF weight for a term.

        This is called during similarity comparison, not at storage time,
        so it always reflects the latest vocabulary state.

        Args:
            term: The term to weight.

        Returns:
            IDF weight for the term.
        """
        return self._compute_idf(term)

    def transform(self, text: str) -> FeatureVector:
        """Extract features from text WITHOUT updating vocabulary.

        Use this for query/test documents where you don't want to
        affect the IDF statistics.

        Features are stored as raw TF.  Apply IDF during comparison.

        Args:
            text: Raw input text.

        Returns:
            Feature vector with raw TF weights.
        """
        terms = self._extract_terms(text)
        tf = self._compute_tf(terms)
        return FeatureVector(features=tf)

    def get_params(self) -> dict:
        """Return extractor parameters for serialization."""
        return {
            "use_idf": self.use_idf,
            "sublinear_tf": self.sublinear_tf,
            "ngram_range": list(self.ngram_range),
            "min_df": self.min_df,
        }

    def set_params(self, df: dict[str, int], num_docs: int) -> None:
        """Restore extractor state from serialized data.

        Args:
            df: Document frequency mapping.
            num_docs: Number of documents previously seen.
        """
        self._df = dict(df)
        self._num_docs = num_docs
