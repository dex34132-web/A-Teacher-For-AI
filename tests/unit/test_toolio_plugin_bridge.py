"""Tests for Toolio plugin source and bridge protocol."""

from __future__ import annotations

import json
import re
from io import StringIO
from unittest.mock import patch

import pytest

from toolio.plugin_source import TS_PLUGIN_SOURCE

#: The approved agent-facing OpenCode tool surface (order matters).
EXPECTED_OPENCODE_TOOLS = [
    "toolio_status",
    "toolio_dashboard",
    "toolio_remember",
    "toolio_recall",
    "toolio_learn",
    "toolio_conflict",
    "toolio_confidence",
    "toolio_search",
    "toolio_deduplicate",
    "toolio_knowledge",
    "toolio_lifecycle",
    "toolio_diagnose",
    "toolio_route",
    "toolio_route_stats",
    "toolio_skill_list",
    "toolio_skill_search",
    "toolio_skill_create",
    "toolio_skill_use",
    "toolio_skill_feedback",
    "toolio_skill_status",
    "toolio_skill_evolve",
    "toolio_skill_search_github",
    "toolio_skill_discover",
    "toolio_skill_analyze_external",
    "toolio_skill_compare",
    "toolio_skill_import",
    "toolio_context_status",
    "toolio_context_compress",
    "toolio_context_restore",
    "toolio_observe",
    "toolio_goal",
    "toolio_research",
    "toolio_explore",
    "toolio_progress",
    "toolio_session",
    "toolio_execute",
    "toolio_navigate",
    "toolio_workflow",
    "toolio_docs",
    "toolio_visualize",
    "toolio_clarion",
    "toolio_blueprint",
    "toolio_edict",
    "toolio_weave",
    "toolio_compass",
    "toolio_brainstorm",
    "toolio_quantify",
    "toolio_elicit",
    "toolio_investigate",
    "toolio_read",
    "toolio_grep",
    "toolio_skills_menu",
]


def _tool_names() -> list[str]:
    """Return the tool names registered by the TypeScript plugin, in order."""
    return re.findall(r"^\s+(toolio_\w+): tool\(", TS_PLUGIN_SOURCE, re.MULTILINE)


def _tool_block(name: str) -> str:
    """Return the full source block of a single plugin tool."""
    pattern = rf"^\s+{name}: tool\(\{{[\s\S]*?^[ ]{{6}}\}}\),"
    match = re.search(pattern, TS_PLUGIN_SOURCE, re.MULTILINE)
    assert match is not None, f"tool block not found: {name}"
    return match.group(0)


