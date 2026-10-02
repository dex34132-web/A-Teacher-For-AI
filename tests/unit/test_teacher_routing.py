"""TS-source contract tests for the adaptive routing loop (Phase 1)."""

import re

from teacher.plugin_source import TS_PLUGIN_SOURCE


class TestRoutingCoreHelpers:
    def test_constants_present(self):
        assert "const ROUTE_TIMEOUT_MS = 10000" in TS_PLUGIN_SOURCE
        assert "const ROUTE_STATS_MAX_LINES = 2000" in TS_PLUGIN_SOURCE

    def test_engage_mapping(self):
        match = re.search(
            r"function engageFor\(severity: string\): string \{\n(.*?)\n\}",
            TS_PLUGIN_SOURCE,
            re.S,
        )
        assert match, "engageFor missing"
        body = match.group(1)
        assert '"light" ? "skill" : "both"' in body.replace(" ", " ").replace(
            "  ", ""
        ) or ('"light"' in body and '"skill"' in body and '"both"' in body)

    def test_evidence_append_and_cap(self):
        assert "function appendEvidence(" in TS_PLUGIN_SOURCE
        assert "routing-stats.jsonl" in TS_PLUGIN_SOURCE
        assert "ROUTE_STATS_MAX_LINES" in TS_PLUGIN_SOURCE
        assert "appendFileSync" in TS_PLUGIN_SOURCE
        assert "mkdirSync" in TS_PLUGIN_SOURCE

    def test_knobs_reader(self):
        assert "function readKnobs(" in TS_PLUGIN_SOURCE
        assert "routing.json" in TS_PLUGIN_SOURCE
        assert "skip_tools" in TS_PLUGIN_SOURCE
        assert "force_tools" in TS_PLUGIN_SOURCE
        assert "statSync" in TS_PLUGIN_SOURCE  # mtime cache check

    def test_knobs_used_in_recall_path(self):
        # recallForExecution reads knobs and applies them to the bridge call.
        idx = TS_PLUGIN_SOURCE.index("const recallForExecution")
        end = TS_PLUGIN_SOURCE.index("return {", idx)
        block = TS_PLUGIN_SOURCE[idx:end]
        assert "readKnobs" in block
        assert "confidence_threshold" in block
        assert "knobs.recall_threshold" in block

    def test_before_hook_skip_force(self):
        idx = TS_PLUGIN_SOURCE.index('"tool.execute.before"')
        block = TS_PLUGIN_SOURCE[idx : TS_PLUGIN_SOURCE.index('"tool.execute.after"')]
        assert "skip_tools" in block
        assert "force_tools" in block

    def test_after_hook_tracks_evidence_and_start_time(self):
        idx = TS_PLUGIN_SOURCE.index('"tool.execute.after"')
        end = TS_PLUGIN_SOURCE.index('"chat.message"', idx)
        block = TS_PLUGIN_SOURCE[idx:end]
        assert 'kind: "exec"' in block
        assert "executionStart" in block
        assert "Date.now()" in block

    def test_routing_marker_suffix(self):
        # After-hook appends the routing marker from metadata.engagement.
        idx = TS_PLUGIN_SOURCE.index('"tool.execute.after"')
        end = TS_PLUGIN_SOURCE.index('"chat.message"', idx)
        block = TS_PLUGIN_SOURCE[idx:end]
        assert "routing: " in block
        assert "metadata" in block

    def test_node_fs_imports_extended(self):
        match = re.search(r'import \{ ([^}]+) \} from "node:fs"', TS_PLUGIN_SOURCE)
        assert match, "node:fs import missing"
        names = {n.strip() for n in match.group(1).split(",")}
        assert {"existsSync", "appendFileSync", "readFileSync", "writeFileSync",
                "mkdirSync", "statSync"} <= names
