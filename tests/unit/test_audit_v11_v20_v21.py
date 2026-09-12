"""Comprehensive audit tests for V1.1, V2.0, and V2.1 learner components.

Covers:
- V1.1: TF-IDF feature extraction, similarity, learning loop
- V2.0: Semantic encoder, hybrid memory, blended similarity
- V2.1: Retrieval scoring, quality, recency, diversity, usage tracking
"""

from __future__ import annotations

import json
import math
import tempfile
import time
from pathlib import Path

import pytest

from core.learner.base import LearningInput, LearningStatus
from core.learner.feature_extractor import (
    FeatureExtractor,
    FeatureVector,
    ngrams,
    remove_stop_words,
    tokenize,
)
from core.learner.hybrid_memory import HybridExample, HybridMemory
from core.learner.learner_v1 import Prediction, SimilarityLearner
from core.learner.learner_v2 import HybridSimilarityLearner
from core.learner.memory import ExampleMemory
from core.learner.retrieval_scorer import (
    ScorerConfig,
    diversify_top_k,
    quality_score,
    recency_score,
    retrieval_score,
)
from core.learner.semantic_encoder import SemanticEncoder, dense_cosine_similarity
from core.learner.similarity import cosine_similarity, weighted_similarity

# ======================================================================
# Helpers
# ======================================================================


def _make_input(text: str, output: str) -> LearningInput:
    return LearningInput(observation={"input": text, "output": output})


def _learn(learner, text: str, output: str):
    return learner.learn(_make_input(text, output))


def _tmp_dir() -> str:
    return tempfile.mkdtemp()


# ======================================================================
# SECTION 1: V1.1 TF-IDF Feature Extraction (30+ tests)
# ======================================================================


class TestTokenize:
    def test_empty_string(self):
        assert tokenize("") == []

    def test_whitespace_only(self):
        assert tokenize("   \t\n  ") == []

    def test_single_word(self):
        assert tokenize("hello") == ["hello"]

    def test_lowercasing(self):
        assert tokenize("Hello World") == ["hello", "world"]

    def test_numbers(self):
        assert tokenize("test123 foo456") == ["test123", "foo456"]

    def test_punctuation_stripped(self):
        assert tokenize("hello, world!") == ["hello", "world"]

    def test_mixed_alphanumeric(self):
        assert tokenize("abc 123 !@#") == ["abc", "123"]

    def test_unicode_ascii(self):
        tokens = tokenize("café résumé")
        assert "café" in tokens or "caf" in tokens

    def test_only_stop_words(self):
        tokens = remove_stop_words(tokenize("the is a an"))
        assert tokens == []

    def test_stop_words_removed(self):
        tokens = tokenize("the quick brown fox")
        # 'the' is a stop word; 'quick', 'brown', 'fox' are not
        assert "the" not in remove_stop_words(tokens)

    def test_consecutive_spaces(self):
        assert tokenize("a  b   c") == ["a", "b", "c"]

    def test_tab_and_newline(self):
        assert tokenize("hello\tworld\nfoo") == ["hello", "world", "foo"]


class TestNgrams:
    def test_unigrams(self):
        assert ngrams(["a", "b", "c"], 1) == ["a", "b", "c"]

    def test_bigrams(self):
        assert ngrams(["a", "b", "c"], 2) == ["a_b", "b_c"]

    def test_trigrams(self):
        assert ngrams(["a", "b", "c", "d"], 3) == ["a_b_c", "b_c_d"]

    def test_single_token_bigram(self):
        assert ngrams(["a"], 2) == []

    def test_empty_tokens(self):
        assert ngrams([], 1) == []

    def test_bigrams_short_list(self):
        assert ngrams(["a", "b"], 2) == ["a_b"]