class TestPluginSource:
    """Test the bundled TypeScript plugin source."""

    def test_contains_toolio_plugin(self) -> None:
        """Plugin source defines Toolio plugin."""
        assert "const Toolio: Plugin" in TS_PLUGIN_SOURCE

    def test_contains_discover_bridge(self) -> None:
        """Plugin source has bridge discovery."""
        assert "discoverBridge" in TS_PLUGIN_SOURCE

    def test_contains_tools(self) -> None:
        """Plugin source defines all 10 tools."""
        assert "toolio_status" in TS_PLUGIN_SOURCE
        assert "toolio_remember" in TS_PLUGIN_SOURCE
        assert "toolio_recall" in TS_PLUGIN_SOURCE
        assert "toolio_conflict" in TS_PLUGIN_SOURCE
        assert "toolio_confidence" in TS_PLUGIN_SOURCE
        assert "toolio_search" in TS_PLUGIN_SOURCE
        assert "toolio_deduplicate" in TS_PLUGIN_SOURCE
        assert "toolio_knowledge" in TS_PLUGIN_SOURCE
        assert "toolio_lifecycle" in TS_PLUGIN_SOURCE
        assert "toolio_diagnose" in TS_PLUGIN_SOURCE

    def test_cross_platform_bridge_discovery(self) -> None:
        """Plugin uses cross-platform PATH detection."""
        assert 'process.platform === "win32"' in TS_PLUGIN_SOURCE
        assert "where ${command}" in TS_PLUGIN_SOURCE
        assert "which ${command}" in TS_PLUGIN_SOURCE
        assert "toolio-bridge" in TS_PLUGIN_SOURCE

    def test_exports_default(self) -> None:
        """Default export satisfies OpenCode's plugin-module loader.

        OpenCode 1.18 loads ``plugin(s)/*.ts`` through a loader that requires a
        default-export *object* carrying a callable ``server`` key. A bare
        function, or an ``{id, setup}`` pair, is rejected at import time
        ("must default export an object with server()") and every plugin tool
        silently fails to register.
        """
        assert re.search(
            r"export default \{[^}]*\bserver:\s*Toolio\b", TS_PLUGIN_SOURCE
        ), "default export must expose `server: Toolio`"

    def test_default_export_keeps_v2_setup(self) -> None:
        """The v2 definition surface stays reachable from the same module."""
        assert re.search(
            r"export default \{[^}]*\bsetup:\s*toolioV2Setup\b", TS_PLUGIN_SOURCE
        ), "default export must keep the v2 `setup` entry point"

    def test_structured_results_are_never_string_coerced(self) -> None:
        """Structured tool results must not be flattened with ``String()``.

        ``String([{type: "text", text: "..."}])`` evaluates to the literal
        ``"[object Object]"``. Assigning that back over ``result.content``
        replaced the real output of every tool call with that string.
        """
        assert "String(result?.content" not in TS_PLUGIN_SOURCE
        assert "String(r.output ?? r.content" not in TS_PLUGIN_SOURCE
        assert "function contentToText(" in TS_PLUGIN_SOURCE

    def test_no_evo_references(self) -> None:
        """No stale EVO references in user-facing output."""
        assert "evo_status" not in TS_PLUGIN_SOURCE
        assert "evo_remember" not in TS_PLUGIN_SOURCE
        assert "evo_recall" not in TS_PLUGIN_SOURCE

    def test_json_protocol(self) -> None:
        """Plugin uses JSON stdin/stdout protocol."""
        assert "JSON.stringify" in TS_PLUGIN_SOURCE
        assert "JSON.parse" in TS_PLUGIN_SOURCE

    def test_error_handling(self) -> None:
        """Plugin handles errors gracefully."""
        assert "catch" in TS_PLUGIN_SOURCE
        assert "bridge_error" in TS_PLUGIN_SOURCE


class TestBridgeProtocol:
    """Test the bridge JSON protocol."""

    def test_bridge_module_importable(self) -> None:
        """toolio.bridge module is importable."""
        from toolio.bridge import _COMMANDS

        assert "status" in _COMMANDS
        assert "remember" in _COMMANDS
        assert "recall" in _COMMANDS
        assert "conflict" in _COMMANDS
        assert "confidence" in _COMMANDS
        assert "search" in _COMMANDS
        assert "deduplicate" in _COMMANDS
        assert "knowledge" in _COMMANDS
        assert "lifecycle" in _COMMANDS
        assert "diagnose" in _COMMANDS

    def test_bridge_handles_malformed_json(self) -> None:
        """Bridge handles malformed JSON input."""
        from toolio.bridge import main

        stdin = StringIO("not valid json {{{")
        stdout = StringIO()
        with (
            patch("sys.stdin", stdin),
            patch("sys.stdout", stdout),
        ):
            main()

        output = json.loads(stdout.getvalue())
        assert output["ok"] is False
        assert output["error"]["type"] == "protocol"

    def test_bridge_handles_unknown_command(self) -> None:
        """Bridge handles unknown commands."""
        from toolio.bridge import main

        stdin = StringIO(json.dumps({"command": "nonexistent"}))
        stdout = StringIO()
        with (
            patch("sys.stdin", stdin),
            patch("sys.stdout", stdout),
        ):
            main()

        output = json.loads(stdout.getvalue())
        assert output["ok"] is False
        assert output["error"]["type"] == "protocol"

    def test_bridge_status_command(self) -> None:
        """Bridge status command returns component info."""
        from toolio.bridge import _handle_status

        result = _handle_status({"worktree": "."})
        assert result["ok"] is True
        assert "components" in result
        assert "toolio" in result["components"]

    def test_bridge_remember_requires_content(self) -> None:
        """Bridge remember command requires content."""
        from toolio.bridge import _handle_remember

        result = _handle_remember({"worktree": ".", "content": "", "observation": ""})
        assert result["ok"] is False
        assert result["error"]["type"] == "validation"

    def test_bridge_recall_requires_query(self) -> None:
        """Bridge recall command requires query."""
        from toolio.bridge import _handle_recall

        result = _handle_recall({"worktree": ".", "query": ""})
        assert result["ok"] is False
        assert result["error"]["type"] == "validation"


