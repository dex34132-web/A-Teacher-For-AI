"""Unit tests for V2.1 RetrievalScorer, metadata fields, and usage tracking."""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from core.learner.feature_extractor import FeatureVector
from core.learner.hybrid_memory import HybridExample, HybridMemory
from core.learner.retrieval_scorer import (
    ScorerConfig,
    diversify_top_k,
    quality_score,
    recency_score,
    retrieval_score,
)

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _fv(features: list[float] | None = None) -> FeatureVector:
    """Create a FeatureVector for testing."""
    feats = features if features is not None else [0.1]
    norm = sum(f * f for f in feats) ** 0.5
    return FeatureVector(features=feats, norm=norm)


# ---------------------------------------------------------------------------
# HybridExample metadata fields
# ---------------------------------------------------------------------------


class TestHybridExampleMetadata:
    """HybridExample has created_at, last_used_at, use_count, etc."""

    def test_default_metadata_values(self):
        ex = HybridExample(
            id=1,
            input_text="hello",
            output="world",
            lexical_vector=_fv(),
        )
        assert ex.created_at == 0.0
        assert ex.last_used_at == 0.0
        assert ex.use_count == 0
        assert ex.success_count == 0
        assert ex.failure_count == 0

    def test_metadata_can_be_set_explicitly(self):
        now = time.time()
        ex = HybridExample(
            id=1,
            input_text="hello",
            output="world",
            lexical_vector=_fv(),
            created_at=100.0,
            last_used_at=now,
            use_count=5,
            success_count=3,
            failure_count=1,
        )
        assert ex.created_at == 100.0
        assert ex.last_used_at == now
        assert ex.use_count == 5
        assert ex.success_count == 3
        assert ex.failure_count == 1

    def test_success_rate_new_memory(self):
        ex = HybridExample(
            id=1,
            input_text="hello",
            output="world",
            lexical_vector=_fv(),
        )
        assert ex.success_rate == 0.5

    def test_success_rate_all_success(self):
        ex = HybridExample(
            id=1,
            input_text="hello",
            output="world",
            lexical_vector=_fv(),
            success_count=5,
            failure_count=0,
        )
        assert ex.success_rate == 1.0

    def test_success_rate_all_failure(self):
        ex = HybridExample(
            id=1,
            input_text="hello",
            output="world",
            lexical_vector=_fv(),
            success_count=0,
            failure_count=5,
        )
        assert ex.success_rate == 0.0


# ---------------------------------------------------------------------------
# HybridMemory usage tracking
# ---------------------------------------------------------------------------


class TestHybridMemoryUsageTracking:
    """HybridMemory tracks usage via record_use/success/failure."""

    def _add_example(self, mem: HybridMemory) -> HybridExample:
        return mem.add(input_text="hello", output="world", vector=_fv(), weight=1.0)

    def test_record_use_increments_count(self):
        mem = HybridMemory()
        ex = self._add_example(mem)
        mem.record_use(ex.id)
        mem.record_use(ex.id)
        stored = mem.get_hybrid(ex.id)
        assert stored.use_count == 2

    def test_record_use_updates_last_used_at(self):
        mem = HybridMemory()
        ex = self._add_example(mem)
        # After add(), last_used_at is set to time.time()
        before = mem.get_hybrid(ex.id).last_used_at
        assert before > 0
        # After a brief sleep, record_use should update it
        time.sleep(0.01)
        mem.record_use(ex.id)
        after = mem.get_hybrid(ex.id).last_used_at
        assert after >= before

    def test_record_success_increments_count(self):
        mem = HybridMemory()
        ex = self._add_example(mem)
        mem.record_success(ex.id)
        mem.record_success(ex.id)
        stored = mem.get_hybrid(ex.id)
        assert stored.success_count == 2

    def test_record_failure_increments_count(self):
        mem = HybridMemory()
        ex = self._add_example(mem)
        mem.record_failure(ex.id)
        stored = mem.get_hybrid(ex.id)
        assert stored.failure_count == 1

    def test_record_use_nonexistent_id_no_error(self):
        mem = HybridMemory()
        assert mem.record_use(999) is False

    def test_record_success_nonexistent_id_no_error(self):
        mem = HybridMemory()
        assert mem.record_success(999) is False

    def test_record_failure_nonexistent_id_no_error(self):
        mem = HybridMemory()
        assert mem.record_failure(999) is False

    def test_usage_stats(self):
        mem = HybridMemory()
        ex = self._add_example(mem)
        mem.record_use(ex.id)
        mem.record_success(ex.id)
        stats = mem.get_usage_stats(ex.id)
        assert stats is not None
        assert stats["use_count"] == 1
        assert stats["success_count"] == 1
        assert stats["failure_count"] == 0

    def test_usage_stats_nonexistent_id(self):
        mem = HybridMemory()
        assert mem.get_usage_stats(999) is None


