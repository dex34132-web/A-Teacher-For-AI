"""Tests for DiagnoseTool."""
from core.routing.v26.memory_manager import MemoryManager
from core.routing.v26.tools.diagnose import DiagnoseTool


def _make_tool():
    manager = MemoryManager()
    return DiagnoseTool(manager)


def test_diagnose_tool_name():
    tool = _make_tool()
    assert tool.name == "lerev_diagnose"


def test_diagnose_tool_schema():
    tool = _make_tool()
    schema = tool.schema
    assert schema["type"] == "object"


def test_diagnose_tool_execute_returns_structure():
    tool = _make_tool()
    result = tool.execute()
    assert result.success is True
    assert "health" in result.data
    assert "stats" in result.data
    assert "warnings" in result.data


def test_diagnose_tool_execute_healthy():
    tool = _make_tool()
    result = tool.execute()
    assert result.data["health"] == "healthy"
    assert isinstance(result.data["stats"], dict)
    assert isinstance(result.data["warnings"], list)


def test_diagnose_tool_execute_empty_store_warning():
    tool = _make_tool()
    result = tool.execute()
    assert any("empty" in w.lower() for w in result.data["warnings"])


def test_diagnose_tool_stats_fields():
    tool = _make_tool()
    result = tool.execute()
    stats = result.data["stats"]
    assert "operation_count" in stats
    assert "error_count" in stats
    assert "store_size" in stats
    assert "consolidations" in stats


def test_diagnose_tool_returns_metadata():
    tool = _make_tool()
    result = tool.execute()
    assert result.metadata.get("tool") == "lerev_diagnose"
