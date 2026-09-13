"""Tests for StatusTool."""
from core.routing.v26.tools.status import StatusTool


def test_status_tool_name():
    tool = StatusTool()
    assert tool.name == "lerev_status"


def test_status_tool_description():
    tool = StatusTool()
    assert "health" in tool.description.lower() or "component" in tool.description.lower()


def test_status_tool_schema():
    tool = StatusTool()
    schema = tool.schema
    assert schema["type"] == "object"
    assert "required" in schema


def test_status_tool_execute():
    tool = StatusTool()
    result = tool.execute()
    assert result.success is True
    assert "components" in result.data
    assert "all_ok" in result.data
    assert isinstance(result.data["components"], dict)


def test_status_tool_all_components_present():
    tool = StatusTool()
    result = tool.execute()
    components = result.data["components"]
    expected = [
        "memory_manager",
        "experience",
        "identity",
        "memory_types",
        "memory_store",
        "semantic_retrieval",
        "confidence",
        "feature_extractor",
        "similarity",
        "consolidation",
    ]
    for comp in expected:
        assert comp in components, f"Missing component: {comp}"


def test_status_tool_validate_always_empty():
    tool = StatusTool()
    errors = tool.validate()
    assert errors == []


def test_status_tool_returns_metadata():
    tool = StatusTool()
    result = tool.execute()
    assert result.metadata.get("tool") == "lerev_status"
