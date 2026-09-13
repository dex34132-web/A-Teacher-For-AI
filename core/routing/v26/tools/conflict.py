"""Conflict detection tool for LEREV V2.6."""

from __future__ import annotations

from core.routing.v26.identity import AgentIdentity
from core.routing.v26.memory_manager import MemoryManager
from core.routing.v26.memory_types import MemoryRequest
from core.routing.v26.tools.base import Tool, ToolResult


class ConflictDetectionTool(Tool):
    """Detect conflicts between new content and existing memories."""

    def __init__(self, manager: MemoryManager) -> None:
        self._manager = manager

    @property
    def name(self) -> str:
        return "lerev_conflict"

    @property
    def description(self) -> str:
        return "Detect conflicts between new content and existing memories."

    @property
    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "New content to check for conflicts."},
                "agent_id": {"type": "string", "description": "Agent identifier.", "default": "default"},
                "limit": {"type": "integer", "description": "Maximum similar memories to retrieve.", "default": 5},
                "similarity_threshold": {
                    "type": "number",
                    "description": "Minimum similarity to consider a conflict [0,1].",
                    "default": 0.5,
                },
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
        agent_id: str = kwargs.get("agent_id", "default")
        limit: int = kwargs.get("limit", 5)

        agent = AgentIdentity.create(agent_id=agent_id)
        request = MemoryRequest(
            agent=agent,
            query=content,
            limit=limit,
            minimum_confidence=0.0,
        )

        response = self._manager.request_memory(request)

        conflicts: list[dict] = []
        for mem in response.memories:
            # Simple overlap-based conflict detection
            content_lower = content.lower()
            mem_lower = mem.content.lower()
            # Check for contradictory patterns
            has_opposite = False
            content_words = set(content_lower.split())
            mem_words = set(mem_lower.split())
            overlap = content_words & mem_words

            if len(overlap) > 2:
                # If significant overlap but not identical, potential conflict
                similarity = len(overlap) / max(len(content_words), len(mem_words), 1)
                if similarity > 0.3:
                    conflicts.append({
                        "memory_id": mem.memory_id,
                        "content": mem.content,
                        "similarity": similarity,
                        "overlap_count": len(overlap),
                        "confidence": mem.confidence,
                    })

        return ToolResult(
            success=True,
            data={
                "has_conflicts": len(conflicts) > 0,
                "conflict_count": len(conflicts),
                "conflicts": conflicts,
                "similar_memories_count": response.count,
            },
            errors=[],
            metadata={"tool": self.name},
        )
