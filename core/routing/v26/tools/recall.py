"""Recall tool for LEREV V2.6 — retrieve memories by query."""

from __future__ import annotations

from core.routing.v26.identity import AgentIdentity
from core.routing.v26.memory_manager import MemoryManager
from core.routing.v26.memory_types import MemoryRequest
from core.routing.v26.tools.base import Tool, ToolResult


class RecallTool(Tool):
    """Retrieve memories from LEREV long-term memory by query."""

    def __init__(self, manager: MemoryManager) -> None:
        self._manager = manager

    @property
    def name(self) -> str:
        return "lerev_recall"

    @property
    def description(self) -> str:
        return "Retrieve memories from LEREV long-term memory by query."

    @property
    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query text."},
                "agent_id": {"type": "string", "description": "Agent identifier.", "default": "default"},
                "limit": {"type": "integer", "description": "Maximum memories to return.", "default": 10},
                "minimum_confidence": {
                    "type": "number",
                    "description": "Minimum confidence threshold [0,1].",
                    "default": 0.0,
                },
                "context_budget": {
                    "type": "integer",
                    "description": "Maximum tokens for returned memories.",
                    "default": 4096,
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Required tags filter.",
                    "default": [],
                },
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
        agent_id: str = kwargs.get("agent_id", "default")
        limit: int = kwargs.get("limit", 10)
        minimum_confidence: float = kwargs.get("minimum_confidence", 0.0)
        context_budget: int = kwargs.get("context_budget", 4096)
        tags: list[str] = kwargs.get("tags", [])

        agent = AgentIdentity.create(agent_id=agent_id)
        request = MemoryRequest(
            agent=agent,
            query=query,
            limit=limit,
            minimum_confidence=minimum_confidence,
            context_budget=context_budget,
            tags=frozenset(tags),
        )

        response = self._manager.request_memory(request)

        return ToolResult(
            success=True,
            data={
                "memories": [m.to_dict() for m in response.memories],
                "total": response.total,
                "truncated": response.truncated,
                "context_cost": response.context_cost,
                "count": response.count,
            },
            errors=[],
            metadata={"tool": self.name, "provenance": list(response.provenance)},
        )
