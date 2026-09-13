"""Tests for ConflictDetectionTool."""
from core.routing.v26.identity import AgentIdentity
from core.routing.v26.memory_manager import MemoryManager
from core.routing.v26.memory_types import MemoryEntry, MemoryKind, MemoryScope
from core.routing.v26.tools.conflict import ConflictDetectionTool


def _make_tool_with_memory():
    manager = MemoryManager()
    agent = AgentIdentity.create(agent_id="test_agent")
    scope = MemoryScope(agent=agent)
    entry = MemoryEntry(
        memory_id="mem_001",
        content="Python is dynamically typed",
        kind=MemoryKind.EPISODIC,
        scope=scope,
        timestamp=1000.0,
        confidence=0.9,
    )
    manager.store_memory(entry)
    return ConflictDetectionTool(manager)


def test_conflict_tool_name():
    tool = _make_tool_with_memory()
    assert tool.name == "lerev_conflict"


def test_conflict_tool_schema_has_content():
    tool = _make_tool_with_memory()
    schema = tool.schema
    assert "content" in schema["properties"]
    assert "content" in schema["required"]


def test_conflict_tool_validate_requires_content():
    tool = _make_tool_with_memory()
    errors = tool.validate()
    assert len(errors) > 0


def test_conflict_tool_validate_with_content():
    tool = _make_tool_with_memory()
    errors = tool.validate(content="test content")
    assert errors == []


def test_conflict_tool_execute_returns_structure():
    tool = _make_tool_with_memory()
    result = tool.execute(content="Python is statically typed")
    assert result.success is True
    assert "has_conflicts" in result.data
    assert "conflict_count" in result.data
    assert "conflicts" in result.data
    assert "similar_memories_count" in result.data


def test_conflict_tool_execute_empty_store():
    manager = MemoryManager()
    tool = ConflictDetectionTool(manager)
    result = tool.execute(content="something new")
    assert result.success is True
    assert result.data["has_conflicts"] is False


def test_conflict_tool_returns_metadata():
    tool = _make_tool_with_memory()
    result = tool.execute(content="test")
    assert result.metadata.get("tool") == "lerev_conflict"
