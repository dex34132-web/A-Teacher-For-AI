"""Tests for V2.6 consolidation module.

Covers: consolidate_experiences, should_consolidate, aggregation, merging.
"""

from __future__ import annotations

from core.routing.v26.consolidation import (
    consolidate_experiences,
    should_consolidate,
)
from core.routing.v26.experience import Experience, ExperienceOutcome
from core.routing.v26.identity import AgentIdentity, MemoryScope
from core.routing.v26.memory_types import MemoryKind


def _make_agent(agent_id: str = "a1") -> AgentIdentity:
    return AgentIdentity(agent_id=agent_id)


def _make_experience(
    agent_id: str = "a1",
    observation: str = "obs",
    outcome: ExperienceOutcome = ExperienceOutcome.SUCCESS,
    confidence: float = 0.8,
    timestamp: float = 1000.0,
) -> Experience:
    return Experience.create(
        agent=_make_agent(agent_id),
        observation=observation,
        outcome=outcome,
        confidence=confidence,
        timestamp=timestamp,
    )


# ---------------------------------------------------------------------------
# Empty / minimal
# ---------------------------------------------------------------------------


class TestConsolidationEmpty:
    def test_empty_input(self) -> None:
        result = consolidate_experiences([])
        assert result.promoted_count == 0
        assert result.retained_count == 0
        assert result.discarded_count == 0


# ---------------------------------------------------------------------------
# Promotion
# ---------------------------------------------------------------------------


class TestConsolidationPromotion:
    def test_promotes_group_of_successes(self) -> None:
        experiences = [
            _make_experience(observation=f"obs {i}", timestamp=1000.0 + i)
            for i in range(3)
        ]
        result = consolidate_experiences(experiences)
        assert result.promoted_count == 1
        promoted = result.promoted[0]
        assert promoted.kind == MemoryKind.LEARNED
        assert "consolidated" in promoted.tags
        assert "outcome:success" in promoted.tags

    def test_promotes_group_of_failures(self) -> None:
        experiences = [
            _make_experience(
                observation=f"fail {i}",
                outcome=ExperienceOutcome.FAILURE,
                timestamp=1000.0 + i,
            )
            for i in range(3)
        ]
        result = consolidate_experiences(experiences)
        assert result.promoted_count == 1
        assert "outcome:failure" in result.promoted[0].tags

    def test_retains_single_experience(self) -> None:
        experiences = [_make_experience()]
        result = consolidate_experiences(experiences)
        assert result.promoted_count == 0
        assert result.retained_count == 1

    def test_retains_neutral_experiences(self) -> None:
        experiences = [
            _make_experience(outcome=ExperienceOutcome.NEUTRAL, timestamp=float(i))
            for i in range(5)
        ]
        result = consolidate_experiences(experiences)
        assert result.promoted_count == 0
        assert result.retained_count == 5


# ---------------------------------------------------------------------------
# Merging
# ---------------------------------------------------------------------------


class TestConsolidationMerging:
    def test_merges_content(self) -> None:
        experiences = [
            _make_experience(observation="observed A", timestamp=1000.0),
            _make_experience(observation="observed B", timestamp=1001.0),
            _make_experience(observation="observed C", timestamp=1002.0),
        ]
        result = consolidate_experiences(experiences)
        assert result.promoted_count == 1
        content = result.promoted[0].content
        assert "observed A" in content
        assert "observed B" in content

    def test_merges_tags(self) -> None:
        experiences = [
            _make_experience(timestamp=1000.0),
            _make_experience(timestamp=1001.0),
            _make_experience(timestamp=1002.0),
        ]
        # Add different tags
        exps_with_tags = []
        for i, e in enumerate(experiences):
            exp_with_tag = Experience(
                experience_id=e.experience_id,
                agent=e.agent,
                timestamp=e.timestamp,
                observation=e.observation,
                outcome=e.outcome,
                confidence=e.confidence,
                tags=frozenset({f"extra{i}"}),
            )
            exps_with_tags.append(exp_with_tag)
        result = consolidate_experiences(exps_with_tags)
        assert result.promoted_count == 1
        tags = result.promoted[0].tags
        assert "extra0" in tags
        assert "extra1" in tags