class TestFeatureExtractor:
    def test_fit_returns_feature_vector(self):
        ext = FeatureExtractor()
        vec = ext.fit("hello world hello")
        assert isinstance(vec, FeatureVector)
        assert "hello" in vec.features

    def test_fit_updates_vocabulary(self):
        ext = FeatureExtractor()
        ext.fit("alpha beta")
        ext.fit("alpha gamma")
        vocab = ext.vocabulary
        assert vocab["alpha"] == 2
        assert vocab["beta"] == 1
        assert vocab["gamma"] == 1

    def test_num_documents_increments(self):
        ext = FeatureExtractor()
        assert ext.num_documents == 0
        ext.fit("doc one")
        assert ext.num_documents == 1
        ext.fit("doc two")
        assert ext.num_documents == 2

    def test_transform_does_not_update_vocabulary(self):
        ext = FeatureExtractor()
        ext.fit("hello world")
        vocab_before = ext.vocabulary.copy()
        ext.transform("goodbye moon")
        assert ext.vocabulary == vocab_before

    def test_empty_text_fit(self):
        ext = FeatureExtractor()
        vec = ext.fit("")
        assert vec.features == {}

    def test_idf_computation_single_doc(self):
        ext = FeatureExtractor()
        ext.fit("unique_term")
        # After one doc, idf = log(1 + 1/(0+1)) = log(2)
        idf = ext.weight_for("unique_term")
        expected = math.log(1.0 + 1.0 / (0 + 1))
        assert abs(idf - expected) < 1e-6

    def test_idf_computation_common_term(self):
        ext = FeatureExtractor()
        ext.fit("common word")
        ext.fit("common other")
        ext.fit("common stuff")
        # common in 3 docs out of 3
        idf = ext.weight_for("common")
        expected = math.log(1.0 + 3.0 / (3.0 + 1))
        assert abs(idf - expected) < 1e-6

    def test_idf_computation_rare_term(self):
        ext = FeatureExtractor()
        ext.fit("common rare")
        ext.fit("common other")
        # rare in 1 doc out of 2
        idf = ext.weight_for("rare")
        expected = math.log(1.0 + 2.0 / (1.0 + 1))
        assert abs(idf - expected) < 1e-6

    def test_idf_unseen_term(self):
        ext = FeatureExtractor()
        ext.fit("hello")
        idf = ext.weight_for("never_seen")
        # unseen: df=0, idf = log(1 + 1/1) = log(2)
        expected = math.log(1.0 + 1.0 / (0 + 1))
        assert abs(idf - expected) < 1e-6

    def test_no_idf(self):
        ext = FeatureExtractor(use_idf=False)
        ext.fit("hello world")
        idf = ext.weight_for("hello")
        assert idf == 1.0

    def test_tf_linear(self):
        ext = FeatureExtractor(sublinear_tf=False)
        vec = ext.fit("cat cat dog")
        # cat appears 2/3, dog appears 1/3
        assert abs(vec.features["cat"] - 2.0 / 3.0) < 1e-6
        assert abs(vec.features["dog"] - 1.0 / 3.0) < 1e-6

    def test_tf_sublinear(self):
        ext = FeatureExtractor(sublinear_tf=True)
        vec = ext.fit("cat cat dog")
        # sublinear: 1 + log(count)
        assert abs(vec.features["cat"] - (1.0 + math.log(2))) < 1e-6
        assert abs(vec.features["dog"] - (1.0 + math.log(1))) < 1e-6

    def test_empty_terms_tf(self):
        ext = FeatureExtractor()
        vec = ext.fit("")
        assert vec.features == {}

    def test_feature_vector_norm(self):
        vec = FeatureVector(features={"a": 3.0, "b": 4.0})
        assert abs(vec.norm - 5.0) < 1e-6

    def test_feature_vector_empty_norm(self):
        vec = FeatureVector(features={})
        assert vec.norm == 0.0

    def test_feature_vector_post_init_computes_norm(self):
        vec = FeatureVector(features={"x": 1.0})
        assert abs(vec.norm - 1.0) < 1e-6

    def test_ngram_range(self):
        ext = FeatureExtractor(ngram_range=(1, 1))
        vec = ext.fit("hello world")
        # Only unigrams: hello, world
        assert "hello" in vec.features
        assert "world" in vec.features
        assert "hello_world" not in vec.features

    def test_bigram_range(self):
        ext = FeatureExtractor(ngram_range=(2, 2))
        vec = ext.fit("hello world foo")
        assert "hello_world" in vec.features
        assert "world_foo" in vec.features

    def test_vocabulary_is_copy(self):
        ext = FeatureExtractor()
        ext.fit("hello world")
        vocab1 = ext.vocabulary
        vocab1["injected"] = 999
        vocab2 = ext.vocabulary
        assert "injected" not in vocab2

    def test_get_params(self):
        ext = FeatureExtractor(
            use_idf=True, sublinear_tf=True,
            ngram_range=(1, 3), min_df=2,
        )
        params = ext.get_params()
        assert params["use_idf"] is True
        assert params["sublinear_tf"] is True
        assert params["ngram_range"] == [1, 3]
        assert params["min_df"] == 2

    def test_set_params_restores_state(self):
        ext = FeatureExtractor()
        ext.set_params(df={"hello": 3, "world": 2}, num_docs=5)
        assert ext.vocabulary == {"hello": 3, "world": 2}
        assert ext.num_documents == 5

    def test_set_params_is_defensive_copy(self):
        ext = FeatureExtractor()
        original_df = {"hello": 3}
        ext.set_params(df=original_df, num_docs=1)
        original_df["hello"] = 999
        assert ext.vocabulary["hello"] == 3

    def test_stop_words_filtered(self):
        ext = FeatureExtractor()
        vec = ext.fit("the quick brown fox is fast")
        # 'the', 'is' are stop words
        assert "the" not in vec.features
        assert "is" not in vec.features
        assert "quick" in vec.features

    def test_min_df_filtering(self):
        ext = FeatureExtractor(min_df=2)
        ext.fit("alpha beta")
        ext.fit("alpha gamma")
        # alpha in 2 docs, beta in 1, gamma in 1
        assert "alpha" in ext.vocabulary


# ======================================================================
# SECTION 2: V1.1 Similarity (20+ tests)
# ======================================================================


class TestCosineSimilarity:
    def test_identical_vectors(self):
        a = FeatureVector(features={"x": 1.0, "y": 2.0})
        b = FeatureVector(features={"x": 1.0, "y": 2.0})
        assert abs(cosine_similarity(a, b) - 1.0) < 1e-6

    def test_orthogonal_vectors(self):
        a = FeatureVector(features={"x": 1.0})
        b = FeatureVector(features={"y": 1.0})
        assert abs(cosine_similarity(a, b)) < 1e-6

    def test_zero_vector_a(self):
        a = FeatureVector(features={})
        b = FeatureVector(features={"x": 1.0})
        assert cosine_similarity(a, b) == 0.0

    def test_zero_vector_b(self):
        a = FeatureVector(features={"x": 1.0})
        b = FeatureVector(features={})
        assert cosine_similarity(a, b) == 0.0

    def test_both_zero(self):
        a = FeatureVector(features={})
        b = FeatureVector(features={})
        assert cosine_similarity(a, b) == 0.0

    def test_near_identical(self):
        a = FeatureVector(features={"x": 1.0, "y": 2.0})
        b = FeatureVector(features={"x": 1.0, "y": 2.01})
        sim = cosine_similarity(a, b)
        assert sim > 0.99

    def test_partial_overlap(self):
        a = FeatureVector(features={"x": 1.0, "y": 1.0})
        b = FeatureVector(features={"y": 1.0, "z": 1.0})
        sim = cosine_similarity(a, b)
        assert 0.0 < sim < 1.0

    def test_with_idf_weighting(self):
        ext = FeatureExtractor()
        ext.fit("common rare")
        a = FeatureVector(features={"common": 1.0, "rare": 1.0})
        b = FeatureVector(features={"common": 1.0, "rare": 1.0})
        sim = cosine_similarity(a, b, ext)
        assert abs(sim - 1.0) < 1e-6

    def test_large_sparse_vectors(self):
        features_a = {f"f{i}": 1.0 for i in range(1000)}
        features_b = {f"f{i}": 1.0 for i in range(1000)}
        a = FeatureVector(features=features_a)
        b = FeatureVector(features=features_b)
        assert abs(cosine_similarity(a, b) - 1.0) < 1e-6

    def test_large_sparse_no_overlap(self):
        features_a = {f"a{i}": 1.0 for i in range(500)}
        features_b = {f"b{i}": 1.0 for i in range(500)}
        a = FeatureVector(features=features_a)
        b = FeatureVector(features=features_b)
        assert cosine_similarity(a, b) == 0.0

    def test_one_shared_feature_many_unique(self):
        a = FeatureVector(features={"shared": 1.0, "u1": 1.0, "u2": 1.0})
        b = FeatureVector(features={"shared": 1.0, "v1": 1.0, "v2": 1.0})
        sim = cosine_similarity(a, b)
        assert 0.0 < sim < 0.5