# ---------------------------------------------------------------------------
# HybridMemory metadata persistence
# ---------------------------------------------------------------------------


class TestHybridMetadataPersistence:
    """Metadata fields persist through save/load."""

    def test_save_load_preserves_created_at(self):
        mem = HybridMemory()
        ex = mem.add(input_text="hello", output="world", vector=_fv(), weight=1.0)
        with tempfile.TemporaryDirectory() as tmpdir:
            mem.save(Path(tmpdir) / "mem.json")
            loaded = HybridMemory.load(Path(tmpdir) / "mem.json")
        stored = loaded.get_hybrid(ex.id)
        assert stored is not None
        assert stored.created_at == ex.created_at

    def test_save_load_preserves_use_count(self):
        mem = HybridMemory()
        ex = mem.add(input_text="hello", output="world", vector=_fv(), weight=1.0)
        mem.record_use(ex.id)
        mem.record_use(ex.id)
        with tempfile.TemporaryDirectory() as tmpdir:
            mem.save(Path(tmpdir) / "mem.json")
            loaded = HybridMemory.load(Path(tmpdir) / "mem.json")
        stored = loaded.get_hybrid(ex.id)
        assert stored.use_count == 2

    def test_save_load_preserves_success_count(self):
        mem = HybridMemory()
        ex = mem.add(input_text="hello", output="world", vector=_fv(), weight=1.0)
        mem.record_success(ex.id)
        with tempfile.TemporaryDirectory() as tmpdir:
            mem.save(Path(tmpdir) / "mem.json")
            loaded = HybridMemory.load(Path(tmpdir) / "mem.json")
        stored = loaded.get_hybrid(ex.id)
        assert stored.success_count == 1

    def test_save_load_preserves_failure_count(self):
        mem = HybridMemory()
        ex = mem.add(input_text="hello", output="world", vector=_fv(), weight=1.0)
        mem.record_failure(ex.id)
        with tempfile.TemporaryDirectory() as tmpdir:
            mem.save(Path(tmpdir) / "mem.json")
            loaded = HybridMemory.load(Path(tmpdir) / "mem.json")
        stored = loaded.get_hybrid(ex.id)
        assert stored.failure_count == 1

    def test_load_v1_format_has_default_metadata(self):
        """Old V1 files without metadata fields load with defaults."""
        v1_data = {
            "next_id": 1,
            "examples": [
                {
                    "id": 0,
                    "input_text": "hello",
                    "output": "world",
                    "vector": [0.1],
                    "norm": 0.1,
                    "weight": 1.0,
                    "feedback_count": 0,
                    "correct_count": 0,
                    "metadata": {},
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "mem.json"
            p.write_text(json.dumps(v1_data), encoding="utf-8")
            loaded = HybridMemory.load(p)
        stored = loaded.get_hybrid(0)
        assert stored.created_at > 0  # defaults to current time on load
        assert stored.use_count == 0
        assert stored.success_count == 0
        assert stored.failure_count == 0


# ---------------------------------------------------------------------------
# RetrievalScorer
# ---------------------------------------------------------------------------


class TestQualityScore:
    """Quality scoring based on success/failure/weight."""

    def test_new_memory_neutral_quality(self):
        ex = HybridExample(
            id=1,
            input_text="hello",
            output="world",
            lexical_vector=_fv(),
            weight=1.0,
        )
        q = quality_score(ex)
        # Neutral success rate (0.5) + normalized weight (1.0/5.0=0.2)
        # = 0.5*0.6 + 0.2*0.4 = 0.3 + 0.08 = 0.38
        assert 0.3 <= q <= 0.5

    def test_successful_memory_higher_quality(self):
        ex = HybridExample(
            id=1,
            input_text="hello",
            output="world",
            lexical_vector=_fv(),
            weight=1.0,
            success_count=5,
            failure_count=0,
        )
        q = quality_score(ex)
        # success_rate=1.0, normalized_weight=0.2
        assert q > 0.6

    def test_failing_memory_lower_quality(self):
        ex = HybridExample(
            id=1,
            input_text="hello",
            output="world",
            lexical_vector=_fv(),
            weight=1.0,
            success_count=0,
            failure_count=5,
        )
        q = quality_score(ex)
        # success_rate=0.0
        assert q < 0.2

    def test_high_weight_increases_quality(self):
        ex_high = HybridExample(
            id=1,
            input_text="hello",
            output="world",
            lexical_vector=_fv(),
            weight=5.0,
            success_count=3,
            failure_count=1,
        )
        ex_low = HybridExample(
            id=2,
            input_text="hello",
            output="world",
            lexical_vector=_fv(),
            weight=0.3,
            success_count=3,
            failure_count=1,
        )
        assert quality_score(ex_high) > quality_score(ex_low)

    def test_quality_range_bounded(self):
        ex = HybridExample(
            id=1,
            input_text="hello",
            output="world",
            lexical_vector=_fv(),
            weight=10.0,
            success_count=100,
            failure_count=0,
        )
        q = quality_score(ex)
        assert 0.0 <= q <= 1.0


class TestRecencyScore:
    """Recency scoring with exponential decay."""

    def test_just_used_has_high_recency(self):
        ex = HybridExample(
            id=1,
            input_text="hello",
            output="world",
            lexical_vector=_fv(),
            weight=1.0,
            last_used_at=time.time(),
        )
        r = recency_score(ex, time.time(), half_life=86400)
        assert r > 0.9

    def test_never_used_has_floor_recency(self):
        ex = HybridExample(
            id=1,
            input_text="hello",
            output="world",
            lexical_vector=_fv(),
            weight=1.0,
            last_used_at=0.0,
        )
        r = recency_score(ex, time.time(), half_life=86400)
        assert r == 0.1

    def test_old_memory_decays(self):
        now = time.time()
        ex = HybridExample(
            id=1,
            input_text="hello",
            output="world",
            lexical_vector=_fv(),
            weight=1.0,
            last_used_at=now - 86400 * 7,  # 7 days ago
        )
        r = recency_score(ex, now, half_life=86400)
        # 7 half-lives = 0.5^7 = 0.0078, but floor at 0.1
        assert 0.1 <= r < 0.5

    def test_recency_disabled_returns_one(self):
        ex = HybridExample(
            id=1,
            input_text="hello",
            output="world",
            lexical_vector=_fv(),
            weight=1.0,
            last_used_at=0.0,
        )
        r = recency_score(ex, time.time(), half_life=0)
        assert r == 1.0

    def test_recency_range_bounded(self):
        ex = HybridExample(
            id=1,
            input_text="hello",
            output="world",
            lexical_vector=_fv(),
            weight=1.0,
            last_used_at=time.time() - 1,
        )
        r = recency_score(ex, time.time(), half_life=1.0)
        assert 0.1 <= r <= 1.0


class TestRetrievalScore:
    """Retrieval score combines relevance, quality, and recency."""

    def test_high_relevance_high_quality(self):
        s = retrieval_score(0.9, 0.8, 0.9, quality_weight=0.1, recency_weight=0.05)
        # 0.9 * (1 + 0.1*0.8 + 0.05*0.9) = 0.9 * 1.085 = 0.9765
        assert s > 0.9

    def test_low_relevance_high_quality(self):
        s = retrieval_score(0.1, 1.0, 1.0, quality_weight=0.1, recency_weight=0.05)
        # 0.1 * (1 + 0.1 + 0.05) = 0.115
        assert s < 0.2

    def test_quality_and_recency_are_multiplicative(self):
        s_with = retrieval_score(0.5, 0.8, 0.8, quality_weight=0.1, recency_weight=0.05)
        s_without = retrieval_score(0.5, 0.0, 0.0, quality_weight=0.0, recency_weight=0.0)
        assert s_with > s_without

    def test_score_range_bounded(self):
        # Max possible with high bonus weights
        s_max = retrieval_score(1.0, 1.0, 1.0, quality_weight=0.5, recency_weight=0.2)
        assert s_max == 1.0 * (1.0 + 0.5 + 0.2)  # = 1.7
        assert s_max <= 1.7
        # Zero relevance always gives zero
        s_zero = retrieval_score(0.0, 0.0, 0.0, quality_weight=0.5, recency_weight=0.2)
        assert s_zero == 0.0

    def test_irrelevant_memory_always_zero(self):
        """Quality and recency cannot boost irrelevant memories."""
        s = retrieval_score(0.0, 1.0, 1.0, quality_weight=1.0, recency_weight=1.0)
        assert s == 0.0


class TestDiversifyTopK:
    """Diversity mechanism removes near-duplicates."""

    def test_no_duplicates_all_kept(self):
        items = [(1, 0.9, 0.0), (2, 0.8, 0.0), (3, 0.7, 0.0)]
        result = diversify_top_k(items, k=3, similarity_threshold=0.9)
        assert len(result) == 3

    def test_near_duplicates_removed(self):
        items = [(1, 0.9, 0.0), (2, 0.85, 0.95), (3, 0.8, 0.0)]
        result = diversify_top_k(items, k=3, similarity_threshold=0.9)
        # Item 2 is near-duplicate of item 1 (similarity 0.95 > 0.9)
        result_ids = [idx for idx, _ in result]
        assert 1 in result_ids
        assert 2 not in result_ids  # Removed as near-duplicate
        assert 3 in result_ids

    def test_high_similarity_keeps_all(self):
        items = [(1, 0.9, 0.5), (2, 0.8, 0.5)]
        result = diversify_top_k(items, k=3, similarity_threshold=0.9)
        # Similarity 0.5 < 0.9, so both kept
        assert len(result) == 2

    def test_k_limits_output(self):
        items = [(i, 1.0 - i * 0.1, 0.0) for i in range(10)]
        result = diversify_top_k(items, k=3, similarity_threshold=0.9)
        assert len(result) == 3

    def test_empty_input(self):
        result = diversify_top_k([], k=3, similarity_threshold=0.9)
        assert result == []

    def test_k_zero_returns_empty(self):
        items = [(1, 0.9, 0.0)]
        result = diversify_top_k(items, k=0, similarity_threshold=0.9)
        assert result == []

    def test_diversity_disabled_keeps_all(self):
        items = [(1, 0.9, 0.0), (2, 0.85, 0.99)]
        result = diversify_top_k(items, k=10, similarity_threshold=1.0)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# ScorerConfig
# ---------------------------------------------------------------------------


class TestScorerConfig:
    """ScorerConfig has sensible defaults."""

    def test_default_values(self):
        config = ScorerConfig()
        assert config.quality_weight == 0.1
        assert config.recency_weight == 0.05
        assert config.recency_half_life == 86400.0
        assert config.diversity_threshold == 0.9

    def test_custom_values(self):
        config = ScorerConfig(
            quality_weight=0.2,
            recency_weight=0.1,
            recency_half_life=3600.0,
            diversity_threshold=0.8,
        )
        assert config.quality_weight == 0.2
        assert config.recency_weight == 0.1
        assert config.recency_half_life == 3600.0
        assert config.diversity_threshold == 0.8
