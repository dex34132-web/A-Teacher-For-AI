"""Calibration dataset for V2.3.2.

Provides labeled test cases across all required categories:
A. High-confidence correct cases
B. High-similarity but unreliable cases
C. Low-evidence cases
D. Contradictory cases
E. Strong consensus cases
F. Noisy-memory cases
G. Recency cases
H. Feedback cases
I. Distribution-shift cases
J. Persistence cases
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.learner.calibration.metrics import CalibrationCase


@dataclass
class TrainingScenario:
    """What to train the learner on before testing."""
    examples: list[tuple[str, str]] = field(default_factory=list)
    feedback: list[tuple[str, str, bool]] = field(default_factory=list)  # (query, output, correct)


@dataclass
class CalibrationScenario:
    """A complete test scenario with training setup and labeled predictions."""
    name: str
    category: str
    description: str
    training: TrainingScenario
    test_cases: list[CalibrationCase]
    expected_brier_max: float = 0.5
    expected_ece_max: float = 0.5


# ---------------------------------------------------------------------------
# A. High-confidence correct cases
# ---------------------------------------------------------------------------

def _build_high_confidence_cases() -> CalibrationScenario:
    training = TrainingScenario(
        examples=[
            ("sort a list", "sorted(x)"),
            ("sort an array", "sorted(x)"),
            ("sort items", "sorted(x)"),
            ("sort data", "sorted(x)"),
            ("sort elements", "sorted(x)"),
            ("sort numbers", "sorted(x)"),
            ("sort strings", "sorted(x)"),
            ("order list", "sorted(x)"),
            ("order items", "sorted(x)"),
            ("rank items", "sorted(x)"),
        ],
        feedback=[
            ("sort a list", "sorted(x)", True),
            ("sort a list", "sorted(x)", True),
            ("sort a list", "sorted(x)", True),
            ("sort a list", "sorted(x)", True),
            ("sort a list", "sorted(x)", True),
            ("sort an array", "sorted(x)", True),
            ("sort an array", "sorted(x)", True),
            ("sort an array", "sorted(x)", True),
            ("sort items", "sorted(x)", True),
            ("sort items", "sorted(x)", True),
        ],
    )
    return CalibrationScenario(
        name="high_confidence_correct",
        category="A",
        description="High similarity, strong evidence, no conflict",
        training=training,
        test_cases=[
            CalibrationCase(
                query="sort a list", expected="sorted(x)",
                confidence=0.0, predicted="sorted(x)", correct=True,
            ),
            CalibrationCase(
                query="sort an array", expected="sorted(x)",
                confidence=0.0, predicted="sorted(x)", correct=True,
            ),
            CalibrationCase(
                query="sort items", expected="sorted(x)",
                confidence=0.0, predicted="sorted(x)", correct=True,
            ),
        ],
        expected_brier_max=0.15,
        expected_ece_max=0.15,
    )


# ---------------------------------------------------------------------------
# B. High-similarity but unreliable cases
# ---------------------------------------------------------------------------

def _build_unreliable_cases() -> CalibrationScenario:
    training = TrainingScenario(
        examples=[
            ("sort a list", "sorted(x)"),
            ("sort a list", "list.sort()"),  # Conflicting
            ("sort an array", "sorted(x)"),
            ("sort items", "sorted(x)"),
            ("reverse a string", "s[::-1]"),
            ("find max", "max(x)"),
            ("join strings", "joined"),
            ("check membership", "x in y"),
        ],
        feedback=[
            ("sort a list", "sorted(x)", True),
            ("sort a list", "sorted(x)", True),
            ("sort a list", "list.sort()", False),
            ("sort a list", "list.sort()", False),
        ],
    )
    return CalibrationScenario(
        name="high_sim_unreliable",
        category="B",
        description="High similarity but weak/conflicting evidence",
        training=training,
        test_cases=[
            # sort a list has conflicting evidence, confidence should be moderate
            CalibrationCase(
                query="sort a list", expected="sorted(x)",
                confidence=0.0, predicted="sorted(x)", correct=True,
            ),
            # Other queries have clear evidence
            CalibrationCase(
                query="reverse a string", expected="s[::-1]",
                confidence=0.0, predicted="s[::-1]", correct=True,
            ),
            CalibrationCase(
                query="find max", expected="max(x)",
                confidence=0.0, predicted="max(x)", correct=True,
            ),
        ],
        expected_brier_max=0.35,
        expected_ece_max=0.35,
    )


# ---------------------------------------------------------------------------
# C. Low-evidence cases
# ---------------------------------------------------------------------------

def _build_low_evidence_cases() -> CalibrationScenario:
    training = TrainingScenario(
        examples=[
            ("sort a list", "sorted(x)"),
            ("reverse a string", "s[::-1]"),
            ("find max", "max(x)"),
        ],
        feedback=[],  # No feedback at all
    )
    return CalibrationScenario(
        name="low_evidence",
        category="C",
        description="Few memories, no feedback, novel queries",
        training=training,
        test_cases=[
            # Known query, no evidence → low confidence
            CalibrationCase(
                query="sort a list", expected="sorted(x)",
                confidence=0.0, predicted="sorted(x)", correct=True,
            ),
            # Novel query, low similarity → very low confidence
            CalibrationCase(
                query="parse JSON", expected="json.loads(x)",
                confidence=0.0, predicted="", correct=False,
            ),
            # Another novel query
            CalibrationCase(
                query="read CSV", expected="csv.reader(x)",
                confidence=0.0, predicted="", correct=False,
            ),
        ],
        expected_brier_max=0.45,
        expected_ece_max=0.45,
    )


# ---------------------------------------------------------------------------
# D. Contradictory cases
# ---------------------------------------------------------------------------

def _build_contradictory_cases() -> CalibrationScenario:
    training = TrainingScenario(
        examples=[
            ("sort a list", "sorted(x)"),
            ("sort a list", "list.sort()"),
            ("sort a list", "sorted(x)"),  # Duplicate for voting
            ("sort a list", "list.sort()"),  # Duplicate for voting
            ("reverse a string", "s[::-1]"),
            ("find max", "max(x)"),
        ],
        feedback=[
            ("sort a list", "sorted(x)", True),
            ("sort a list", "sorted(x)", True),
            ("sort a list", "list.sort()", True),
            ("sort a list", "list.sort()", True),
        ],
    )
    return CalibrationScenario(
        name="contradictory",
        category="D",
        description="Multiple relevant memories disagree",
        training=training,
        test_cases=[
            # sort a list has 50/50 split → low confidence
            CalibrationCase(
                query="sort a list", expected="sorted(x)",
                confidence=0.0, predicted="sorted(x)", correct=True,
            ),
            # Other queries are clear
            CalibrationCase(
                query="reverse a string", expected="s[::-1]",
                confidence=0.0, predicted="s[::-1]", correct=True,
            ),
            CalibrationCase(
                query="find max", expected="max(x)",
                confidence=0.0, predicted="max(x)", correct=True,
            ),
        ],
        expected_brier_max=0.40,
        expected_ece_max=0.40,
    )


# ---------------------------------------------------------------------------
# E. Strong consensus cases
# ---------------------------------------------------------------------------

def _build_consensus_cases() -> CalibrationScenario:
    training = TrainingScenario(
        examples=[
            ("sort a list", "sorted(x)"),
            ("sort a list", "sorted(x)"),
            ("sort a list", "sorted(x)"),
            ("sort a list", "sorted(x)"),
            ("sort a list", "sorted(x)"),
            ("sort a list", "sorted(x)"),
            ("sort a list", "sorted(x)"),
            ("sort a list", "sorted(x)"),
            ("reverse a string", "s[::-1]"),
            ("find max", "max(x)"),
        ],
        feedback=[
            ("sort a list", "sorted(x)", True),
            ("sort a list", "sorted(x)", True),
            ("sort a list", "sorted(x)", True),
            ("sort a list", "sorted(x)", True),
            ("sort a list", "sorted(x)", True),
            ("sort a list", "sorted(x)", True),
            ("sort a list", "sorted(x)", True),
            ("sort a list", "sorted(x)", True),
        ],
    )
    return CalibrationScenario(
        name="strong_consensus",
        category="E",
        description="Many independent memories support same answer",
        training=training,
        test_cases=[
            CalibrationCase(
                query="sort a list", expected="sorted(x)",
                confidence=0.0, predicted="sorted(x)", correct=True,
            ),
            CalibrationCase(
                query="reverse a string", expected="s[::-1]",
                confidence=0.0, predicted="s[::-1]", correct=True,
            ),
        ],
        expected_brier_max=0.10,
        expected_ece_max=0.10,
    )


# ---------------------------------------------------------------------------
# F. Noisy-memory cases
# ---------------------------------------------------------------------------

def _build_noisy_cases() -> CalibrationScenario:
    training = TrainingScenario(
        examples=[
            ("sort a list", "sorted(x)"),
            ("cook dinner", "recipe"),
            ("drive car", "steering"),
            ("play music", "instrument"),
            ("paint picture", "brush"),
            ("write book", "pen"),
            ("build house", "hammer"),
            ("fly airplane", "pilot"),
            ("sail boat", "wind"),
            ("swim pool", "water"),
        ],
        feedback=[
            ("cook dinner", "recipe", True),
            ("cook dinner", "recipe", True),
            ("cook dinner", "recipe", True),
            ("drive car", "steering", True),
            ("drive car", "steering", True),
            ("play music", "instrument", True),
        ],
    )
    return CalibrationScenario(
        name="noisy_memories",
        category="F",
        description="Irrelevant, low-quality memories present",
        training=training,
        test_cases=[
            # sort a list has one good memory among noise
            CalibrationCase(
                query="sort a list", expected="sorted(x)",
                confidence=0.0, predicted="sorted(x)", correct=True,
            ),
            # Unrelated query should get low confidence
            CalibrationCase(
                query="bake cake", expected="recipe",
                confidence=0.0, predicted="", correct=False,
            ),
        ],
        expected_brier_max=0.40,
        expected_ece_max=0.40,
    )


# ---------------------------------------------------------------------------
# G. Recency cases
# ---------------------------------------------------------------------------

def _build_recency_cases() -> CalibrationScenario:
    training = TrainingScenario(
        examples=[
            ("sort a list", "sorted(x)"),
            ("sort a list", "list.sort()"),
            ("reverse a string", "s[::-1]"),
            ("find max", "max(x)"),
        ],
        feedback=[
            # sort a list: old correct, recent correct
            ("sort a list", "sorted(x)", True),
            ("sort a list", "sorted(x)", True),
            ("sort a list", "sorted(x)", True),
            ("sort a list", "sorted(x)", True),
            ("sort a list", "sorted(x)", True),
            # reverse: old correct
            ("reverse a string", "s[::-1]", True),
            ("reverse a string", "s[::-1]", True),
        ],
    )
    return CalibrationScenario(
        name="recency",
        category="G",
        description="Fresh vs old knowledge, reliability vs recency",
        training=training,
        test_cases=[
            CalibrationCase(
                query="sort a list", expected="sorted(x)",
                confidence=0.0, predicted="sorted(x)", correct=True,
            ),
            CalibrationCase(
                query="reverse a string", expected="s[::-1]",
                confidence=0.0, predicted="s[::-1]", correct=True,
            ),
            CalibrationCase(
                query="find max", expected="max(x)",
                confidence=0.0, predicted="max(x)", correct=True,
            ),
        ],
        expected_brier_max=0.35,
        expected_ece_max=0.35,
    )


# ---------------------------------------------------------------------------
# H. Feedback cases
# ---------------------------------------------------------------------------

def _build_feedback_cases() -> CalibrationScenario:
    training = TrainingScenario(
        examples=[
            ("sort a list", "sorted(x)"),
            ("sort a list", "list.sort()"),
            ("reverse a string", "s[::-1]"),
            ("find max", "max(x)"),
        ],
        feedback=[
            # sort: mostly correct
            ("sort a list", "sorted(x)", True),
            ("sort a list", "sorted(x)", True),
            ("sort a list", "sorted(x)", True),
            ("sort a list", "sorted(x)", True),
            ("sort a list", "sorted(x)", True),
            ("sort a list", "sorted(x)", True),
            ("sort a list", "sorted(x)", True),
            ("sort a list", "sorted(x)", True),
            # list.sort: mostly wrong
            ("sort a list", "list.sort()", False),
            ("sort a list", "list.sort()", False),
            ("sort a list", "list.sort()", False),
            ("sort a list", "list.sort()", False),
            ("sort a list", "list.sort()", True),
            ("sort a list", "list.sort()", True),
        ],
    )
    return CalibrationScenario(
        name="feedback",
        category="H",
        description="Correct, incorrect, repeated, alternating feedback",
        training=training,
        test_cases=[
            CalibrationCase(
                query="sort a list", expected="sorted(x)",
                confidence=0.0, predicted="sorted(x)", correct=True,
            ),
            CalibrationCase(
                query="reverse a string", expected="s[::-1]",
                confidence=0.0, predicted="s[::-1]", correct=True,
            ),
        ],
        expected_brier_max=0.30,
        expected_ece_max=0.30,
    )


# ---------------------------------------------------------------------------
# I. Distribution-shift cases
# ---------------------------------------------------------------------------

def _build_distribution_shift_cases() -> CalibrationScenario:
    training = TrainingScenario(
        examples=[
            ("sort a list of integers", "sorted(x)"),
            ("sort an array of numbers", "sorted(x)"),
            ("sort items in a list", "sorted(x)"),
            ("reverse a text string", "s[::-1]"),
            ("reverse characters in string", "s[::-1]"),
            ("find the maximum value", "max(x)"),
            ("get the largest number", "max(x)"),
        ],
        feedback=[
            ("sort a list of integers", "sorted(x)", True),
            ("sort a list of integers", "sorted(x)", True),
            ("sort a list of integers", "sorted(x)", True),
            ("sort an array of numbers", "sorted(x)", True),
            ("sort an array of numbers", "sorted(x)", True),
        ],
    )
    return CalibrationScenario(
        name="distribution_shift",
        category="I",
        description="Queries that differ from training distribution",
        training=training,
        test_cases=[
            # Close to training → moderate confidence
            CalibrationCase(
                query="sort integers", expected="sorted(x)",
                confidence=0.0, predicted="sorted(x)", correct=True,
            ),
            # Far from training → low confidence
            CalibrationCase(
                query="arrange numbers ascending", expected="sorted(x)",
                confidence=0.0, predicted="sorted(x)", correct=True,
            ),
            # Very different vocabulary
            CalibrationCase(
                query="order elements numerically", expected="sorted(x)",
                confidence=0.0, predicted="sorted(x)", correct=True,
            ),
        ],
        expected_brier_max=0.45,
        expected_ece_max=0.45,
    )


# ---------------------------------------------------------------------------
# Build complete dataset
# ---------------------------------------------------------------------------

def build_all_scenarios() -> list[CalibrationScenario]:
    """Build all calibration scenarios."""
    return [
        _build_high_confidence_cases(),
        _build_unreliable_cases(),
        _build_low_evidence_cases(),
        _build_contradictory_cases(),
        _build_consensus_cases(),
        _build_noisy_cases(),
        _build_recency_cases(),
        _build_feedback_cases(),
        _build_distribution_shift_cases(),
    ]


def run_scenario(scenario: CalibrationScenario, learner_factory: Any) -> list[CalibrationCase]:
    """Run a calibration scenario and return cases with actual confidence values.

    Args:
        scenario: The scenario to test.
        learner_factory: Callable that returns a fresh learner.

    Returns:
        List of CalibrationCase with actual confidence values filled in.
    """
    learner = learner_factory()

    # Train
    for inp, out in scenario.training.examples:
        from core.learner.base import LearningInput
        learner.learn(LearningInput(observation={"input": inp, "output": out}))

    # Apply feedback
    for inp, out, correct in scenario.training.feedback:
        learner.feedback(inp, out, correct)

    # Test
    results = []
    for case in scenario.test_cases:
        r = learner.predict(case.query)
        results.append(CalibrationCase(
            query=case.query,
            expected=case.expected,
            confidence=r.confidence,
            predicted=r.output,
            correct=r.output == case.expected,
            metadata={
                "similarity": r.similarity,
                "uncertainty_state": r.uncertainty_state,
                "scenario": scenario.name,
            },
        ))
    return results
