"""Tests for RecallTool."""
from core.routing.v26.identity import AgentIdentity
from core.routing.v26.memory_manager import MemoryManager
from core.routing.v26.memory_types import MemoryEntry, MemoryKind, MemoryScope
from core.routing.v26.tools.recall import RecallTool


def _make_tool_with_memories():
    manager = MemoryManager()
    agent = AgentIdentity.create(agent_id="test_agent")
    scope = MemoryScope(agent=agent)
    entry = MemoryEntry(
        memory_id="mem_001",
        content="Python is a programming language",
        kind=MemoryKind.EPISODIC,
        scope=scope,
        timestamp=1000.0,
        confidence=0.9,
    )
    manager.store_memory(entry)
    return RecallTool(manager)


def test_recall_tool_name():
    tool = _make_tool_with_memories()
    assert tool.name == "lerev_recall"


def test_recall_tool_schema_has_query():
    tool = _make_tool_with_memories()
    schema = tool.schema
    assert "query" in schema["properties"]
    assert "query" in schema["required"]


def test_recall_tool_validate_requires_query():
    tool = _make_tool_with_memories()
    errors = tool.validate()
    assert len(errors) > 0
    assert "query" in errors[0]


def test_recall_tool_validate_with_query():
    tool = _make_tool_with_memories()
    errors = tool.validate(query="test query")
    assert errors == []


def test_recall_tool_execute_returns_memories():
    tool = _make_tool_with_memories()
    result = tool.execute(query="Python")
    assert result.success is True
    assert "memories" in result.data
    assert "total" in result.data
    assert "count" in result.data


def test_recall_tool_execute_empty_store():
    manager = MemoryManager()
    tool = RecallTool(manager)
    result = tool.execute(query="anything")
    assert result.success is True
    assert result.data["count"] == 0


def test_recall_tool_execute_with_limit():
    tool = _make_tool_with_memories()
    result = tool.execute(query="Python", limit=5)
    assert result.success is True
    assert result.data["count"] <= 5


def test_recall_tool_returns_metadata():
    tool = _make_tool_with_memories()
    result = tool.execute(query="Python")
    assert result.metadata.get("tool") == "lerev_recall"
