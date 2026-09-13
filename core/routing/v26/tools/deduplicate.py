"""Deduplication tool for LEREV V2.6."""

from __future__ import annotations

from core.learner.feature_extractor import FeatureExtractor
from core.learner.similarity import cosine_similarity
from core.routing.v26.identity import AgentIdentity, MemoryScope
from core.routing.v26.memory_store import MemoryStore
from core.routing.v26.semantic_retrieval import scored_query
from core.routing.v26.tools.base import Tool, ToolResult


class DeduplicateTool(Tool):
    """Find duplicate or near-duplicate memories."""

    def __init__(self, store: MemoryStore, extractor: FeatureExtractor) -> None:
        self._store = store
        self._extractor = extractor

    @property
    def name(self) -> str:
        return "lerev_deduplicate"

    @property
    def description(self) -> str:
        return "Find duplicate or near-duplicate memories using semantic similarity."

    @property
    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Content to check for duplicates."},
                "limit": {"type": "integer", "description": "Maximum similar memories to check.", "default": 20},
                "similarity_threshold": {
                    "type": "number",
                    "description": "Minimum similarity to consider a duplicate [0,1].",
                    "default": 0.8,
                },
                "agent_id": {"type": "string", "description": "Agent scope filter.", "default": "default"},
            },
            "required": ["content"],
        }

    def validate(self, **kwargs) -> list[str]:
        errors = super().validate(**kwargs)
        content = kwargs.get("content", "")
        if not content:
            errors.append("content is required and must not be empty")
        return errors

    def execute(self, **kwargs) -> ToolResult:
        content: str = kwargs["content"]
        limit: int = kwargs.get("limit", 20)
        similarity_threshold: float = kwargs.get("similarity_threshold", 0.8)
        agent_id: str = kwargs.get("agent_id", "default")

        agent = AgentIdentity.create(agent_id=agent_id)
        scope = MemoryScope(agent=agent)

        entries = self._store.query(scope=scope, limit=10000)

        candidates = scored_query(entries, content, self._extractor, limit=limit)

        duplicates: list[dict] = []
        content_vec = self._extractor.transform(content)

        for entry in candidates:
            entry_vec = self._extractor.transform(entry.content)
            sim = cosine_similarity(content_vec, entry_vec, self._extractor)
            if sim >= similarity_threshold:
                duplicates.append({
                    "memory_id": entry.memory_id,
                    "content": entry.content,
                    "similarity": sim,
                    "confidence": entry.confidence,
                })

        return ToolResult(
            success=True,
            data={
                "has_duplicates": len(duplicates) > 0,
                "duplicate_count": len(duplicates),
                "duplicates": duplicates,
                "similarity_threshold": similarity_threshold,
            },
            errors=[],
            metadata={"tool": self.name},
        )
