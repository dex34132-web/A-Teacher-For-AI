"""Tests for DeduplicateTool."""
from core.learner.feature_extractor import FeatureExtractor
from core.routing.v26.identity import AgentIdentity, MemoryScope
from core.routing.v26.memory_store import MemoryStore
from core.routing.v26.memory_types import MemoryEntry, MemoryKind
from core.routing.v26.tools.deduplicate import DeduplicateTool


def _make_tool_with_entries():
    store = MemoryStore()
    extractor = FeatureExtractor()
    agent = AgentIdentity.create(agent_id="test_agent")
    scope = MemoryScope(agent=agent)
    texts = [
        "Python is a programming language",
        "Python is a programming language used widely",
        "Java is also a programming language",
    ]
    for i, text in enumerate(texts):
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
    return DeduplicateTool(store, extractor)


def test_deduplicate_tool_name():
    tool = _make_tool_with_entries()
    assert tool.name == "lerev_deduplicate"


def test_deduplicate_tool_schema():
    tool = _make_tool_with_entries()
    schema = tool.schema
    assert "content" in schema["properties"]
    assert "content" in schema["required"]


def test_deduplicate_tool_validate_requires_content():
    tool = _make_tool_with_entries()
    errors = tool.validate()
    assert len(errors) > 0


def test_deduplicate_tool_validate_with_content():
    tool = _make_tool_with_entries()
    errors = tool.validate(content="test")
    assert errors == []


def test_deduplicate_tool_execute_returns_structure():
    tool = _make_tool_with_entries()
    result = tool.execute(content="Python is a programming language")
    assert result.success is True
    assert "has_duplicates" in result.data
    assert "duplicate_count" in result.data
    assert "duplicates" in result.data
    assert "similarity_threshold" in result.data


def test_deduplicate_tool_execute_empty_store():
    store = MemoryStore()
    extractor = FeatureExtractor()
    tool = DeduplicateTool(store, extractor)
    result = tool.execute(content="anything")
    assert result.success is True
    assert result.data["has_duplicates"] is False


def test_deduplicate_tool_returns_metadata():
    tool = _make_tool_with_entries()
    result = tool.execute(content="Python")
    assert result.metadata.get("tool") == "lerev_deduplicate"
