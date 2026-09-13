"""Tests for ConfidenceTool."""
from core.routing.v26.tools.confidence import ConfidenceTool


def test_confidence_tool_name():
    tool = ConfidenceTool()
    assert tool.name == "lerev_confidence"


def test_confidence_tool_schema():
    tool = ConfidenceTool()
    schema = tool.schema
    assert schema["type"] == "object"
    assert "properties" in schema


def test_confidence_tool_execute_default():
    tool = ConfidenceTool()
    result = tool.execute()
    assert result.success is True
    assert "confidence" in result.data
    assert "band" in result.data
    assert "uncertainty_state" in result.data
    assert 0.0 <= result.data["confidence"] <= 1.0


def test_confidence_tool_execute_with_params():
    tool = ConfidenceTool()
    result = tool.execute(
        similarity=0.8,
        success_count=5,
        failure_count=1,
        supporting_weight=3.0,
        total_weight=4.0,
        supporting_count=3,
        total_count=4,
        outputs=["a", "a", "a", "b"],
    )
    assert result.success is True
    assert result.data["confidence"] > 0.0


def test_confidence_tool_execute_high_similarity():
    tool = ConfidenceTool()
    result = tool.execute(similarity=1.0, success_count=10, failure_count=0)
    assert result.success is True
    assert result.data["confidence"] >= 0.5


def test_confidence_tool_execute_low_similarity():
    tool = ConfidenceTool()
    result = tool.execute(similarity=0.0, success_count=0, failure_count=10)
    assert result.success is True
    assert result.data["confidence"] <= 0.5


def test_confidence_tool_execute_returns_all_fields():
    tool = ConfidenceTool()
    result = tool.execute()
    expected_fields = [
        "confidence", "probability", "band", "similarity",
        "evidence_factor", "agreement_bonus", "conflict_penalty",
        "novelty_penalty", "evidence_strength", "supporting_count",
        "total_count", "conflict_count", "uncertainty_state",
    ]
    for field in expected_fields:
        assert field in result.data, f"Missing field: {field}"


def test_confidence_tool_returns_metadata():
    tool = ConfidenceTool()
    result = tool.execute()
    assert result.metadata.get("tool") == "lerev_confidence"
