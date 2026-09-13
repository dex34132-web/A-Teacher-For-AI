"""Tests for KnowledgeExtractionTool."""
from core.routing.v26.memory_manager import MemoryManager
from core.routing.v26.tools.knowledge import KnowledgeExtractionTool


def _make_tool():
    manager = MemoryManager()
    return KnowledgeExtractionTool(manager)


def test_knowledge_tool_name():
    tool = _make_tool()
    assert tool.name == "lerev_knowledge"


def test_knowledge_tool_schema():
    tool = _make_tool()
    schema = tool.schema
    assert schema["type"] == "object"


def test_knowledge_tool_execute_returns_structure():
    tool = _make_tool()
    result = tool.execute()
    assert result.success is True
    assert "promoted_count" in result.data
    assert "retained_count" in result.data
    assert "discarded_count" in result.data
    assert "promoted" in result.data
    assert "provenance" in result.data


def test_knowledge_tool_execute_empty_experiences():
    tool = _make_tool()
    result = tool.execute()
    assert result.success is True
    assert result.data["promoted_count"] == 0
    assert result.data["retained_count"] == 0


def test_knowledge_tool_execute_with_agent_id():
    tool = _make_tool()
    result = tool.execute(agent_id="agent_42")
    assert result.success is True


def test_knowledge_tool_returns_metadata():
    tool = _make_tool()
    result = tool.execute()
    assert result.metadata.get("tool") == "lerev_knowledge"
