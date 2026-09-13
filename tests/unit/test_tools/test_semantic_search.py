"""Tests for SemanticSearchTool."""
from core.learner.feature_extractor import FeatureExtractor
from core.routing.v26.identity import AgentIdentity, MemoryScope
from core.routing.v26.memory_store import MemoryStore
from core.routing.v26.memory_types import MemoryEntry, MemoryKind
from core.routing.v26.tools.semantic_search import SemanticSearchTool


def _make_tool_with_entries():
    store = MemoryStore()
    extractor = FeatureExtractor()
    agent = AgentIdentity.create(agent_id="test_agent")
    scope = MemoryScope(agent=agent)
    for i, text in enumerate(["Python programming", "Java development", "C++ systems"]):
        entry = MemoryEntry(
            memory_id=f"mem_{i:03d}",
            content=text,
            kind=MemoryKind.EPISODIC,
            scope=scope,
            timestamp=float(i),
            confidence=0.8,
        )
        store.store(entry)
        extractor.fit(text)
    return SemanticSearchTool(store, extractor)


def test_semantic_search_tool_name():
    tool = _make_tool_with_entries()
    assert tool.name == "lerev_search"


def test_semantic_search_tool_schema():
    tool = _make_tool_with_entries()
    schema = tool.schema
    assert "query" in schema["properties"]
    assert "query" in schema["required"]


def test_semantic_search_tool_validate_requires_query():
    tool = _make_tool_with_entries()
    errors = tool.validate()
    assert len(errors) > 0


def test_semantic_search_tool_validate_with_query():
    tool = _make_tool_with_entries()
    errors = tool.validate(query="test")
    assert errors == []


def test_semantic_search_tool_execute_returns_results():
    tool = _make_tool_with_entries()
    result = tool.execute(query="Python programming")
    assert result.success is True
    assert "memories" in result.data
    assert "count" in result.data
    assert "query" in result.data


def test_semantic_search_tool_execute_empty_store():
    store = MemoryStore()
    extractor = FeatureExtractor()
    tool = SemanticSearchTool(store, extractor)
    result = tool.execute(query="anything")
    assert result.success is True
    assert result.data["count"] == 0


def test_semantic_search_tool_returns_metadata():
    tool = _make_tool_with_entries()
    result = tool.execute(query="Python")
    assert result.metadata.get("tool") == "lerev_search"