class TestWeightedSimilarity:
    def test_basic_ordering(self):
        query = FeatureVector(features={"x": 1.0, "y": 1.0})
        v1 = FeatureVector(features={"x": 1.0, "y": 1.0})
        v2 = FeatureVector(features={"x": 1.0})
        candidates = [(v1, 1.0), (v2, 1.0)]
        results = weighted_similarity(query, candidates)
        # v1 is more similar to query than v2
        assert results[0][0] == 0
        assert results[0][1] >= results[1][1]

    def test_weight_affects_score(self):
        query = FeatureVector(features={"x": 1.0})
        v = FeatureVector(features={"x": 1.0})
        candidates = [(v, 1.0), (v, 0.5)]
        results = weighted_similarity(query, candidates)
        assert results[0][1] > results[1][1]

    def test_empty_candidates(self):
        query = FeatureVector(features={"x": 1.0})
        results = weighted_similarity(query, [])
        assert results == []

    def test_zero_weight_candidate(self):
        query = FeatureVector(features={"x": 1.0})
        v = FeatureVector(features={"x": 1.0})
        candidates = [(v, 0.0)]
        results = weighted_similarity(query, candidates)
        assert results[0][1] == 0.0

    def test_sorted_descending(self):
        query = FeatureVector(features={"a": 1.0, "b": 1.0})
        candidates = [
            (FeatureVector(features={"a": 1.0}), 1.0),
            (FeatureVector(features={"a": 1.0, "b": 1.0}), 1.0),
            (FeatureVector(features={"b": 1.0}), 1.0),
        ]
        results = weighted_similarity(query, candidates)
        scores = [s for _, s in results]
        assert scores == sorted(scores, reverse=True)

    def test_with_idf(self):
        ext = FeatureExtractor()
        ext.fit("alpha beta gamma")
        query = FeatureVector(features={"alpha": 1.0, "beta": 1.0})
        v1 = FeatureVector(features={"alpha": 1.0, "beta": 1.0})
        v2 = FeatureVector(features={"alpha": 1.0})
        results = weighted_similarity(query, [(v1, 1.0), (v2, 1.0)], ext)
        assert results[0][1] > results[1][1]


# ======================================================================
# SECTION 3: V1.1 Learning Loop (20+ tests)
# ======================================================================


