"""Unit tests for the Teacher MCP server — thin translation over the bridge."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from teacher import bridge
from teacher.mcp import server as mcp_server

EXPECTED_TOOL_ORDER = [
    "teacher_status",
    "teacher_remember",
    "teacher_recall",
    "teacher_learn",
    "teacher_conflict",
    "teacher_confidence",
    "teacher_search",
    "teacher_deduplicate",
    "teacher_knowledge",
    "teacher_lifecycle",
    "teacher_diagnose",
]


@pytest.fixture(autouse=True)
def fresh_bridge() -> Any:
    """Reset the bridge's single-worktree module cache around every test."""

    def _reset() -> None:
        bridge._manager = None
        bridge._storage = None
        bridge._init_error = None
        bridge._orchestrator = None

    _reset()
    yield
    _reset()


@pytest.fixture()
def worktree(tmp_path: Path) -> str:
    project = tmp_path / "mcp_project"
    project.mkdir()
    return str(project)


class TestToolSurface:
    def test_list_tools_exact_names_and_order(self) -> None:
        result = mcp_server._list_tools()
        assert [t.name for t in result.tools] == EXPECTED_TOOL_ORDER

    def test_all_schemas_are_json_objects(self) -> None:
        for tool in mcp_server._list_tools().tools:
            assert tool.input_schema["type"] == "object"
            assert tool.description

    def test_recall_schema_contract(self) -> None:
        schema = mcp_server._TOOLS["teacher_recall"]["schema"]
        assert schema["required"] == ["query"]
        assert set(schema["properties"]) == {
            "query",
            "confidence_threshold",
            "context_budget",
            "limit",
            "project",
            "session",
            "agent_id",
        }

    def test_remember_schema_contract(self) -> None:
        schema = mcp_server._TOOLS["teacher_remember"]["schema"]
        assert schema["required"] == ["content"]
        assert schema["properties"]["outcome"]["enum"] == [
            "SUCCESS",
            "FAILURE",
            "NEUTRAL",
            "MIXED",
        ]
        assert {"confidence", "tags", "project", "session", "agent_id"} <= set(
            schema["properties"]
        )

    def test_learn_schema_contract(self) -> None:
        schema = mcp_server._TOOLS["teacher_learn"]["schema"]
        assert schema["required"] == ["content"]
        assert {"outcome", "project", "session", "agent_id"} <= set(schema["properties"])

    def test_lifecycle_schema_enums(self) -> None:
        schema = mcp_server._TOOLS["teacher_lifecycle"]["schema"]
        assert schema["required"] == ["action"]
        assert schema["properties"]["action"]["enum"] == [
            "score",
            "decay",
            "promote",
            "archive",
        ]


