"""Tests for V2.6 experience module.

Covers: Experience creation, validation, conversion, promotion checks.
"""

from __future__ import annotations

from core.routing.v26.experience import (
    Experience,
    ExperienceOutcome,
    is_promotable,
    validate_experience_content,
)
from core.routing.v26.identity import AgentIdentity, ProjectIdentity, SessionIdentity
from core.routing.v26.memory_types import MemoryKind


def _make_agent(agent_id: str = "a1") -> AgentIdentity:
    return AgentIdentity(agent_id=agent_id)


# ---------------------------------------------------------------------------
# Experience creation
# ---------------------------------------------------------------------------


class TestExperience:
    def test_create(self) -> None:
        exp = Experience.create(
            agent=_make_agent(),
            observation="observed something",
            action="took action",
            outcome=ExperienceOutcome.SUCCESS,
        )
        assert exp.experience_id  # auto-generated
        assert exp.observation == "observed something"
        assert exp.action == "took action"
        assert exp.outcome == ExperienceOutcome.SUCCESS
        assert exp.timestamp > 0

    def test_create_with_project_session(self) -> None:
        exp = Experience.create(
            agent=_make_agent(),
            project=ProjectIdentity(project_id="p1"),
            session=SessionIdentity(session_id="s1"),
            observation="test",
        )
        assert exp.project is not None
        assert exp.project.project_id == "p1"
        assert exp.session is not None
        assert exp.session.session_id == "s1"

    def test_to_scope(self) -> None:
        exp = Experience.create(
            agent=_make_agent("a1"),
            project=ProjectIdentity(project_id="p1"),
            session=SessionIdentity(session_id="s1"),
        )
        scope = exp.to_scope()
        assert scope.agent.agent_id == "a1"
        assert scope.project is not None
        assert scope.session is not None

    def test_to_memory_entry(self) -> None:
        exp = Experience.create(
            agent=_make_agent(),
            observation="saw something",
            action="did something",
            outcome=ExperienceOutcome.SUCCESS,
            confidence=0.8,
        )
        entry = exp.to_memory_entry()
        assert entry.kind == MemoryKind.EPISODIC
        assert "Observation: saw something" in entry.content
        assert "Action: did something" in entry.content
        assert "Outcome: SUCCESS" in entry.content
        assert entry.confidence == 0.8
        assert "outcome:success" in entry.tags


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestExperienceValidation:
    def test_valid_experience(self) -> None:
        exp = Experience.create(
            agent=_make_agent(),
            observation="test",
        )
        is_valid, _ = exp.validate()
        assert is_valid

    def test_invalid_no_agent(self) -> None:
        exp = Experience(
            experience_id="e1",
            agent=AgentIdentity(agent_id="__unresolved__"),
        )
        is_valid, _ = exp.validate()
        assert not is_valid

    def test_invalid_no_id(self) -> None:
        exp = Experience(
            experience_id="",
            agent=_make_agent(),
        )
        is_valid, _ = exp.validate()
        assert not is_valid

    def test_invalid_confidence_out_of_range(self) -> None:
        exp = Experience.create(
            agent=_make_agent(),
            confidence=1.5,
        )
        is_valid, _ = exp.validate()
        assert not is_valid

    def test_content_validation_empty(self) -> None:
        exp = Experience.create(agent=_make_agent())
        is_valid, _ = validate_experience_content(exp)
        assert not is_valid

    def test_content_validation_ok(self) -> None:
        exp = Experience.create(
            agent=_make_agent(),
            observation="valid observation",
        )
        is_valid, _ = validate_experience_content(exp)
        assert is_valid

    def test_content_validation_oversized_observation(self) -> None:
        exp = Experience.create(
            agent=_make_agent(),
            observation="x" * 200_000,
        )
        is_valid, _ = validate_experience_content(exp)
        assert not is_valid


# ---------------------------------------------------------------------------
# Promotion check
# ---------------------------------------------------------------------------


class TestPromotionCheck:
    def test_success_experience_promotable(self) -> None:
        exp = Experience.create(
            agent=_make_agent(),
            observation="observed success",
            outcome=ExperienceOutcome.SUCCESS,
            confidence=0.8,
        )
        promotable, _ = is_promotable(exp)
        assert promotable

    def test_failure_experience_promotable(self) -> None:
        exp = Experience.create(
            agent=_make_agent(),
            observation="observed failure",
            outcome=ExperienceOutcome.FAILURE,
            confidence=0.6,
        )
        promotable, _ = is_promotable(exp)
        assert promotable

    def test_neutral_not_promotable(self) -> None:
        exp = Experience.create(
            agent=_make_agent(),
            observation="neutral observation",
            outcome=ExperienceOutcome.NEUTRAL,
        )
        promotable, _ = is_promotable(exp)
        assert not promotable

    def test_mixed_not_promotable(self) -> None:
        exp = Experience.create(
            agent=_make_agent(),
            observation="mixed",
            outcome=ExperienceOutcome.MIXED,
        )
        promotable, _ = is_promotable(exp)
        assert not promotable

    def test_low_confidence_not_promotable(self) -> None:
        exp = Experience.create(
            agent=_make_agent(),
            observation="test",
            outcome=ExperienceOutcome.SUCCESS,
            confidence=0.1,
        )
        promotable, _ = is_promotable(exp)
        assert not promotable


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


class TestExperienceSerialization:
    def test_to_dict_roundtrip(self) -> None:
        exp = Experience.create(
            agent=_make_agent("a1"),
            project=ProjectIdentity(project_id="p1"),
            observation="test observation",
            action="test action",
            outcome=ExperienceOutcome.SUCCESS,
            confidence=0.9,
            tags=frozenset({"tag1"}),
            metadata={"key": "value"},
        )
        d = exp.to_dict()
        restored = Experience.from_dict(d)
        assert restored.agent.agent_id == "a1"
        assert restored.observation == "test observation"
        assert restored.action == "test action"
        assert restored.outcome == ExperienceOutcome.SUCCESS
        assert restored.confidence == 0.9
        assert "tag1" in restored.tags

    def test_from_dict_defaults(self) -> None:
        d: dict = {"experience_id": "e1", "agent": {"agent_id": "a1"}}
        exp = Experience.from_dict(d)
        assert exp.outcome == ExperienceOutcome.NEUTRAL
        assert exp.confidence == 0.5
