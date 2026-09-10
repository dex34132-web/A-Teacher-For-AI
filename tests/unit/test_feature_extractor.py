"""Tests for FeatureExtractor.

Covers tokenization, stop word removal, n-gram generation, TF/IDF
computation, fit vs transform behavior, and vocabulary building.
"""

from __future__ import annotations

import math

import pytest

from core.learner.feature_extractor import (
    STOP_WORDS,
    FeatureExtractor,
    FeatureVector,
    ngrams,
    remove_stop_words,
    tokenize,
)

# ---------------------------------------------------------------------------
# Tokenization
# ---------------------------------------------------------------------------


class TestTokenize:
    """Test the tokenize function splits and normalizes text."""

    def test_basic_splitting(self) -> None:
        """Lowercase words are returned as individual tokens."""
        tokens = tokenize("Hello World")
        assert tokens == ["hello", "world"]

    def test_lowercasing(self) -> None:
        """Mixed-case input is lowercased."""
        tokens = tokenize("FOO bar Baz")
        assert tokens == ["foo", "bar", "baz"]

    def test_alphanumeric_only(self) -> None:
        """Non-alphanumeric characters are stripped."""
        tokens = tokenize("hello, world! How's it going?")
        assert tokens == ["hello", "world", "how", "s", "it", "going"]

    def test_numbers_preserved(self) -> None:
        """Numeric tokens are kept."""
        tokens = tokenize("version 2 released in 2024")
        assert tokens == ["version", "2", "released", "in", "2024"]

    def test_empty_string(self) -> None:
        """Empty input returns an empty list."""
        assert tokenize("") == []

    def test_punctuation_only(self) -> None:
        """Punctuation-only input yields no tokens."""
        assert tokenize("...!!!???") == []


# ---------------------------------------------------------------------------
# Stop word removal
# ---------------------------------------------------------------------------


class TestRemoveStopWords:
    """Test stop word filtering."""

    def test_common_words_removed(self) -> None:
        """Common English stop words are removed."""
        tokens = ["the", "cat", "is", "on", "the", "mat"]
        result = remove_stop_words(tokens)
        assert result == ["cat", "mat"]

    def test_no_stop_words(self) -> None:
        """If no stop words are present, all tokens pass through."""
        tokens = ["python", "programming", "fun"]
        result = remove_stop_words(tokens)
        assert result == tokens

    def test_all_stop_words(self) -> None:
        """If every token is a stop word, result is empty."""
        tokens = ["the", "is", "a", "it"]
        result = remove_stop_words(tokens)
        assert result == []

    def test_stop_words_set_is_frozen(self) -> None:
        """STOP_WORDS is a frozen set (immutable)."""
        assert isinstance(STOP_WORDS, frozenset)

    def test_empty_input(self) -> None:
        """Empty token list returns empty list."""
        assert remove_stop_words([]) == []


# ---------------------------------------------------------------------------
# N-grams
# ---------------------------------------------------------------------------


class TestNgrams:
    """Test n-gram generation."""

    def test_unigrams(self) -> None:
        """n=1 returns the original tokens."""
        tokens = ["a", "b", "c"]
        assert ngrams(tokens, 1) == ["a", "b", "c"]

    def test_bigrams(self) -> None:
        """n=2 produces two-element underscore-joined strings."""
        tokens = ["a", "b", "c"]
        assert ngrams(tokens, 2) == ["a_b", "b_c"]

    def test_trigrams(self) -> None:
        """n=3 produces three-element bigrams."""
        tokens = ["a", "b", "c", "d"]
        assert ngrams(tokens, 3) == ["a_b_c", "b_c_d"]

    def test_n_greater_than_length(self) -> None:
        """n larger than token count returns empty list."""
        assert ngrams(["a", "b"], 5) == []

    def test_single_token(self) -> None:
        """Single token with n=1 returns that token."""
        assert ngrams(["only"], 1) == ["only"]

    def test_empty_tokens(self) -> None:
        """Empty token list returns empty list."""
        assert ngrams([], 2) == []


# ---------------------------------------------------------------------------
# TF computation
# ---------------------------------------------------------------------------


class TestTF:
    """Test term frequency computation."""

    def test_equal_tf(self) -> None:
        """Each unique term gets count/total."""
        ext = FeatureExtractor(use_idf=False)
        tf = ext._compute_tf(["a", "b", "c"])
        assert tf == {
            "a": pytest.approx(1 / 3),
            "b": pytest.approx(1 / 3),
            "c": pytest.approx(1 / 3),
        }

    def test_repeated_term(self) -> None:
        """Repeated terms have proportionally higher TF."""
        ext = FeatureExtractor(use_idf=False)
        tf = ext._compute_tf(["a", "a", "b"])
        assert tf["a"] == pytest.approx(2 / 3)
        assert tf["b"] == pytest.approx(1 / 3)

    def test_empty_terms(self) -> None:
        """Empty term list returns empty dict."""
        ext = FeatureExtractor()
        assert ext._compute_tf([]) == {}

    def test_sublinear_tf(self) -> None:
        """Sublinear TF uses 1 + log(count)."""
        ext = FeatureExtractor(use_idf=False, sublinear_tf=True)
        tf = ext._compute_tf(["x", "x", "x"])
        assert tf["x"] == pytest.approx(1.0 + math.log(3))