# ---------------------------------------------------------------------------
# Scope isolation
# ---------------------------------------------------------------------------


class TestConsolidationScope:
    def test_groups_by_scope(self) -> None:
        experiences = [
            _make_experience(agent_id="a1", timestamp=1000.0),
            _make_experience(agent_id="a1", timestamp=1001.0),
            _make_experience(agent_id="a1", timestamp=1002.0),
            _make_experience(agent_id="a2", timestamp=1000.0),
            _make_experience(agent_id="a2", timestamp=1001.0),
            _make_experience(agent_id="a2", timestamp=1002.0),
        ]
        result = consolidate_experiences(experiences)
        # Two groups of 3 successes each → 2 promoted
        assert result.promoted_count == 2

    def test_scope_filter(self) -> None:
        experiences = [
            _make_experience(agent_id="a1", timestamp=1000.0),
            _make_experience(agent_id="a1", timestamp=1001.0),
            _make_experience(agent_id="a1", timestamp=1002.0),
            _make_experience(agent_id="a2", timestamp=1000.0),
            _make_experience(agent_id="a2", timestamp=1001.0),
            _make_experience(agent_id="a2", timestamp=1002.0),
        ]
        scope = MemoryScope(agent=AgentIdentity(agent_id="a1"))
        result = consolidate_experiences(experiences, scope=scope)
        assert result.promoted_count == 1
        assert result.promoted[0].scope.agent.agent_id == "a1"


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestConsolidationDeterminism:
    def test_same_input_same_output(self) -> None:
        experiences = [
            _make_experience(observation=f"obs {i}", timestamp=1000.0 + i)
            for i in range(5)
        ]
        r1 = consolidate_experiences(experiences)
        r2 = consolidate_experiences(experiences)
        assert r1.promoted_count == r2.promoted_count
        assert r1.retained_count == r2.retained_count

    def test_sorted_by_timestamp(self) -> None:
        experiences = [
            _make_experience(timestamp=1002.0),
            _make_experience(timestamp=1000.0),
            _make_experience(timestamp=1001.0),
        ]
        result = consolidate_experiences(experiences)
        # Should sort by timestamp, still group as 3 successes
        assert result.promoted_count == 1


# ---------------------------------------------------------------------------
# should_consolidate
# ---------------------------------------------------------------------------


class TestShouldConsolidate:
    def test_empty_not_needed(self) -> None:
        assert not should_consolidate([])

    def test_few_experiences_not_needed(self) -> None:
        exps = [_make_experience(timestamp=float(i)) for i in range(3)]
        assert not should_consolidate(exps)

    def test_many_same_outcome_triggers(self) -> None:
        exps = [
            _make_experience(outcome=ExperienceOutcome.SUCCESS, timestamp=float(i))
            for i in range(6)
        ]
        assert should_consolidate(exps)

    def test_time_span_triggers(self) -> None:
        exps = [
            _make_experience(timestamp=1000.0),
            _make_experience(timestamp=8200.0),  # 2 hours later
        ]
        assert should_consolidate(exps)

    def test_count_over_10_triggers(self) -> None:
        exps = [_make_experience(timestamp=float(i)) for i in range(15)]
        assert should_consolidate(exps)


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


class TestConsolidationProvenance:
    def test_provenance_preserved(self) -> None:
        experiences = [
            _make_experience(observation=f"obs {i}", timestamp=1000.0 + i)
            for i in range(3)
        ]
        result = consolidate_experiences(experiences)
        assert result.promoted_count == 1
        mid = result.promoted[0].memory_id
        assert mid in result.provenance
        assert len(result.provenance[mid]) == 3


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


class TestConsolidationSerialization:
    def test_to_dict(self) -> None:
        experiences = [
            _make_experience(observation="obs", timestamp=1000.0),
            _make_experience(observation="obs2", timestamp=1001.0),
        ]
        result = consolidate_experiences(experiences)
        d = result.to_dict()
        assert "promoted" in d
        assert "retained" in d
        assert "discarded" in d
        assert "provenance" in d