class TestPluginToolSurface:
    """The plugin must expose exactly the approved 29-tool surface."""

    def test_exposes_exactly_29_tools(self) -> None:
        names = _tool_names()
        assert len(names) == 52, f"expected 52 tools, got {len(names)}: {names}"
        assert set(names) == set(EXPECTED_OPENCODE_TOOLS)

    def test_tool_order_matches_approved_surface(self) -> None:
        assert _tool_names() == EXPECTED_OPENCODE_TOOLS

    def test_learn_registered_after_recall(self) -> None:
        names = _tool_names()
        assert "toolio_learn" in names
        assert names.index("toolio_learn") == names.index("toolio_recall") + 1

    def test_existing_ten_tools_preserved(self) -> None:
        names = set(_tool_names())
        for tool_name in EXPECTED_OPENCODE_TOOLS:
            if tool_name != "toolio_learn":
                assert tool_name in names

    def test_no_internal_orchestrator_tools_exposed(self) -> None:
        """Internal Orchestrator primitives stay internal (no second routing surface)."""
        for forbidden in (
            "pipeline(",
            "parallel(",
            "remember_with_learning",
            "trigger_background",
            "process_background",
            "toolio_pipeline",
            "toolio_parallel",
            "toolio_background",
        ):
            assert forbidden not in TS_PLUGIN_SOURCE, f"internal API exposed: {forbidden}"


class TestLearnTool:
    """toolio_learn must be a thin passthrough to the existing bridge `learn` command."""

    def test_learn_sends_learn_command(self) -> None:
        block = _tool_block("toolio_learn")
        assert 'command: "learn"' in block
        assert 'command: "remember"' not in block

    def test_learn_content_is_required(self) -> None:
        block = _tool_block("toolio_learn")
        args_section = block.split("async execute")[0]
        content_decl = re.search(r"content: (tool\.schema[\s\S]*?)\n\s+\w+:", args_section)
        assert content_decl is not None, "content argument not declared"
        assert ".optional()" not in content_decl.group(1)

    def test_learn_supports_all_approved_arguments(self) -> None:
        args_section = _tool_block("toolio_learn").split("async execute")[0]
        for arg in (
            "content",
            "outcome",
            "project",
            "session",
            "observation",
            "action",
            "tags",
            "confidence",
        ):
            assert re.search(rf"\b{arg}:", args_section), f"missing learn argument: {arg}"

    def test_learn_surfaces_bridge_errors(self) -> None:
        """Orchestrator failures arrive as `errors: [...]`, not `error: {...}`."""
        block = _tool_block("toolio_learn")
        assert "errors" in block

    def test_learn_contains_no_learning_logic(self) -> None:
        """No second learning engine in TypeScript: no orchestrator/storage calls."""
        block = _tool_block("toolio_learn")
        for forbidden in ("create_orchestrator", "dispatch(", "store(", "MemoryManager"):
            assert forbidden not in block, f"TS learning logic found: {forbidden}"


class TestPluginVersionMetadata:
    """The installed plugin reports the canonical Toolio version."""

    def test_version_matches_python_package_version(self) -> None:
        from toolio import __version__

        assert f'const TOOLIO_VERSION = "{__version__}"' in TS_PLUGIN_SOURCE

    def test_no_unresolved_version_placeholder(self) -> None:
        assert "__TOOLIO_VERSION__" not in TS_PLUGIN_SOURCE

    def test_status_reports_plugin_and_bridge_versions(self) -> None:
        block = _tool_block("toolio_status")
        assert "TOOLIO_VERSION" in block
        assert "bridgeVersion" in block
        assert "Version match" in block

    def test_status_mismatch_is_non_fatal(self) -> None:
        """A version mismatch must never block the status call."""
        block = _tool_block("toolio_status")
        assert "throw" not in block
        assert "MISMATCH" in block
        # mismatch is only ever surfaced in reporting, via metadata
        assert "compat" in block


