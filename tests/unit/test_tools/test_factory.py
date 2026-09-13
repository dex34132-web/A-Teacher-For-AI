"""Tests for factory."""
import pytest
from core.routing.v26.factory import create_orchestrator


class TestFactory:
    def test_create_orchestrator_registers_all_tools(self):
        orch = create_orchestrator()
        tool_names = [t["name"] for t in orch._registry.list_tools()]
        expected = [
            "lerev_status",
            "lerev_remember",
            "lerev_recall",
            "lerev_conflict",
            "lerev_confidence",
            "lerev_search",
            "lerev_deduplicate",
            "lerev_knowledge",
            "lerev_lifecycle",
            "lerev_diagnose",
        ]
        for name in expected:
            assert name in tool_names, f"Tool {name} not registered"

    def test_create_orchestrator_all_executable(self):
        orch = create_orchestrator()
        # Tools that need specific params - provide defaults
        defaults = {
            "lerev_remember": {"content": "test"},
            "lerev_recall": {"query": "test"},
            "lerev_conflict": {"content": "test"},
            "lerev_deduplicate": {"content": "test"},
            "lerev_search": {"query": "test"},
            "lerev_lifecycle": {"action": "score", "memory_id": "test"},
        }
        # Tools that may fail due to state dependencies (not param issues)
        state_dependent = {"lerev_lifecycle"}
        for tool_info in orch._registry.list_tools():
            params = defaults.get(tool_info["name"], {})
            result = orch.dispatch(tool_info["name"], **params)
            if tool_info["name"] in state_dependent:
                # These may fail due to missing state, but should not crash
                assert result.metadata.get("tool") == tool_info["name"]
            else:
                assert result.success, f"Tool {tool_info['name']} failed: {result.errors}"
