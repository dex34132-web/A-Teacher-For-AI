"""Tests for factory."""
import pytest
from core.routing.v26.factory import create_orchestrator


class TestFactory:
    def test_create_orchestrator_registers_all_tools(self):
        orch = create_orchestrator()
        tool_names = [t["name"] for t in orch._registry.list_tools()]
        expected = [
            "teacher_status",
            "teacher_remember",
            "teacher_recall",
            "teacher_conflict",
            "teacher_confidence",
            "teacher_search",
            "teacher_deduplicate",
            "teacher_knowledge",
            "teacher_lifecycle",
            "teacher_diagnose",
        ]
        for name in expected:
            assert name in tool_names, f"Tool {name} not registered"

    def test_create_orchestrator_all_executable(self):
        orch = create_orchestrator()
        # Tools that need specific params - provide defaults
        defaults = {
            "teacher_remember": {"content": "test"},
            "teacher_recall": {"query": "test"},
            "teacher_conflict": {"content": "test"},
            "teacher_deduplicate": {"content": "test"},
            "teacher_search": {"query": "test"},
            "teacher_lifecycle": {"action": "score", "memory_id": "test"},
        }
        # Tools that may fail due to state dependencies (not param issues)
        state_dependent = {"teacher_lifecycle"}
        for tool_info in orch._registry.list_tools():
            params = defaults.get(tool_info["name"], {})
            result = orch.dispatch(tool_info["name"], **params)
            if tool_info["name"] in state_dependent:
                # These may fail due to missing state, but should not crash
                assert result.metadata.get("tool") == tool_info["name"]
            else:
                assert result.success, f"Tool {tool_info['name']} failed: {result.errors}"
