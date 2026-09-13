"""Tests for LifecycleTool."""
from core.routing.v26.identity import AgentIdentity
from core.routing.v26.memory_manager import MemoryManager
from core.routing.v26.memory_types import MemoryEntry, MemoryKind, MemoryScope
from core.routing.v26.tools.lifecycle import LifecycleTool


def _make_tool_with_memory():
    manager = MemoryManager()
    agent = AgentIdentity.create(agent_id="test_agent")
    scope = MemoryScope(agent=agent)
    entry = MemoryEntry(
        memory_id="mem_001",
        content="test memory",
        kind=MemoryKind.EPISODIC,
        scope=scope,
        timestamp=1000.0,
        confidence=0.5,
    )
    manager.store_memory(entry)
    return LifecycleTool(manager), manager


def test_lifecycle_tool_name():
    tool, _ = _make_tool_with_memory()
    assert tool.name == "lerev_lifecycle"


def test_lifecycle_tool_schema():
    tool, _ = _make_tool_with_memory()
    schema = tool.schema
    assert "action" in schema["properties"]
    assert "action" in schema["required"]


def test_lifecycle_tool_validate_requires_action():
    tool, _ = _make_tool_with_memory()
    errors = tool.validate()
    assert len(errors) > 0


def test_lifecycle_tool_validate_invalid_action():
    tool, _ = _make_tool_with_memory()
    errors = tool.validate(action="invalid")
    assert len(errors) > 0


def test_lifecycle_tool_validate_requires_memory_id_for_promote():
    tool, _ = _make_tool_with_memory()
    errors = tool.validate(action="promote")
    assert len(errors) > 0
    assert any("memory_id" in e for e in errors)


def test_lifecycle_tool_validate_requires_memory_id_for_archive():
    tool, _ = _make_tool_with_memory()
    errors = tool.validate(action="archive")
    assert len(errors) > 0


def test_lifecycle_tool_execute_score():
    tool, _ = _make_tool_with_memory()
    result = tool.execute(action="score", memory_id="mem_001", amount=0.2)
    assert result.success is True
    assert result.data["action"] == "score"
    assert result.data["new_confidence"] > result.data["old_confidence"]


def test_lifecycle_tool_execute_decay():
    tool, _ = _make_tool_with_memory()
    result = tool.execute(action="decay", memory_id="mem_001", amount=0.1)
    assert result.success is True
    assert result.data["action"] == "decay"
    assert result.data["new_confidence"] < result.data["old_confidence"]


def test_lifecycle_tool_execute_promote():
    tool, _ = _make_tool_with_memory()
    result = tool.execute(action="promote", memory_id="mem_001")
    assert result.success is True
    assert result.data["action"] == "promote"


def test_lifecycle_tool_execute_archive():
    tool, manager = _make_tool_with_memory()
    result = tool.execute(action="archive", memory_id="mem_001")
    assert result.success is True
    assert result.data["action"] == "archive"
    assert result.data["removed"] is True
    assert manager.get_memory("mem_001") is None


def test_lifecycle_tool_execute_score_not_found():
    tool, _ = _make_tool_with_memory()
    result = tool.execute(action="score", memory_id="nonexistent")
    assert result.success is False
    assert len(result.errors) > 0


def test_lifecycle_tool_returns_metadata():
    tool, _ = _make_tool_with_memory()
    result = tool.execute(action="score", memory_id="mem_001")
    assert result.metadata.get("tool") == "lerev_lifecycle"