class TestToolCalls:
    def test_status_returns_ok_payload(self, worktree: str) -> None:
        result = mcp_server._call_tool(worktree, "teacher_status", {})
        assert result.is_error is False
        payload = json.loads(result.content[0].text)
        assert payload["ok"] is True
        assert payload["components"]["teacher"] == "available"
        assert result.structured_content == payload

    def test_recall_missing_query_is_error(self, worktree: str) -> None:
        result = mcp_server._call_tool(worktree, "teacher_recall", {})
        assert result.is_error is True
        payload = json.loads(result.content[0].text)
        assert payload["ok"] is False
        assert payload["error"]["type"] == "validation"

    def test_remember_missing_content_is_error(self, worktree: str) -> None:
        result = mcp_server._call_tool(worktree, "teacher_remember", {})
        assert result.is_error is True

    def test_unknown_tool_raises(self, worktree: str) -> None:
        with pytest.raises(ValueError, match="Unknown tool"):
            mcp_server._call_tool(worktree, "teacher_bogus", {})

    def test_unknown_arguments_are_filtered(self, worktree: str) -> None:
        result = mcp_server._call_tool(
            worktree,
            "teacher_recall",
            {"query": "anything", "bogus_argument": 123, "nested": {"x": 1}},
        )
        assert result.is_error is False

    def test_learn_alias_stores_and_recall_finds(self, worktree: str) -> None:
        stored = mcp_server._call_tool(
            worktree,
            "teacher_learn",
            {"content": "learn alias unit probe", "outcome": "SUCCESS"},
        )
        assert stored.is_error is False
        assert stored.structured_content["ok"] is True
        assert stored.structured_content["result"]["stored"] is True
        assert stored.structured_content["result"]["experience_id"]

        recalled = mcp_server._call_tool(
            worktree, "teacher_recall", {"query": "learn alias probe"}
        )
        assert recalled.is_error is False
        memories = recalled.structured_content["memories"]
        assert len(memories) >= 1
        assert any("learn alias unit probe" in m["content"] for m in memories)

    def test_remember_then_recall_same_session_scope(
        self, worktree: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("TEACHER_PROJECT", raising=False)
        monkeypatch.delenv("TEACHER_SESSION", raising=False)
        monkeypatch.delenv("TEACHER_AGENT", raising=False)
        mcp_server._call_tool(
            worktree,
            "teacher_remember",
            {"content": "scoped memory probe", "project": "envscope", "session": "s1"},
        )
        recall = mcp_server._call_tool(
            worktree, "teacher_recall", {"query": "scoped memory probe"}
        )
        # No env project set: recall defaults to worktree basename, so the
        # project-scoped memory must NOT leak through.
        assert recall.is_error is False
        assert recall.structured_content["memories"] == []

        monkeypatch.setenv("TEACHER_PROJECT", "envscope")
        monkeypatch.setenv("TEACHER_SESSION", "s1")
        recall = mcp_server._call_tool(
            worktree, "teacher_recall", {"query": "scoped memory probe"}
        )
        assert recall.is_error is False
        memories = recall.structured_content["memories"]
        assert any("scoped memory probe" in m["content"] for m in memories)


class TestScopeIsolation:
    def test_cross_worktree_isolation(self, tmp_path: Path) -> None:
        one = tmp_path / "one"
        two = tmp_path / "two"
        one.mkdir()
        two.mkdir()

        stored = mcp_server._call_tool(
            str(one), "teacher_remember", {"content": "isolated secret memory"}
        )
        assert stored.is_error is False

        leaked = mcp_server._call_tool(
            str(two), "teacher_recall", {"query": "isolated secret memory"}
        )
        assert leaked.is_error is False
        assert leaked.structured_content["memories"] == []

    def test_same_worktree_finds_memory(self, tmp_path: Path) -> None:
        one = tmp_path / "one"
        one.mkdir()
        mcp_server._call_tool(str(one), "teacher_remember", {"content": "visible memory"})
        found = mcp_server._call_tool(str(one), "teacher_recall", {"query": "visible memory"})
        assert len(found.structured_content["memories"]) >= 1


class TestBuildRequest:
    def test_project_defaults_to_worktree_basename(self) -> None:
        req = mcp_server._build_request("/tmp/proj-xyz", "teacher_recall", {"query": "q"})
        assert req["project"] == "proj-xyz"

    def test_lifecycle_has_no_basename_default(self) -> None:
        req = mcp_server._build_request("/tmp/proj-xyz", "teacher_lifecycle", {"action": "score"})
        assert "project" not in req

    def test_agent_defaults_to_opencode_for_bridge_tools(self) -> None:
        # Matches bridge remember/recall defaults and the OpenCode plugin,
        # so MCP and plugin memories share one agent scope.
        req = mcp_server._build_request("/tmp/p", "teacher_recall", {"query": "q"})
        assert req["agent"] == "opencode"
        assert "agent_id" not in req

    def test_agent_defaults_to_opencode_for_dispatch_tools(self) -> None:
        req = mcp_server._build_request("/tmp/p", "teacher_learn", {"content": "x"})
        assert req["agent_id"] == "opencode"
        assert "agent" not in req

    def test_env_project_overrides_basename(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TEACHER_PROJECT", "env-proj")
        req = mcp_server._build_request("/tmp/proj-xyz", "teacher_recall", {"query": "q"})
        assert req["project"] == "env-proj"

    def test_arg_project_overrides_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEACHER_PROJECT", "env-proj")
        req = mcp_server._build_request(
            "/tmp/proj-xyz", "teacher_recall", {"query": "q", "project": "arg-proj"}
        )
        assert req["project"] == "arg-proj"

    def test_session_env_fill(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEACHER_SESSION", "sess-9")
        req = mcp_server._build_request("/tmp/p", "teacher_recall", {"query": "q"})
        assert req["session"] == "sess-9"

    def test_agent_env_maps_to_bridge_agent_for_remember(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TEACHER_AGENT", "mcp-agent")
        req = mcp_server._build_request("/tmp/p", "teacher_remember", {"content": "x"})
        assert req["agent"] == "mcp-agent"
        assert "agent_id" not in req

    def test_agent_env_maps_to_agent_id_for_dispatch_tools(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TEACHER_AGENT", "mcp-agent")
        req = mcp_server._build_request("/tmp/p", "teacher_learn", {"content": "x"})
        assert req["agent_id"] == "mcp-agent"
        assert "agent" not in req

    def test_worktree_always_present(self) -> None:
        req = mcp_server._build_request("/tmp/p", "teacher_status", {})
        assert req["worktree"] == "/tmp/p"

    def test_foreign_arguments_dropped(self) -> None:
        req = mcp_server._build_request("/tmp/p", "teacher_recall", {"query": "q", "zzz": 1})
        assert "zzz" not in req


class TestIntParam:
    def test_clamps_high_values(self) -> None:
        assert mcp_server._int_param({"limit": ["99"]}, "limit", 5, 1, 5) == 5
        assert mcp_server._int_param({"budget": ["999999"]}, "budget", 600, 1, 600) == 600

    def test_clamps_low_values(self) -> None:
        assert mcp_server._int_param({"limit": ["0"]}, "limit", 5, 1, 5) == 1

    def test_defaults_on_missing_or_invalid(self) -> None:
        assert mcp_server._int_param({}, "limit", 5, 1, 5) == 5
        assert mcp_server._int_param({"limit": ["abc"]}, "limit", 5, 1, 5) == 5


class TestResources:
    def test_list_resources_status_only(self) -> None:
        resources = mcp_server._list_resources().resources
        assert [str(r.uri) for r in resources] == ["teacher://status"]

    def test_list_resource_templates(self) -> None:
        templates = mcp_server._list_resource_templates().resource_templates
        assert templates[0].uri_template == "teacher://context/{project}"

    def test_read_status_resource(self, worktree: str) -> None:
        result = mcp_server._read_resource(worktree, "teacher://status")
        payload = json.loads(result.contents[0].text)
        assert payload["ok"] is True
        assert result.contents[0].mime_type == "application/json"

    def test_read_context_resource_budgeted(
        self, worktree: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TEACHER_PROJECT", "ctxproj")
        for index in range(7):
            mcp_server._call_tool(
                worktree,
                "teacher_remember",
                {"content": f"ctx memory number {index}", "project": "ctxproj"},
            )
        project = Path(worktree).name
        uri = f"teacher://context/{project}?q=ctx memory&limit=99&budget=99999"
        result = mcp_server._read_resource(worktree, uri)
        payload = json.loads(result.contents[0].text)
        assert payload["ok"] is True
        # limit is clamped to 5 no matter what the caller asks for
        assert len(payload["memories"]) <= 5

    def test_unknown_resource_raises(self, worktree: str) -> None:
        with pytest.raises(ValueError, match="Unknown resource"):
            mcp_server._read_resource(worktree, "teacher://bogus")

    def test_context_without_project_raises(self, worktree: str) -> None:
        with pytest.raises(ValueError, match="Unknown resource"):
            mcp_server._read_resource(worktree, "teacher://context/")


class TestPrompts:
    def test_list_prompts(self) -> None:
        prompts = mcp_server._list_prompts().prompts
        assert [p.name for p in prompts] == ["relevant_context"]
        query_arg = prompts[0].arguments[0]
        assert query_arg.name == "query"
        assert query_arg.required is True

    def test_get_prompt_marks_context_block(self, worktree: str) -> None:
        mcp_server._call_tool(worktree, "teacher_remember", {"content": "prompt memory probe"})
        result = mcp_server._get_prompt(worktree, "relevant_context", {"query": "prompt memory"})
        text = result.messages[0].content.text
        assert text.startswith("[teacher context]")
        assert text.rstrip().endswith("[/teacher]")
        assert "prompt memory probe" in text
        assert result.messages[0].role == "user"

    def test_get_prompt_no_hits_is_not_an_error(self, worktree: str) -> None:
        result = mcp_server._get_prompt(worktree, "relevant_context", {"query": "nothing here"})
        assert "No memories matched" in result.messages[0].content.text

    def test_get_prompt_missing_query_raises(self, worktree: str) -> None:
        with pytest.raises(ValueError, match="query"):
            mcp_server._get_prompt(worktree, "relevant_context", {})

    def test_unknown_prompt_raises(self, worktree: str) -> None:
        with pytest.raises(ValueError, match="Unknown prompt"):
            mcp_server._get_prompt(worktree, "bogus", {"query": "x"})


class TestBuildServer:
    def test_build_server_binds_worktree(self, worktree: str) -> None:
        server = mcp_server.build_server(worktree)
        assert server.name == "teacher"
        assert bridge._manager is not None
        assert bridge._storage is not None

    def test_build_server_env_worktree(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        project = tmp_path / "env_wt"
        project.mkdir()
        monkeypatch.setenv("TEACHER_WORKTREE", str(project))
        mcp_server.build_server()
        assert bridge._manager is not None

    def test_instructions_frame_memory_as_data(self) -> None:
        assert "never instructions" in mcp_server._INSTRUCTIONS


class TestClientConfig:
    def test_all_presets_produce_valid_config(self) -> None:
        import json as jsonlib
        import tomllib

        from teacher.mcp.config import CLIENT_PATHS, build_client_config

        for client in CLIENT_PATHS:
            preset = build_client_config(client)
            assert preset["name"] == client
            assert preset["path"]
            if preset["format"] == "json":
                jsonlib.loads(preset["config"])
            else:
                tomllib.loads(preset["config"])
            assert "teacher.mcp" in preset["config"]

    def test_unknown_client_raises(self) -> None:
        from teacher.mcp.config import build_client_config

        with pytest.raises(ValueError, match="Unknown MCP client"):
            build_client_config("not-a-client")

    def test_custom_python_interpreter(self) -> None:
        import json as jsonlib

        from teacher.mcp.config import build_client_config

        preset = build_client_config("claude", python="C:\\custom\\python.exe")
        block = jsonlib.loads(preset["config"])
        assert block["mcpServers"]["teacher"]["command"] == "C:\\custom\\python.exe"
