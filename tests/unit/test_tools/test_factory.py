"""Tests for factory."""
from core.routing.v26.factory import create_orchestrator


class TestFactory:
    def test_create_orchestrator_registers_all_tools(self):
        orch = create_orchestrator()
        tool_names = [t["name"] for t in orch._registry.list_tools()]
        expected = [
            "toolio_status",
            "toolio_remember",
            "toolio_recall",
            "toolio_conflict",
            "toolio_confidence",
            "toolio_search",
            "toolio_deduplicate",
            "toolio_knowledge",
            "toolio_lifecycle",
            "toolio_diagnose",
            "toolio_skill_list",
            "toolio_skill_search",
            "toolio_skill_create",
            "toolio_skill_use",
            "toolio_skill_feedback",
            "toolio_skill_status",
            "toolio_skill_evolve",
        ]
        for name in expected:
            assert name in tool_names, f"Tool {name} not registered"

    def test_create_orchestrator_all_executable(self, tmp_path, monkeypatch):
        orch = create_orchestrator()
        wt = str(tmp_path)  # keep skillgen writes out of the repo tree
        # Phase 2 tools are network-bound: mock discovery (no live GitHub).
        from core.routing.v26.tools import skillgen_github

        def _fake_discovery(*_args, **_kwargs):
            return {"ok": True}

        for _fn in (
            "search_github",
            "discover",
            "analyze_external",
            "compare",
            "import_external",
        ):
            monkeypatch.setattr(skillgen_github.discovery, _fn, _fake_discovery)
        # Tools that need specific params - provide defaults
        defaults = {
            "toolio_remember": {"content": "test"},
            "toolio_recall": {"query": "test"},
            "toolio_conflict": {"content": "test"},
            "toolio_deduplicate": {"content": "test"},
            "toolio_search": {"query": "test"},
            "toolio_lifecycle": {"action": "score", "memory_id": "test"},
            "toolio_skill_list": {"worktree": wt},
            "toolio_skill_search": {"query": "test", "worktree": wt},
            "toolio_skill_create": {
                "name": "factory-exec-test",
                "description": "Factory executable test skill",
                "purpose": "Created by the factory executability test",
                "procedure": ["Do the one thing"],
                "worktree": wt,
            },
            "toolio_skill_use": {"query": "test", "worktree": wt},
            "toolio_skill_feedback": {
                "name": "factory-exec-test",
                "success": True,
                "worktree": wt,
            },
            "toolio_skill_status": {"worktree": wt},
            "toolio_skill_evolve": {"worktree": wt},
            "toolio_skill_search_github": {"task": "test task", "worktree": wt},
            "toolio_skill_discover": {"task": "test task", "worktree": wt},
            "toolio_skill_analyze_external": {
                "owner": "acme",
                "repo": "demo",
                "worktree": wt,
            },
            "toolio_skill_compare": {"owner": "acme", "repo": "demo", "worktree": wt},
            "toolio_skill_import": {
                "owner": "acme",
                "repo": "demo",
                "approve": True,
                "worktree": wt,
            },
        }
        # Tools that may fail due to state dependencies (not param issues)
        state_dependent = {"toolio_lifecycle"}
        for tool_info in orch._registry.list_tools():
            params = defaults.get(tool_info["name"], {})
            result = orch.dispatch(tool_info["name"], **params)
            if tool_info["name"] in state_dependent:
                # These may fail due to missing state, but should not crash
                assert result.metadata.get("tool") == tool_info["name"]
            else:
                assert result.success, f"Tool {tool_info['name']} failed: {result.errors}"