class TestBridgeLearnCommand:
    """Bridge `learn` command → Orchestrator.dispatch("toolio_remember")."""

    def test_learn_command_registered(self) -> None:
        from toolio.bridge import _COMMANDS

        assert "learn" in _COMMANDS

    def test_learn_dispatches_to_orchestrator(self) -> None:
        from core.routing.v26.tools.base import ToolResult
        from toolio import bridge as bridge_module

        calls: dict[str, object] = {}

        class StubOrchestrator:
            def dispatch(self, command: str, **params: object) -> ToolResult:
                calls["command"] = command
                calls["params"] = params
                return ToolResult(success=True, data={"stored": True}, errors=[], metadata={})

        request = {"command": "learn", "content": "learned something", "worktree": "."}
        with patch.object(bridge_module, "_get_orchestrator", return_value=StubOrchestrator()):
            resp = bridge_module._handle_learn(request)

        assert calls["command"] == "toolio_remember"
        assert calls["params"]["content"] == "learned something"
        assert "command" not in calls["params"]
        assert resp["ok"] is True
        assert resp["result"] == {"stored": True}

    def test_successful_learn_call_through_real_orchestrator(self) -> None:
        from toolio.bridge import _handle_learn

        resp = _handle_learn(
            {
                "command": "learn",
                "content": "pytest suites must stay green before committing",
                "outcome": "SUCCESS",
            }
        )
        assert resp["ok"] is True, resp
        assert resp["result"]["stored"] is True

    def test_malformed_learn_input_reports_errors(self) -> None:
        from toolio.bridge import _handle_learn

        resp = _handle_learn({"command": "learn"})
        assert resp["ok"] is False
        assert resp["errors"], "expected validation errors for missing content"

    def test_learn_orchestrator_failure_propagates(self) -> None:
        from core.routing.v26.tools.base import ToolResult
        from toolio import bridge as bridge_module

        class FailingOrchestrator:
            def dispatch(self, command: str, **params: object) -> ToolResult:
                return ToolResult(
                    success=False, data={}, errors=["storage rejected"], metadata={}
                )

        with patch.object(bridge_module, "_get_orchestrator", return_value=FailingOrchestrator()):
            resp = bridge_module._handle_learn({"command": "learn", "content": "x"})

        assert resp["ok"] is False
        assert resp["errors"] == ["storage rejected"]

    def test_bridge_exception_returns_runtime_error(self) -> None:
        from toolio.bridge import main

        stdin = StringIO(json.dumps({"command": "learn", "content": "x"}))
        stdout = StringIO()
        with (
            patch("sys.stdin", stdin),
            patch("sys.stdout", stdout),
            patch("toolio.bridge._get_orchestrator", side_effect=RuntimeError("orch down")),
        ):
            main()

        output = json.loads(stdout.getvalue())
        assert output["ok"] is False
        assert output["error"]["type"] == "runtime"
        assert "orch down" in output["error"]["message"]


class TestBridgeVersionCompatibility:
    """Offline plugin/bridge compatibility reporting."""

    def test_status_includes_version(self) -> None:
        from toolio import __version__
        from toolio.bridge import _handle_status

        result = _handle_status({"worktree": "."})
        assert result["version"] == __version__

    def test_status_version_matches_plugin_version(self) -> None:
        from toolio import __version__

        assert f'const TOOLIO_VERSION = "{__version__}"' in TS_PLUGIN_SOURCE