# ---------------------------------------------------------------------------
# IDF computation
# ---------------------------------------------------------------------------


class TestIDF:
    """Test inverse document frequency computation."""

    def test_no_docs_returns_one(self) -> None:
        """IDF returns 1.0 when no documents have been seen."""
        ext = FeatureExtractor(use_idf=True)
        assert ext._compute_idf("term") == 1.0

    def test_idf_decreases_with_frequency(self) -> None:
        """IDF is lower for terms that appear in more documents."""
        ext = FeatureExtractor(use_idf=True)
        ext._df = {"common": 10, "rare": 1}
        ext._num_docs = 10
        assert ext._compute_idf("rare") > ext._compute_idf("common")

    def test_idf_formula(self) -> None:
        """IDF follows the smoothed formula log(1 + N/(df+1))."""
        ext = FeatureExtractor(use_idf=True)
        ext._df = {"term": 2}
        ext._num_docs = 8
        expected = math.log(1.0 + 8 / 3)
        assert ext._compute_idf("term") == pytest.approx(expected)

    def test_disabled_idf(self) -> None:
        """IDF always returns 1.0 when use_idf=False."""
        ext = FeatureExtractor(use_idf=False)
        ext._df = {"term": 5}
        ext._num_docs = 10
        assert ext._compute_idf("term") == 1.0

    def test_below_min_df(self) -> None:
        """Terms with low df still get non-zero IDF (smoothed formula)."""
        ext = FeatureExtractor(use_idf=True, min_df=3)
        ext._df = {"term": 1}
        ext._num_docs = 5
        # Smoothed IDF never returns 0 for df >= 0
        idf = ext._compute_idf("term")
        assert idf > 0.0


# ---------------------------------------------------------------------------
# Fit vs Transform
# ---------------------------------------------------------------------------


class TestFitVsTransform:
    """Test that fit updates vocabulary while transform does not."""

    def test_fit_updates_vocab(self) -> None:
        """fit() increments document frequency and doc count."""
        ext = FeatureExtractor(use_idf=True)
        ext.fit("hello world")
        assert ext.num_documents == 1
        assert ext.vocabulary["hello"] == 1
        assert ext.vocabulary["world"] == 1

    def test_transform_preserves_vocab(self) -> None:
        """transform() does not change document frequency."""
        ext = FeatureExtractor(use_idf=True)
        ext.fit("hello world")
        transform_before = dict(ext.vocabulary)
        ext.transform("hello again")
        assert ext.vocabulary == transform_before
        assert ext.num_documents == 1

    def test_fit_increments_df(self) -> None:
        """Multiple fit calls increment document frequency."""
        ext = FeatureExtractor(use_idf=True)
        ext.fit("cat sat mat")
        ext.fit("dog sat mat")
        assert ext.vocabulary["cat"] == 1
        assert ext.vocabulary["mat"] == 2
        assert ext.num_documents == 2

    def test_fit_returns_feature_vector(self) -> None:
        """fit() returns a FeatureVector; may be empty if all terms are stop words."""
        ext = FeatureExtractor(use_idf=True)
        vec = ext.fit("some meaningful unique text")
        assert isinstance(vec, FeatureVector)

    def test_transform_returns_feature_vector(self) -> None:
        """transform() returns a FeatureVector from a fitted vocabulary."""
        ext = FeatureExtractor(use_idf=True)
        ext.fit("programming language")
        ext.fit("coding language")
        vec = ext.transform("programming")
        assert isinstance(vec, FeatureVector)
        assert len(vec.features) > 0


# ---------------------------------------------------------------------------
# Vocabulary building
# ---------------------------------------------------------------------------


class TestVocabulary:
    """Test vocabulary properties and state management."""

    def test_empty_initial_vocab(self) -> None:
        """New extractor has empty vocabulary."""
        ext = FeatureExtractor()
        assert ext.vocabulary == {}
        assert ext.num_documents == 0

    def test_get_params(self) -> None:
        """get_params returns serializable configuration."""
        ext = FeatureExtractor(use_idf=False, sublinear_tf=True, ngram_range=(1, 2), min_df=2)
        params = ext.get_params()
        assert params["use_idf"] is False
        assert params["sublinear_tf"] is True
        assert params["ngram_range"] == [1, 2]
        assert params["min_df"] == 2

    def test_set_params_restores_state(self) -> None:
        """set_params restores document frequency and doc count."""
        ext = FeatureExtractor()
        ext.set_params(df={"hello": 3, "world": 1}, num_docs=5)
        assert ext.vocabulary == {"hello": 3, "world": 1}
        assert ext.num_documents == 5

    def test_vocabulary_is_a_copy(self) -> None:
        """vocabulary property returns a copy, not the internal dict."""
        ext = FeatureExtractor()
        ext.fit("test")
        vocab = ext.vocabulary
        vocab["injected"] = 999
        assert "injected" not in ext.vocabulary
