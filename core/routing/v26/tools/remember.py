"""Remember tool for LEREV V2.6 — store an experience."""

from __future__ import annotations

from core.routing.v26.experience import Experience, ExperienceOutcome
from core.routing.v26.identity import AgentIdentity
from core.routing.v26.memory_manager import MemoryManager
from core.routing.v26.tools.base import Tool, ToolResult


class RememberTool(Tool):
    """Store an experience into LEREV long-term memory."""

    def __init__(self, manager: MemoryManager) -> None:
        self._manager = manager

    @property
    def name(self) -> str:
        return "lerev_remember"

    @property
    def description(self) -> str:
        return "Store an experience into LEREV long-term memory."

    @property
    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Experience content to remember."},
                "outcome": {
                    "type": "string",
                    "enum": ["SUCCESS", "FAILURE", "NEUTRAL", "MIXED"],
                    "description": "Outcome of the experience.",
                    "default": "NEUTRAL",
                },
                "observation": {"type": "string", "description": "What was observed."},
                "action": {"type": "string", "description": "What action was taken."},
                "agent_id": {"type": "string", "description": "Agent identifier.", "default": "default"},
                "source": {"type": "string", "description": "Source of the experience.", "default": "tool"},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for filtering."},
                "confidence": {"type": "number", "description": "Confidence in this memory [0,1].", "default": 0.5},
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
        outcome_str: str = kwargs.get("outcome", "NEUTRAL")
        observation: str = kwargs.get("observation", content)
        action: str = kwargs.get("action", "")
        agent_id: str = kwargs.get("agent_id", "default")
        source: str = kwargs.get("source", "tool")
        tags: list[str] = kwargs.get("tags", [])
        confidence: float = kwargs.get("confidence", 0.5)

        try:
            outcome = ExperienceOutcome[outcome_str]
        except KeyError:
            return ToolResult(
                success=False,
                data={},
                errors=[f"Invalid outcome: {outcome_str}. Must be one of: SUCCESS, FAILURE, NEUTRAL, MIXED"],
                metadata={"tool": self.name},
            )

        agent = AgentIdentity.create(agent_id=agent_id)
        experience = Experience.create(
            agent=agent,
            observation=observation,
            action=action,
            outcome=outcome,
            source=source,
            tags=frozenset(tags),
            confidence=confidence,
        )

        success, reason = self._manager.store_experience(experience)

        return ToolResult(
            success=success,
            data={"experience_id": experience.experience_id, "stored": success},
            errors=[] if success else [reason],
            metadata={"tool": self.name},
        )
