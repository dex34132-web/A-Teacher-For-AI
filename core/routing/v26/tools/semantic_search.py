"""Semantic search tool for LEREV V2.6."""

from __future__ import annotations

from core.learner.feature_extractor import FeatureExtractor
from core.routing.v26.identity import AgentIdentity
from core.routing.v26.memory_store import MemoryStore
from core.routing.v26.semantic_retrieval import scored_query
from core.routing.v26.tools.base import Tool, ToolResult


class SemanticSearchTool(Tool):
    """Search memories using TF-IDF semantic similarity."""

    def __init__(self, store: MemoryStore, extractor: FeatureExtractor) -> None:
        self._store = store
        self._extractor = extractor

    @property
    def name(self) -> str:
        return "lerev_search"

    @property
    def description(self) -> str:
        return "Search memories using TF-IDF semantic similarity ranking."

    @property
    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query text."},
                "limit": {"type": "integer", "description": "Maximum results.", "default": 10},
                "agent_id": {"type": "string", "description": "Agent scope filter.", "default": "default"},
            },
            "required": ["query"],
        }

    def validate(self, **kwargs) -> list[str]:
        errors = super().validate(**kwargs)
        query = kwargs.get("query", "")
        if not query:
            errors.append("query is required and must not be empty")
        return errors

    def execute(self, **kwargs) -> ToolResult:
        query: str = kwargs["query"]
        limit: int = kwargs.get("limit", 10)
        agent_id: str = kwargs.get("agent_id", "default")

        agent = AgentIdentity.create(agent_id=agent_id)
        scope = _make_scope(agent)

        entries = self._store.query(scope=scope, limit=10000)

        results = scored_query(entries, query, self._extractor, limit=limit)

        return ToolResult(
            success=True,
            data={
                "memories": [e.to_dict() for e in results],
                "count": len(results),
                "query": query,
            },
            errors=[],
            metadata={"tool": self.name},
        )


def _make_scope(agent: AgentIdentity):
    """Create a MemoryScope from an AgentIdentity."""
    from core.routing.v26.identity import MemoryScope
    return MemoryScope(agent=agent)
