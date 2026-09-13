"""Knowledge extraction tool for LEREV V2.6."""

from __future__ import annotations

from core.routing.v26.identity import MemoryScope
from core.routing.v26.memory_manager import MemoryManager
from core.routing.v26.tools.base import Tool, ToolResult


class KnowledgeExtractionTool(Tool):
    """Consolidate experiences into learned knowledge."""

    def __init__(self, manager: MemoryManager) -> None:
        self._manager = manager

    @property
    def name(self) -> str:
        return "lerev_knowledge"

    @property
    def description(self) -> str:
        return "Consolidate episodic experiences into learned knowledge."

    @property
    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Agent scope for consolidation.", "default": "default"},
            },
            "required": [],
        }

    def execute(self, **kwargs) -> ToolResult:
        agent_id: str = kwargs.get("agent_id", "default")

        from core.routing.v26.identity import AgentIdentity
        agent = AgentIdentity.create(agent_id=agent_id)
        scope = MemoryScope(agent=agent)

        result = self._manager.consolidate([], scope=scope)

        return ToolResult(
            success=True,
            data={
                "promoted_count": result.promoted_count,
                "retained_count": result.retained_count,
                "discarded_count": result.discarded_count,
                "promoted": [e.to_dict() for e in result.promoted],
                "provenance": {k: list(v) for k, v in result.provenance.items()},
            },
            errors=[],
            metadata={"tool": self.name},
        )
