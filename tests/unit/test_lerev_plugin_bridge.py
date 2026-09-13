"""Tests for Lerev plugin source and bridge protocol."""

from __future__ import annotations

import json
from io import StringIO
from unittest.mock import patch

import pytest

from lerev.plugin_source import TS_PLUGIN_SOURCE


class TestPluginSource:
    """Test the bundled TypeScript plugin source."""

    def test_contains_lerev_plugin(self) -> None:
        """Plugin source defines LEREV plugin."""
        assert "const LEREV: Plugin" in TS_PLUGIN_SOURCE

    def test_contains_discover_bridge(self) -> None:
        """Plugin source has bridge discovery."""
        assert "discoverBridge" in TS_PLUGIN_SOURCE

    def test_contains_tools(self) -> None:
        """Plugin source defines all three tools."""
        assert "lerev_status" in TS_PLUGIN_SOURCE
        assert "lerev_remember" in TS_PLUGIN_SOURCE
        assert "lerev_recall" in TS_PLUGIN_SOURCE

    def test_cross_platform_bridge_discovery(self) -> None:
        """Plugin uses cross-platform PATH detection."""
        assert 'process.platform === "win32"' in TS_PLUGIN_SOURCE
        assert "where lerev-bridge" in TS_PLUGIN_SOURCE
        assert "which lerev-bridge" in TS_PLUGIN_SOURCE

    def test_exports_default(self) -> None:
        """Plugin exports default."""
        assert "export default LEREV" in TS_PLUGIN_SOURCE

    def test_no_evo_references(self) -> None:
        """No stale EVO references in user-facing output."""
        # EVO_HOME is allowed as backward-compat
        # But user-facing strings should say Lerev
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
        """lerev.bridge module is importable."""
        from lerev.bridge import main, _COMMANDS
        assert "status" in _COMMANDS
        assert "remember" in _COMMANDS
        assert "recall" in _COMMANDS

    def test_bridge_handles_malformed_json(self) -> None:
        """Bridge handles malformed JSON input."""
        from lerev.bridge import main

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
        from lerev.bridge import main

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
        from lerev.bridge import _handle_status

        result = _handle_status({"worktree": "."})
        assert result["ok"] is True
        assert "components" in result
        assert "lerev" in result["components"]

    def test_bridge_remember_requires_content(self) -> None:
        """Bridge remember command requires content."""
        from lerev.bridge import _handle_remember

        result = _handle_remember({"worktree": ".", "content": "", "observation": ""})
        assert result["ok"] is False
        assert result["error"]["type"] == "validation"

    def test_bridge_recall_requires_query(self) -> None:
        """Bridge recall command requires query."""
        from lerev.bridge import _handle_recall

        result = _handle_recall({"worktree": ".", "query": ""})
        assert result["ok"] is False
        assert result["error"]["type"] == "validation"