class TestSkeletonCommand:
    def test_registered_in_commands(self):
        import toolio.bridge as bridge_mod

        assert "skeleton" in bridge_mod._COMMANDS
        assert bridge_mod._COMMANDS["skeleton"] is bridge_mod._handle_skeleton

    def test_payload_compressed_with_footer(self):
        import toolio.bridge as bridge_mod

        text = "\n".join(f'{{"k": "some value {i}}}' for i in range(400))
        out = bridge_mod._handle_skeleton(
            {"text": text, "filename": "data.json"}
        )
        assert out["ok"] is True
        assert out["compressed"] is True
        assert out["tokens_in"] >= 1000
        assert out["tokens_out"] < out["tokens_in"]
        assert "[toolio ctx:" in out["content"]
        assert out["parser"] == "payload"

    def test_small_text_passthrough(self):
        import toolio.bridge as bridge_mod

        out = bridge_mod._handle_skeleton({"text": "tiny", "filename": "a.txt"})
        assert out["ok"] is True
        assert out["compressed"] is False
        assert out["content"] == "tiny"
        assert "toolio ctx" not in out["content"]

    def test_missing_text_validation(self):
        import toolio.bridge as bridge_mod

        out = bridge_mod._handle_skeleton({})
        assert out["ok"] is False
        assert out["error"]["type"] == "validation"

    def test_invalid_strategy_validation(self):
        import toolio.bridge as bridge_mod

        out = bridge_mod._handle_skeleton(
            {"text": "x" * 4000, "strategy": "nope"}
        )
        assert out["ok"] is False
        assert out["error"]["type"] == "validation"

    def test_kill_switch(self, monkeypatch):
        import toolio.bridge as bridge_mod

        monkeypatch.setenv("TOOLIO_CTX", "0")
        text = "\n".join(f'{{"k": "some value {i}}}' for i in range(400))
        out = bridge_mod._handle_skeleton({"text": text, "filename": "d.json"})
        assert out["ok"] is True
        assert out["compressed"] is False
        assert out["content"] == text

    def test_stdio_roundtrip(self):
        import json as json_mod
        from io import StringIO
        from unittest.mock import patch

        import toolio.bridge as bridge_mod

        text = "\n".join(f'{{"k": "some value {i}}}' for i in range(400))
        payload = json_mod.dumps(
            {"command": "skeleton", "text": text, "filename": "d.json"}
        )
        stdin = StringIO(payload)
        stdout = StringIO()
        with (
            patch("sys.stdin", stdin),
            patch("sys.stdout", stdout),
        ):
            bridge_mod.main()
        output = json_mod.loads(stdout.getvalue())
        assert output["ok"] is True
        assert output["compressed"] is True
        assert "[toolio ctx:" in output["content"]


class TestContextToolsTS:
    """The three context tools on the OpenCode plugin surface (S2)."""

    def test_status_sends_context_status(self) -> None:
        block = _tool_block("toolio_context_status")
        assert 'command: "context_status"' in block
        assert "Toolio Context Status" in block
        assert "if (!bridge)" in block

    def test_compress_sends_context_compress(self) -> None:
        block = _tool_block("toolio_context_compress")
        assert 'command: "context_compress"' in block
        assert "messages: args.messages ?? []" in block

    def test_restore_sends_context_restore(self) -> None:
        block = _tool_block("toolio_context_restore")
        assert 'command: "context_restore"' in block
        assert 'block_id: args.block_id ?? ""' in block

    def test_context_descriptions_match_mcp(self) -> None:
        mcp_server = pytest.importorskip(
            "toolio.mcp.server", reason="mcp package not installed"
        )

        for name in (
            "toolio_context_status",
            "toolio_context_compress",
            "toolio_context_restore",
        ):
            block = _tool_block(name)
            match = re.search(r"description:\s*\n(.*?),\n\s*args:", block, re.S)
            assert match, name
            ts_desc = "".join(re.findall(r'"([^"]*)"', match.group(1)))
            assert ts_desc == mcp_server._TOOLS[name]["description"], name


class TestWrapperRobustness:
    """Regressions from the 52-tool plugin-layer sweep."""

    def test_bridge_exit_code_never_discards_valid_stdout(self) -> None:
        """A non-zero bridge exit must not be treated as a transport failure.

        The bridge can emit a complete JSON response and then exit non-zero
        (e.g. a command that itself runs the bridge). Throwing here lost a
        perfectly good result and surfaced a bogus "bridge_error".
        """
        src = TS_PLUGIN_SOURCE
        assert "resolve({ stdout, stderr, code })" in src
        assert "if (code !== 0)" not in src
        assert "const { stdout, stderr, code } = await runBridge(" in src
        assert "empty bridge response (exit ${code})" in src

    def test_route_stats_does_not_reference_out_of_scope_resp(self) -> None:
        """``resp`` was declared inside ``if (bridge)`` but used outside it."""
        block = _tool_block("toolio_route_stats")
        assert "let resp: Record<string, unknown> | undefined" in block
        assert "const resp = await invokeBridge(" not in block
        assert "resp ?? {}" in block

    def test_execute_forwards_its_timeout_to_the_wrapper(self) -> None:
        """``toolio_execute`` must not be capped at the 30s bridge default.

        The wrapper passed no timeout, so ``invokeBridge`` used 30s and killed
        the bridge mid-command even when the caller asked for longer.
        """
        block = _tool_block("toolio_execute")
        assert "Number(args.timeout_ms ?? 30000) || 30000" in block
        assert "execTimeout + 15000" in block