class TestV1Learning:
    def test_first_example_learned(self):
        learner = SimilarityLearner()
        out = _learn(learner, "hello world", "greeting")
        assert out.status == LearningStatus.UPDATED
        assert learner.memory.count() == 1

    def test_incremental_learning(self):
        learner = SimilarityLearner()
        _learn(learner, "hello world", "greeting")
        _learn(learner, "goodbye moon", "farewell")
        assert learner.memory.count() == 2

    def test_predict_after_learning(self):
        learner = SimilarityLearner()
        _learn(learner, "hello world", "greeting")
        pred = learner.predict("hello world")
        assert pred.output == "greeting"
        assert pred.confidence > 0.0

    def test_predict_empty_memory(self):
        learner = SimilarityLearner()
        pred = learner.predict("anything")
        assert pred.output == ""
        assert pred.confidence == 0.0

    def test_feedback_strengthens_correct(self):
        learner = SimilarityLearner()
        _learn(learner, "hello world", "greeting")
        # Find the example id
        examples = learner.memory.get_all()
        ex_id = examples[0].id
        before = examples[0].weight
        learner.feedback("hello world", "greeting", correct=True)
        after = learner.memory.get(ex_id).weight
        assert after > before

    def test_feedback_weakens_incorrect(self):
        learner = SimilarityLearner()
        _learn(learner, "hello world", "greeting")
        examples = learner.memory.get_all()
        ex_id = examples[0].id
        before = examples[0].weight
        learner.feedback("hello world", "greeting", correct=False)
        after = learner.memory.get(ex_id).weight
        assert after < before

    def test_correction_adds_example(self):
        learner = SimilarityLearner()
        _learn(learner, "hello world", "wrong")
        before_count = learner.memory.count()
        learner.feedback(
            "hello world", "wrong", correct=False,
            actual_output="greeting",
        )
        assert learner.memory.count() == before_count + 1

    def test_correction_no_duplicate(self):
        learner = SimilarityLearner()
        _learn(learner, "hello world", "greeting")
        # Already exists with correct output — no duplicate
        before = learner.memory.count()
        learner.feedback(
            "hello world", "greeting", correct=True,
            actual_output="greeting",
        )
        assert learner.memory.count() == before

    def test_reset_clears_everything(self):
        learner = SimilarityLearner()
        _learn(learner, "hello", "a")
        _learn(learner, "world", "b")
        learner.reset()
        assert learner.memory.count() == 0
        assert len(learner.extractor.vocabulary) == 0

    def test_confidence_bounds(self):
        learner = SimilarityLearner()
        _learn(learner, "hello world", "greeting")
        _learn(learner, "goodbye moon", "farewell")
        pred = learner.predict("hello world")
        assert 0.0 <= pred.confidence <= 1.0

    def test_multiple_categories(self):
        learner = SimilarityLearner()
        _learn(learner, "hello there", "greeting")
        _learn(learner, "goodbye friend", "farewell")
        pred_hello = learner.predict("hello there")
        pred_goodbye = learner.predict("goodbye friend")
        assert pred_hello.output == "greeting"
        assert pred_goodbye.output == "farewell"

    def test_predict_legacy_returns_prediction(self):
        learner = SimilarityLearner()
        _learn(learner, "hello world", "greeting")
        pred = learner.predict("hello world")
        assert isinstance(pred, Prediction)

    def test_state_save_load_roundtrip(self):
        learner = SimilarityLearner()
        _learn(learner, "hello world", "greeting")
        _learn(learner, "goodbye moon", "farewell")
        learner.feedback("hello world", "greeting", correct=True)

        path = _tmp_dir()
        learner.save_state(path)
        loaded = SimilarityLearner.load_state(path)

        assert loaded.memory.count() == 2
        pred = loaded.predict("hello world")
        assert pred.output == "greeting"

    def test_parameters_property(self):
        learner = SimilarityLearner(k=3, min_confidence=0.2)
        params = learner.parameters
        assert params["k"] == 3
        assert params["min_confidence"] == 0.2
        assert params["num_examples"] == 0

    def test_parameters_reflect_learning(self):
        learner = SimilarityLearner()
        _learn(learner, "hello", "a")
        params = learner.parameters
        assert params["num_examples"] == 1
        assert params["num_features"] > 0

    def test_feedback_counts_tracked(self):
        learner = SimilarityLearner()
        _learn(learner, "hello", "a")
        learner.feedback("hello", "a", correct=True)
        learner.feedback("hello", "a", correct=False)
        params = learner.parameters
        assert params["total_predictions"] >= 0
        # feedback_count is tracked per-example, not in parameters
        ex = learner.memory.get_all()[0]
        assert ex.feedback_count == 2

    def test_accuracy_property(self):
        learner = SimilarityLearner()
        _learn(learner, "hello", "a")
        _learn(learner, "world", "b")
        # Manually set stats
        learner._total_predictions = 10
        learner._correct_predictions = 7
        params = learner.parameters
        assert abs(params["accuracy"] - 0.7) < 1e-6

    def test_accuracy_zero_predictions(self):
        learner = SimilarityLearner()
        params = learner.parameters
        assert params["accuracy"] == 0.0

    def test_mode_is_online(self):
        learner = SimilarityLearner()
        from core.learner.base import LearningMode
        assert learner.mode == LearningMode.ONLINE

    def test_memory_and_extractor_accessible(self):
        learner = SimilarityLearner()
        assert isinstance(learner.memory, ExampleMemory)
        assert isinstance(learner.extractor, FeatureExtractor)

    def test_learn_missing_input_returns_error(self):
        learner = SimilarityLearner()
        out = learner.learn(LearningInput(observation={"output": "a"}))
        assert out.status == LearningStatus.ERROR

    def test_learn_missing_output_returns_error(self):
        learner = SimilarityLearner()
        out = learner.learn(LearningInput(observation={"input": "a"}))
        assert out.status == LearningStatus.ERROR

    def test_sublinear_tf_option(self):
        learner = SimilarityLearner(use_sublinear_tf=True)
        _learn(learner, "hello hello world", "greeting")
        pred = learner.predict("hello world")
        assert pred.output == "greeting"

    def test_custom_k(self):
        learner = SimilarityLearner(k=1)
        _learn(learner, "hello world", "greeting")
        _learn(learner, "hello there", "greeting2")
        pred = learner.predict("hello world")
        # With k=1, only the single best match is used
        assert pred.output in ("greeting", "greeting2")


# ======================================================================
# SECTION 4: V2.0 Semantic (25+ tests)
# ======================================================================


class TestSemanticEncoder:
    def test_abc_cannot_instantiate(self):
        with pytest.raises(TypeError):
            SemanticEncoder()

    def test_subclass_must_implement(self):
        class Incomplete(SemanticEncoder):
            pass

        with pytest.raises(TypeError):
            Incomplete()

    def test_subclass_works(self):
        class FakeEncoder(SemanticEncoder):
            def encode(self, texts):
                return [[1.0, 0.0]] * len(texts)

            def encode_single(self, text):
                return [1.0, 0.0]

            @property
            def dimension(self):
                return 2

        enc = FakeEncoder()
        assert enc.dimension == 2
        assert enc.encode_single("test") == [1.0, 0.0]
        assert enc.encode(["a", "b"]) == [[1.0, 0.0], [1.0, 0.0]]


