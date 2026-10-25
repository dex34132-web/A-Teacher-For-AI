"""Lifecycle management tool for Toolio V2.6."""

from __future__ import annotations

import math

from core.routing.v26.identity import coerce_text
from core.routing.v26.memory_manager import MemoryManager
from core.routing.v26.tools.base import (
    Tool,
    ToolResult,
    error_result,
    fail_open,
    fail_open_validate,
)

_VALID_ACTIONS = frozenset({"score", "decay", "promote", "archive"})
_DEFAULT_AMOUNT = 0.1


class LifecycleTool(Tool):
    """Manage memory lifecycle operations (score, decay, promote, archive)."""

    def __init__(self, manager: MemoryManager) -> None:
        self._manager = manager

    @property
    def name(self) -> str:
        return "toolio_lifecycle"

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

    @fail_open_validate
    def validate(self, **kwargs) -> list[str]:
        errors: list[str] = []
        raw_action = kwargs.get("action", "")
        action = raw_action if isinstance(raw_action, str) else None
        if action is None or action not in _VALID_ACTIONS:
            errors.append(
                f"Invalid action: {coerce_text(raw_action, '<unprintable>')}. "
                f"Must be one of: {', '.join(sorted(_VALID_ACTIONS))}"
            )
        try:
            has_memory_id = bool(kwargs.get("memory_id"))
        except Exception:  # noqa: BLE001 - hostile ids count as missing
            has_memory_id = False
        if action in ("promote", "archive") and not has_memory_id:
            errors.append(f"memory_id is required for action '{action}'")
        return errors

    @fail_open
    def execute(self, **kwargs) -> ToolResult:
        raw_action = kwargs.get("action", "")
        action = coerce_text(raw_action)
        memory_id = coerce_text(kwargs.get("memory_id", ""))

        if action in ("score", "decay"):
            ok, amount = _resolve_amount(kwargs.get("amount", _DEFAULT_AMOUNT))
            if not ok:
                return error_result(self.name, "amount must be a number")
        else:
            amount = _DEFAULT_AMOUNT

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
            errors=[f"Unknown action: {coerce_text(raw_action, '<unprintable>')}"],
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
        current = _entry_confidence(entry)
        new_confidence = max(0.0, min(1.0, current + amount))
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
        current = _entry_confidence(entry)
        new_confidence = max(0.0, current - amount)
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
        data = {
            "memory_id": memory_id,
            "action": "promote",
            "content": entry.content,
        }
        # LLM-in-the-loop advisory (non-breaking: annotates only).
        try:
            from core.llm import llm_complete

            reply = llm_complete(
                "Memory: {!r}\nShould this memory be promoted to a higher "
                "confidence tier? Reply YES or NO only.".format(entry.content[:200]),
                system="You are a memory-lifecycle judge. Reply YES or NO only.",
                temperature=0.0,
                max_tokens=4,
            )
            if reply is not None:
                low = reply.strip().lower()
                data["llm_advice"] = "promote" if low.startswith("y") else "hold"
        except Exception:  # noqa: BLE001
            pass
        return ToolResult(
            success=True,
            data=data,
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
        # LLM-in-the-loop advisory (non-breaking: annotates only, never blocks).
        llm_advice = None
        try:
            from core.llm import llm_complete

            reply = llm_complete(
                "Memory: {!r}\nShould this memory be archived (removed from "
                "active recall)? Reply YES or NO only.".format(entry.content[:200]),
                system="You are a memory-lifecycle judge. Reply YES or NO only.",
                temperature=0.0,
                max_tokens=4,
            )
            if reply is not None:
                low = reply.strip().lower()
                llm_advice = "archive" if low.startswith("y") else "keep"
        except Exception:  # noqa: BLE001
            pass
        removed = self._manager.remove_memory(memory_id)
        data = {
            "memory_id": memory_id,
            "action": "archive",
            "removed": removed,
        }
        if llm_advice is not None:
            data["llm_advice"] = llm_advice
        return ToolResult(
            success=removed,
            data=data,
            errors=[] if removed else [f"Failed to archive memory: {memory_id}"],
            metadata={"tool": self.name},
        )


def _entry_confidence(entry) -> float:
    """Numeric confidence of an entry; garbage degrades to 0.0."""
    try:
        value = float(entry.confidence)
    except Exception:  # noqa: BLE001
        return 0.0
    return value if math.isfinite(value) else 0.0


def _resolve_amount(raw: object) -> tuple[bool, float]:
    """Resolve amount fail-open: NaN/inf -> default, garbage -> not ok."""
    if raw is None:
        return True, _DEFAULT_AMOUNT
    if isinstance(raw, bool):
        return True, float(raw)
    if isinstance(raw, (int, float)):
        value = float(raw)
        return True, value if math.isfinite(value) else _DEFAULT_AMOUNT
    if isinstance(raw, str):
        try:
            value = float(raw)
        except ValueError:
            return False, _DEFAULT_AMOUNT
        return True, value if math.isfinite(value) else _DEFAULT_AMOUNT
    return False, _DEFAULT_AMOUNT
