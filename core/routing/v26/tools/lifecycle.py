"""Lifecycle management tool for LEREV V2.6."""

from __future__ import annotations

from core.routing.v26.memory_manager import MemoryManager
from core.routing.v26.tools.base import Tool, ToolResult

_VALID_ACTIONS = frozenset({"score", "decay", "promote", "archive"})


class LifecycleTool(Tool):
    """Manage memory lifecycle operations (score, decay, promote, archive)."""

    def __init__(self, manager: MemoryManager) -> None:
        self._manager = manager

    @property
    def name(self) -> str:
        return "lerev_lifecycle"

    @property
    def description(self) -> str:
        return "Manage memory lifecycle: score, decay, promote, or archive memories."

    @property
    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["score", "decay", "promote", "archive"],
                    "description": "Lifecycle action to perform.",
                },
                "memory_id": {
                    "type": "string",
                    "description": "Memory ID to operate on (required for promote/archive).",
                },
                "amount": {
                    "type": "number",
                    "description": "Amount for score/decay operations.",
                    "default": 0.1,
                },
            },
            "required": ["action"],
        }

    def validate(self, **kwargs) -> list[str]:
        errors = super().validate(**kwargs)
        action = kwargs.get("action", "")
        if action not in _VALID_ACTIONS:
            errors.append(f"Invalid action: {action}. Must be one of: {', '.join(sorted(_VALID_ACTIONS))}")
        if action in ("promote", "archive") and not kwargs.get("memory_id"):
            errors.append(f"memory_id is required for action '{action}'")
        return errors

    def execute(self, **kwargs) -> ToolResult:
        action: str = kwargs["action"]
        memory_id: str = kwargs.get("memory_id", "")
        amount: float = kwargs.get("amount", 0.1)

        if action == "score":
            return self._handle_score(memory_id, amount)
        elif action == "decay":
            return self._handle_decay(memory_id, amount)
        elif action == "promote":
            return self._handle_promote(memory_id)
        elif action == "archive":
            return self._handle_archive(memory_id)

        return ToolResult(
            success=False,
            data={},
            errors=[f"Unknown action: {action}"],
            metadata={"tool": self.name},
        )

    def _handle_score(self, memory_id: str, amount: float) -> ToolResult:
        entry = self._manager.get_memory(memory_id)
        if entry is None:
            return ToolResult(
                success=False,
                data={},
                errors=[f"Memory not found: {memory_id}"],
                metadata={"tool": self.name},
            )
        new_confidence = max(0.0, min(1.0, entry.confidence + amount))
        return ToolResult(
            success=True,
            data={
                "memory_id": memory_id,
                "old_confidence": entry.confidence,
                "new_confidence": new_confidence,
                "action": "score",
            },
            errors=[],
            metadata={"tool": self.name},
        )

    def _handle_decay(self, memory_id: str, amount: float) -> ToolResult:
        entry = self._manager.get_memory(memory_id)
        if entry is None:
            return ToolResult(
                success=False,
                data={},
                errors=[f"Memory not found: {memory_id}"],
                metadata={"tool": self.name},
            )
        new_confidence = max(0.0, entry.confidence - amount)
        return ToolResult(
            success=True,
            data={
                "memory_id": memory_id,
                "old_confidence": entry.confidence,
                "new_confidence": new_confidence,
                "action": "decay",
            },
            errors=[],
            metadata={"tool": self.name},
        )

    def _handle_promote(self, memory_id: str) -> ToolResult:
        entry = self._manager.get_memory(memory_id)
        if entry is None:
            return ToolResult(
                success=False,
                data={},
                errors=[f"Memory not found: {memory_id}"],
                metadata={"tool": self.name},
            )
        return ToolResult(
            success=True,
            data={
                "memory_id": memory_id,
                "action": "promote",
                "content": entry.content,
            },
            errors=[],
            metadata={"tool": self.name},
        )

    def _handle_archive(self, memory_id: str) -> ToolResult:
        entry = self._manager.get_memory(memory_id)
        if entry is None:
            return ToolResult(
                success=False,
                data={},
                errors=[f"Memory not found: {memory_id}"],
                metadata={"tool": self.name},
            )
        removed = self._manager.remove_memory(memory_id)
        return ToolResult(
            success=removed,
            data={
                "memory_id": memory_id,
                "action": "archive",
                "removed": removed,
            },
            errors=[] if removed else [f"Failed to archive memory: {memory_id}"],
            metadata={"tool": self.name},
        )