class TestDenseCosineSimilarity:
    def test_identical_vectors(self):
        a = [1.0, 2.0, 3.0]
        b = [1.0, 2.0, 3.0]
        assert abs(dense_cosine_similarity(a, b) - 1.0) < 1e-6

    def test_orthogonal_vectors(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert abs(dense_cosine_similarity(a, b)) < 1e-6

    def test_opposite_vectors(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert abs(dense_cosine_similarity(a, b) - (-1.0)) < 1e-6

    def test_zero_vector(self):
        a = [0.0, 0.0]
        b = [1.0, 1.0]
        assert dense_cosine_similarity(a, b) == 0.0

    def test_both_zero_vectors(self):
        a = [0.0, 0.0]
        b = [0.0, 0.0]
        assert dense_cosine_similarity(a, b) == 0.0

    def test_dimension_mismatch_raises(self):
        with pytest.raises(ValueError):
            dense_cosine_similarity([1.0], [1.0, 2.0])

    def test_high_dimensional(self):
        n = 384
        a = [1.0 / n] * n
        b = [1.0 / n] * n
        assert abs(dense_cosine_similarity(a, b) - 1.0) < 1e-6


class TestHybridMemory:
    def test_add_with_semantic(self):
        mem = HybridMemory()
        vec = FeatureVector(features={"a": 1.0})
        ex = mem.add("hello", "greeting", vec, semantic_vector=[1.0, 0.0])
        assert ex.semantic_vector == [1.0, 0.0]

    def test_add_without_semantic(self):
        mem = HybridMemory()
        vec = FeatureVector(features={"a": 1.0})
        ex = mem.add("hello", "greeting", vec)
        assert ex.semantic_vector is None

    def test_set_semantic_vector(self):
        mem = HybridMemory()
        vec = FeatureVector(features={"a": 1.0})
        ex = mem.add("hello", "greeting", vec)
        result = mem.set_semantic_vector(ex.id, [0.5, 0.5])
        assert result is True
        hybrid = mem.get_hybrid(ex.id)
        assert hybrid.semantic_vector == [0.5, 0.5]

    def test_set_semantic_nonexistent(self):
        mem = HybridMemory()
        result = mem.set_semantic_vector(999, [1.0])
        assert result is False

    def test_has_semantic_vectors_true(self):
        mem = HybridMemory()
        vec = FeatureVector(features={"a": 1.0})
        mem.add("hello", "greeting", vec, semantic_vector=[1.0])
        assert mem.has_semantic_vectors() is True

    def test_has_semantic_vectors_false(self):
        mem = HybridMemory()
        vec = FeatureVector(features={"a": 1.0})
        mem.add("hello", "greeting", vec)
        assert mem.has_semantic_vectors() is False

    def test_remove_cleans_semantic(self):
        mem = HybridMemory()
        vec = FeatureVector(features={"a": 1.0})
        ex = mem.add("hello", "greeting", vec, semantic_vector=[1.0, 0.0])
        mem.remove(ex.id)
        assert mem.get_hybrid(ex.id) is None

    def test_clear_cleans_semantic(self):
        mem = HybridMemory()
        vec = FeatureVector(features={"a": 1.0})
        mem.add("hello", "greeting", vec, semantic_vector=[1.0, 0.0])
        mem.clear()
        assert mem.count() == 0
        assert mem.has_semantic_vectors() is False

    def test_persistence_with_semantic(self):
        mem = HybridMemory()
        vec = FeatureVector(features={"a": 1.0})
        mem.add("hello", "greeting", vec, semantic_vector=[1.0, 0.0])
        path = Path(_tmp_dir()) / "memory.json"
        mem.save(path)

        loaded = HybridMemory.load(path)
        assert loaded.count() == 1
        examples = loaded.get_all_hybrid()
        assert examples[0].semantic_vector == [1.0, 0.0]

    def test_persistence_without_semantic(self):
        mem = HybridMemory()
        vec = FeatureVector(features={"a": 1.0})
        mem.add("hello", "greeting", vec)
        path = Path(_tmp_dir()) / "memory.json"
        mem.save(path)

        loaded = HybridMemory.load(path)
        assert loaded.count() == 1
        examples = loaded.get_all_hybrid()
        assert examples[0].semantic_vector is None

    def test_load_v1_format_backward_compat(self):
        """HybridMemory.load handles old V1 format (no semantic, no usage)."""
        v1_data = {
            "next_id": 1,
            "examples": [
                {
                    "id": 0,
                    "input_text": "hello",
                    "output": "greeting",
                    "vector": {"a": 1.0},
                    "norm": 1.0,
                    "weight": 1.0,
                    "feedback_count": 0,
                    "correct_count": 0,
                    "metadata": {},
                }
            ],
        }
        path = Path(_tmp_dir()) / "memory.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(v1_data), encoding="utf-8")

        loaded = HybridMemory.load(path)
        assert loaded.count() == 1
        ex = loaded.get_all_hybrid()[0]
        assert ex.semantic_vector is None
        assert ex.created_at > 0  # defaulted to now

    def test_get_all_hybrid(self):
        mem = HybridMemory()
        vec = FeatureVector(features={"a": 1.0})
        mem.add("a", "out1", vec, semantic_vector=[1.0, 0.0])
        mem.add("b", "out2", vec)
        result = mem.get_all_hybrid()
        assert len(result) == 2
        assert all(isinstance(ex, HybridExample) for ex in result)

    def test_usage_metadata_initialized(self):
        mem = HybridMemory()
        vec = FeatureVector(features={"a": 1.0})
        ex = mem.add("hello", "greeting", vec)
        hybrid = mem.get_hybrid(ex.id)
        assert hybrid.use_count == 0
        assert hybrid.success_count == 0
        assert hybrid.failure_count == 0
        assert hybrid.created_at > 0


class TestHybridSimilarityLearner:
    def test_without_encoder_fallback_v1(self):
        learner = HybridSimilarityLearner()
        assert learner.has_semantic is False
        _learn(learner, "hello world", "greeting")
        result = learner.predict("hello world")
        assert result.output == "greeting"

    def test_with_encoder_v2_behavior(self):
        class FakeEncoder(SemanticEncoder):
            def encode(self, texts):
                return [[1.0, 0.0]] * len(texts)

            def encode_single(self, text):
                return [1.0, 0.0]

            @property
            def dimension(self):
                return 2

        learner = HybridSimilarityLearner(
            semantic_encoder=FakeEncoder()
        )
        assert learner.has_semantic is True
        _learn(learner, "hello world", "greeting")
        result = learner.predict("hello world")
        assert result.output == "greeting"

    def test_lexical_semantic_weight_normalization(self):
        learner = HybridSimilarityLearner(
            lexical_weight=3.0, semantic_weight=7.0,
        )
        # Normalized: 0.3, 0.7
        assert abs(learner.parameters["lexical_weight"] - 0.3) < 1e-6
        assert abs(learner.parameters["semantic_weight"] - 0.7) < 1e-6

    def test_zero_weights(self):
        learner = HybridSimilarityLearner(
            lexical_weight=0.0, semantic_weight=0.0,
        )
        # Should not crash
        assert learner.parameters["lexical_weight"] == 0.0

    def test_encoder_property(self):
        learner = HybridSimilarityLearner()
        assert learner.encoder is None

    def test_encoder_accessible(self):
        class FakeEncoder(SemanticEncoder):
            def encode(self, texts):
                return [[1.0]] * len(texts)
            def encode_single(self, text):
                return [1.0]
            @property
            def dimension(self):
                return 1

        enc = FakeEncoder()
        learner = HybridSimilarityLearner(semantic_encoder=enc)
        assert learner.encoder is enc

    def test_feedback_adds_correction_with_semantic(self):
        class FakeEncoder(SemanticEncoder):
            def encode(self, texts):
                return [[1.0, 0.0]] * len(texts)
            def encode_single(self, text):
                return [1.0, 0.0]
            @property
            def dimension(self):
                return 2

        learner = HybridSimilarityLearner(
            semantic_encoder=FakeEncoder()
        )
        _learn(learner, "hello world", "wrong")
        learner.feedback(
            "hello world", "wrong", correct=False,
            actual_output="right",
        )
        assert learner.memory.count() == 2

    def test_state_save_load_with_scorer(self):
        cfg = ScorerConfig(quality_weight=0.2, recency_weight=0.1)
        learner = HybridSimilarityLearner(scorer_config=cfg)
        _learn(learner, "hello", "a")
        path = _tmp_dir()
        learner.save_state(path)
        loaded = HybridSimilarityLearner.load_state(path)
        assert loaded.memory.count() == 1

    def test_parameters_has_scorer_info(self):
        cfg = ScorerConfig()
        learner = HybridSimilarityLearner(scorer_config=cfg)
        params = learner.parameters
        assert params["has_scorer"] is True
        assert params["scorer_quality_weight"] == 0.1

    def test_parameters_no_encoder(self):
        learner = HybridSimilarityLearner()
        params = learner.parameters
        assert params["has_semantic_encoder"] is False
        assert params["semantic_dimension"] is None

    def test_parameters_with_encoder(self):
        class FakeEncoder(SemanticEncoder):
            def encode(self, texts):
                return [[1.0, 2.0]] * len(texts)
            def encode_single(self, text):
                return [1.0, 2.0]
            @property
            def dimension(self):
                return 2

        learner = HybridSimilarityLearner(
            semantic_encoder=FakeEncoder()
        )
        params = learner.parameters
        assert params["has_semantic_encoder"] is True
        assert params["semantic_dimension"] == 2

    def test_reset_clears_hybrid_state(self):
        class FakeEncoder(SemanticEncoder):
            def encode(self, texts):
                return [[1.0, 0.0]] * len(texts)
            def encode_single(self, text):
                return [1.0, 0.0]
            @property
            def dimension(self):
                return 2

        learner = HybridSimilarityLearner(
            semantic_encoder=FakeEncoder()
        )
        _learn(learner, "hello", "a")
        _learn(learner, "world", "b")
        learner.reset()
        assert learner.memory.count() == 0

    def test_predict_legacy_returns_prediction(self):
        learner = HybridSimilarityLearner()
        _learn(learner, "hello", "a")
        pred = learner.predict_legacy("hello")
        assert isinstance(pred, Prediction)

    def test_predict_returns_predict_result(self):
        learner = HybridSimilarityLearner()
        _learn(learner, "hello", "a")
        result = learner.predict("hello")
        from core.learner.predict_result import PredictResult
        assert isinstance(result, PredictResult)

    def test_empty_memory_prediction(self):
        learner = HybridSimilarityLearner()
        result = learner.predict("anything")
        assert result.output == ""


# ======================================================================
# SECTION 5: V2.1 Retrieval Scoring (25+ tests)
# ======================================================================


class TestScorerConfig:
    def test_defaults(self):
        cfg = ScorerConfig()
        assert cfg.quality_weight == 0.1
        assert cfg.recency_weight == 0.05
        assert cfg.recency_half_life == 86400.0
        assert cfg.diversity_threshold == 0.9

    def test_custom_values(self):
        cfg = ScorerConfig(
            quality_weight=0.2,
            recency_weight=0.1,
            recency_half_life=43200.0,
            diversity_threshold=0.85,
        )
        assert cfg.quality_weight == 0.2
        assert cfg.recency_weight == 0.1
        assert cfg.recency_half_life == 43200.0
        assert cfg.diversity_threshold == 0.85

    def test_frozen(self):
        cfg = ScorerConfig()
        with pytest.raises(AttributeError):
            cfg.quality_weight = 0.5


class TestQualityScore:
    def _make_example(
        self,
        weight=1.0,
        success_count=0,
        failure_count=0,
    ) -> HybridExample:
        return HybridExample(
            id=0,
            input_text="test",
            output="out",
            lexical_vector=FeatureVector(features={"a": 1.0}),
            weight=weight,
            success_count=success_count,
            failure_count=failure_count,
        )

    def test_untested_example(self):
        ex = self._make_example()
        # success_rate=0.5, weight_norm=0.149
        score = quality_score(ex)
        assert 0.0 < score < 1.0

    def test_high_success_rate(self):
        ex = self._make_example(
            weight=5.0, success_count=10, failure_count=0,
        )
        score = quality_score(ex)
        assert score > 0.8

    def test_low_success_rate(self):
        ex = self._make_example(
            weight=0.3, success_count=1, failure_count=9,
        )
        score = quality_score(ex)
        assert score < 0.4

    def test_range_0_to_1(self):
        ex = self._make_example(
            weight=5.0, success_count=100, failure_count=0,
        )
        score = quality_score(ex)
        assert 0.0 <= score <= 1.0

    def test_zero_weight(self):
        ex = self._make_example(weight=0.3, success_count=5, failure_count=5)
        score = quality_score(ex)
        assert 0.0 <= score <= 1.0


class TestRecencyScore:
    def _make_example(self, last_used_at: float) -> HybridExample:
        return HybridExample(
            id=0,
            input_text="test",
            output="out",
            lexical_vector=FeatureVector(),
            last_used_at=last_used_at,
        )

    def test_just_used(self):
        now = time.time()
        ex = self._make_example(last_used_at=now)
        score = recency_score(ex, now, 86400.0)
        assert score == 1.0

    def test_one_half_life_ago(self):
        now = time.time()
        half_life = 86400.0
        ex = self._make_example(last_used_at=now - half_life)
        score = recency_score(ex, now, half_life)
        assert abs(score - 0.5) < 0.01

    def test_two_half_lives_ago(self):
        now = time.time()
        half_life = 86400.0
        ex = self._make_example(last_used_at=now - 2 * half_life)
        score = recency_score(ex, now, half_life)
        assert abs(score - 0.25) < 0.01

    def test_disabled_half_life(self):
        now = time.time()
        ex = self._make_example(last_used_at=now - 999999)
        score = recency_score(ex, now, 0.0)
        assert score == 1.0

    def test_floor_at_01(self):
        now = time.time()
        ex = self._make_example(last_used_at=now - 99999999)
        score = recency_score(ex, now, 86400.0)
        assert score >= 0.1

    def test_future_timestamp(self):
        now = time.time()
        ex = self._make_example(last_used_at=now + 100)
        score = recency_score(ex, now, 86400.0)
        assert score == 1.0


class TestRetrievalScore:
    def test_zero_relevance_gives_zero(self):
        score = retrieval_score(0.0, 1.0, 1.0, 0.1, 0.05)
        assert score == 0.0

    def test_perfect_quality_recency_bonus(self):
        score = retrieval_score(1.0, 1.0, 1.0, 0.1, 0.05)
        expected = 1.0 * (1.0 + 0.1 + 0.05)
        assert abs(score - expected) < 1e-9

    def test_no_bonus(self):
        score = retrieval_score(0.5, 0.0, 0.0, 0.1, 0.05)
        assert abs(score - 0.5) < 1e-6

    def test_formula_correctness(self):
        rel, q, r = 0.7, 0.8, 0.6
        qw, rw = 0.1, 0.05
        expected = rel * (1.0 + qw * q + rw * r)
        assert abs(retrieval_score(rel, q, r, qw, rw) - expected) < 1e-9

    def test_quality_weight_zero(self):
        score = retrieval_score(1.0, 1.0, 1.0, 0.0, 0.05)
        expected = 1.0 * (1.0 + 0.0 + 0.05)
        assert abs(score - expected) < 1e-9

    def test_recency_weight_zero(self):
        score = retrieval_score(1.0, 1.0, 1.0, 0.1, 0.0)
        expected = 1.0 * (1.0 + 0.1)
        assert abs(score - expected) < 1e-9


class TestDiversifyTopK:
    def test_basic_diversity(self):
        scored = [
            (1, 1.0, 0.0),
            (2, 0.9, 0.95),  # near-dup of 1
            (3, 0.8, 0.0),
        ]
        result = diversify_top_k(scored, k=2, similarity_threshold=0.9)
        ids = [eid for eid, _ in result]
        assert 1 in ids
        assert 3 in ids
        assert 2 not in ids

    def test_no_duplicates(self):
        scored = [
            (1, 1.0, 0.0),
            (2, 0.9, 0.0),
            (3, 0.8, 0.0),
        ]
        result = diversify_top_k(scored, k=3, similarity_threshold=0.9)
        assert len(result) == 3

    def test_max_k(self):
        scored = [(i, 1.0 - i * 0.1, 0.0) for i in range(10)]
        result = diversify_top_k(scored, k=3, similarity_threshold=0.9)
        assert len(result) == 3

    def test_diversity_disabled(self):
        scored = [
            (1, 1.0, 0.99),
            (2, 0.9, 0.99),
        ]
        result = diversify_top_k(scored, k=2, similarity_threshold=1.0)
        assert len(result) == 2

    def test_empty_input(self):
        result = diversify_top_k([], k=5, similarity_threshold=0.9)
        assert result == []

    def test_k_larger_than_input(self):
        scored = [(1, 1.0, 0.0)]
        result = diversify_top_k(scored, k=5, similarity_threshold=0.9)
        assert len(result) == 1

    def test_all_near_duplicates(self):
        scored = [
            (1, 1.0, 0.0),
            (2, 0.9, 0.95),
            (3, 0.8, 0.95),
            (4, 0.7, 0.95),
        ]
        result = diversify_top_k(scored, k=4, similarity_threshold=0.9)
        # Only first survives; rest are duplicates
        assert len(result) == 1


class TestUsageTracking:
    def _make_learner(self):
        return HybridSimilarityLearner()

    def test_record_use(self):
        learner = self._make_learner()
        _learn(learner, "hello", "a")
        ex = learner.memory.get_all_hybrid()[0]
        learner.memory.record_use(ex.id)
        stats = learner.memory.get_usage_stats(ex.id)
        assert stats["use_count"] == 1

    def test_record_success(self):
        learner = self._make_learner()
        _learn(learner, "hello", "a")
        ex = learner.memory.get_all_hybrid()[0]
        learner.memory.record_success(ex.id)
        stats = learner.memory.get_usage_stats(ex.id)
        assert stats["success_count"] == 1

    def test_record_failure(self):
        learner = self._make_learner()
        _learn(learner, "hello", "a")
        ex = learner.memory.get_all_hybrid()[0]
        learner.memory.record_failure(ex.id)
        stats = learner.memory.get_usage_stats(ex.id)
        assert stats["failure_count"] == 1

    def test_usage_stats_nonexistent(self):
        learner = self._make_learner()
        assert learner.memory.get_usage_stats(999) is None

    def test_usage_stats_success_rate(self):
        learner = self._make_learner()
        _learn(learner, "hello", "a")
        ex = learner.memory.get_all_hybrid()[0]
        learner.memory.record_success(ex.id)
        learner.memory.record_success(ex.id)
        learner.memory.record_failure(ex.id)
        stats = learner.memory.get_usage_stats(ex.id)
        assert abs(stats["success_rate"] - 2.0 / 3.0) < 1e-6

    def test_usage_stats_untested_rate(self):
        learner = self._make_learner()
        _learn(learner, "hello", "a")
        ex = learner.memory.get_all_hybrid()[0]
        stats = learner.memory.get_usage_stats(ex.id)
        assert stats["success_rate"] == 0.5

    def test_record_use_nonexistent(self):
        learner = self._make_learner()
        assert learner.memory.record_use(999) is False

    def test_record_success_nonexistent(self):
        learner = self._make_learner()
        assert learner.memory.record_success(999) is False

    def test_record_failure_nonexistent(self):
        learner = self._make_learner()
        assert learner.memory.record_failure(999) is False

    def test_feedback_records_success(self):
        class FakeEncoder(SemanticEncoder):
            def encode(self, texts):
                return [[1.0, 0.0]] * len(texts)
            def encode_single(self, text):
                return [1.0, 0.0]
            @property
            def dimension(self):
                return 2

        cfg = ScorerConfig()
        learner = HybridSimilarityLearner(
            semantic_encoder=FakeEncoder(),
            scorer_config=cfg,
        )
        _learn(learner, "hello", "greeting")
        learner.feedback("hello", "greeting", correct=True)
        ex = learner.memory.get_all_hybrid()[0]
        stats = learner.memory.get_usage_stats(ex.id)
        assert stats["success_count"] >= 1

    def test_feedback_records_failure(self):
        cfg = ScorerConfig()
        learner = HybridSimilarityLearner(scorer_config=cfg)
        _learn(learner, "hello", "greeting")
        learner.feedback("hello", "greeting", correct=False)
        ex = learner.memory.get_all_hybrid()[0]
        stats = learner.memory.get_usage_stats(ex.id)
        assert stats["failure_count"] >= 1

    def test_persistence_preserves_scorer_config(self):
        cfg = ScorerConfig(
            quality_weight=0.15,
            recency_weight=0.08,
            recency_half_life=43200.0,
            diversity_threshold=0.85,
        )
        learner = HybridSimilarityLearner(scorer_config=cfg)
        _learn(learner, "hello", "a")
        path = _tmp_dir()
        learner.save_state(path)
        loaded = HybridSimilarityLearner.load_state(path)
        assert loaded._scorer_config is not None
        assert loaded._scorer_config.quality_weight == 0.15
        assert loaded._scorer_config.recency_weight == 0.08
        assert loaded._scorer_config.recency_half_life == 43200.0
        assert loaded._scorer_config.diversity_threshold == 0.85

    def test_retrieval_scoring_integration(self):
        """V2.1 scorer is applied during predict when configured."""
        cfg = ScorerConfig()
        learner = HybridSimilarityLearner(scorer_config=cfg)
        _learn(learner, "hello world", "greeting")
        _learn(learner, "goodbye moon", "farewell")
        result = learner.predict("hello world")
        assert result.output == "greeting"

    def test_quality_irrelevant_not_ranked_above_relevant(self):
        """A high-quality but irrelevant memory should not beat
        a relevant memory."""
        cfg = ScorerConfig(quality_weight=0.1, recency_weight=0.05)
        learner = HybridSimilarityLearner(scorer_config=cfg)
        _learn(learner, "hello world", "greeting")
        # Give it lots of success
        ex = learner.memory.get_all_hybrid()[0]
        for _ in range(10):
            learner.memory.record_success(ex.id)
        # New irrelevant memory with perfect quality
        _learn(learner, "zzz top", "unrelated")
        result = learner.predict("hello world")
        assert result.output == "greeting"

    def test_low_quality_relevant_still_retrievable(self):
        """A low-quality but relevant memory should still be found."""
        cfg = ScorerConfig(quality_weight=0.1, recency_weight=0.05)
        learner = HybridSimilarityLearner(scorer_config=cfg)
        _learn(learner, "hello world", "greeting")
        # Make quality low
        ex = learner.memory.get_all_hybrid()[0]
        for _ in range(5):
            learner.memory.record_failure(ex.id)
        result = learner.predict("hello world")
        assert result.output == "greeting"

    def test_stale_memory_scored_lower(self):
        """An old memory should score lower than a fresh one."""
        cfg = ScorerConfig(recency_weight=0.1, recency_half_life=1.0)
        learner = HybridSimilarityLearner(scorer_config=cfg)
        _learn(learner, "hello world", "greeting")
        # Make it old
        ex = learner.memory.get_all_hybrid()[0]
        learner.memory._last_used_at[ex.id] = time.time() - 9999
        _learn(learner, "hello world", "greeting2")
        result = learner.predict("hello world")
        # The newer one should win
        assert result.output == "greeting2"

    def test_recent_memory_scored_higher(self):
        """Fresh memories should rank above old ones with same content."""
        cfg = ScorerConfig(recency_weight=0.1, recency_half_life=86400.0)
        learner = HybridSimilarityLearner(scorer_config=cfg)
        _learn(learner, "hello world", "old_label")
        _learn(learner, "hello world", "new_label")
        result = learner.predict("hello world")
        assert result.output == "new_label"

    def test_quality_score_range(self):
        """quality_score always returns [0, 1]."""
        for w in [0.3, 1.0, 3.0, 5.0]:
            for s, f in [(0, 0), (5, 0), (0, 5), (3, 3)]:
                ex = HybridExample(
                    id=0, input_text="t", output="o",
                    lexical_vector=FeatureVector(),
                    weight=w, success_count=s, failure_count=f,
                )
                score = quality_score(ex)
                assert 0.0 <= score <= 1.0, (
                    f"quality_score out of range: {score} "
                    f"for weight={w}, s={s}, f={f}"
                )

    def test_recency_score_range(self):
        """recency_score always returns [0.1, 1.0]."""
        now = time.time()
        for offset in [0, 86400, 86400 * 30, 86400 * 365]:
            ex = HybridExample(
                id=0, input_text="t", output="o",
                lexical_vector=FeatureVector(),
                last_used_at=now - offset,
            )
            score = recency_score(ex, now, 86400.0)
            assert 0.1 <= score <= 1.0, (
                f"recency_score out of range: {score} "
                f"for offset={offset}"
            )

    def test_scorer_config_persistence_via_save_load(self):
        """Save/load roundtrip preserves the scorer config in state."""
        cfg = ScorerConfig(
            quality_weight=0.25,
            recency_weight=0.12,
            diversity_threshold=0.8,
        )
        learner = HybridSimilarityLearner(scorer_config=cfg)
        _learn(learner, "test", "a")
        path = _tmp_dir()
        learner.save_state(path)

        # Verify the scorer.json was written
        scorer_file = Path(path) / "scorer.json"
        assert scorer_file.exists()
        data = json.loads(scorer_file.read_text(encoding="utf-8"))
        assert data["quality_weight"] == 0.25
        assert data["recency_weight"] == 0.12
        assert data["diversity_threshold"] == 0.8
