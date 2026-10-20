"""Wire + behaviour tests for the precision/investigate tools (Mission: always-visible tools).

ALL FIXTURES AND PAYLOADS IN THIS FILE ARE SYNTHETIC.
"""
from __future__ import annotations

import re

from school import bridge, plugin_source
from school.mcp import server as mcp_server

# --- wire registration -------------------------------------------------------

NEW_TOOLS = ("school_quantify", "school_elicit", "school_investigate")
NEW_CMDS = ("quantify", "elicit", "investigate")


class TestWireRegistration:
    def test_bridge_commands_registered(self) -> None:
        for cmd in NEW_CMDS:
            assert cmd in bridge._COMMANDS, cmd

    def test_mcp_tools_registered(self) -> None:
        for tool in NEW_TOOLS:
            assert tool in mcp_server._TOOLS, tool

    def test_ts_blocks_carry_matching_command_keys(self) -> None:
        src = plugin_source.TS_PLUGIN_SOURCE
        for tool, cmd in zip(NEW_TOOLS, NEW_CMDS, strict=True):
            m = re.search(rf"{tool}: tool\(\{{[\s\S]*?command: \"([a-z_]+)\"", src)
            assert m, f"no TS block for {tool}"
            assert m.group(1) == cmd, (tool, m.group(1))

    def test_descriptions_are_branded_like_every_tool(self) -> None:
        for tool in NEW_TOOLS:
            desc = mcp_server._TOOLS[tool]["description"]
            assert desc.startswith(f"Use {tool}"), tool
            assert "ANY kind of work" in desc, tool


# --- bridge behaviour (SYNTHETIC payloads) -----------------------------------


class TestQuantifyTool:
    def test_contradictory_schedule_never_reaches_go(self) -> None:
        res = bridge._handle_quantify(
            {
                "command": "quantify",
                "title": "Smoke",
                "currency": "USD",
                "budget": {"lines": [{"name": "signage", "amount": 40}]},
                "schedule": {
                    "start": "2026-03-15",
                    "deadline": "2026-03-01",
                    "reference": "2026-01-01",
                },
                "constraints": [
                    {
                        "id": "H1",
                        "requirement": "total money at most $200",
                        "kind": "hard",
                        "actual": "40",
                        "expected": "200",
                        "evidence_source": "smoke",
                        "evidence_kind": "machine_checked",
                        "result": "satisfied",
                        "explanation": "",
                    }
                ],
            }
        )
        assert res["ok"] is True
        assert "NO-GO" in res["report"]
        assert "SCHEDULE-1" in res["report"]
        assert "GO — every hard constraint satisfied" not in res["report"]

    def test_wrong_typed_section_is_refused_not_silently_dropped(self) -> None:
        res = bridge._handle_quantify({"command": "quantify", "budget": "nope"})
        assert res["ok"] is False
        assert "budget" in res["error"]


class TestElicitTool:
    DATA = {
        "goal": "Smoke goal",
        "unknowns": [
            {
                "id": "u-a",
                "question": "When is the deadline?",
                "variable": "deadline",
                "why_it_matters": "schedule",
                "affects": ["schedule"],
                "derivable": False,
                "must_ask_user": True,
                "if_unknown": "cannot schedule",
                "wrong_assumption_cost": "high",
                "state": "UNKNOWN",
                "critical": True,
            },
            {
                "id": "u-b",
                "question": "Who is the audience?",
                "variable": "audience",
                "why_it_matters": "acceptance",
                "affects": ["acceptance"],
                "derivable": False,
                "must_ask_user": True,
                "if_unknown": "wrong framing",
                "wrong_assumption_cost": "high",
                "state": "UNKNOWN",
                "critical": True,
            },
            {
                "id": "u-c",
                "question": "What tone?",
                "variable": "tone",
                "why_it_matters": "style",
                "affects": [],
                "derivable": False,
                "must_ask_user": False,
                "if_unknown": "minor",
                "wrong_assumption_cost": "low",
                "state": "UNKNOWN",
                "critical": False,
            },
        ],
    }

    def test_budget_enforced_and_session_round_trips(self) -> None:
        res = bridge._handle_elicit(
            {"command": "elicit", "question_budget": 2, "data": self.DATA}
        )
        assert res["ok"] is True
        assert "## Question budget" in res["report"]
        assert "budget exhausted (not success)" in res["report"]
        session = res["session"]
        assert session["presented"] == 2
        assert session["config"]["question_budget"] == 2

    def test_session_resume_does_not_reset_the_budget(self) -> None:
        first = bridge._handle_elicit(
            {"command": "elicit", "question_budget": 2, "data": self.DATA}
        )
        second = bridge._handle_elicit(
            {"command": "elicit", "session": first["session"], "data": self.DATA}
        )
        assert second["ok"] is True
        assert second["session"]["presented"] == 2, "resume must preserve the count"

    def test_invalid_budget_and_shapes_refused(self) -> None:
        bad = bridge._handle_elicit({"command": "elicit", "question_budget": "many"})
        assert bad["ok"] is False and "question_budget" in bad["error"]
        bad2 = bridge._handle_elicit({"command": "elicit", "session": [1]})
        assert bad2["ok"] is False and "session" in bad2["error"]


class TestInvestigateTool:
    CASE = {
        "id": "INV-T",
        "title": "Tool smoke",
        "scope": "smoke",
        "evidence": [],
        "hypotheses": [],
        "findings": [],
        "questions": [],
        "actions": [],
    }

    def test_report_is_honest_and_case_round_trips(self) -> None:
        res = bridge._handle_investigate({"command": "investigate", "case": self.CASE})
        assert res["ok"] is True
        assert "does not claim exhaustive discovery" in res["report"]
        assert res["case"]["id"] == "INV-T"

    def test_probe_persists_evidence_into_the_case(self) -> None:
        res = bridge._handle_investigate(
            {
                "command": "investigate",
                "case": self.CASE,
                "action": "probe",
                "probe_cmd": "echo probe-ok",
            }
        )
        assert res["ok"] is True
        assert "Probe evidence" in res["report"]
        assert res["case"]["evidence"], "probe evidence must persist into the case"

    def test_wrong_shaped_case_refused(self) -> None:
        res = bridge._handle_investigate({"command": "investigate", "case": [1, 2]})
        assert res["ok"] is False and "case" in res["error"]


class TestJsonStringArgs:
    """The packages distribution types structured args as JSON strings —
    the bridge must accept both shapes explicitly (fail-closed otherwise)."""

    def test_elicit_accepts_json_string_data(self) -> None:
        import json

        res = bridge._handle_elicit(
            {
                "command": "elicit",
                "question_budget": 2,
                "data": json.dumps(TestElicitTool.DATA),
            }
        )
        assert res["ok"] is True
        assert res["session"]["presented"] == 2

    def test_investigate_accepts_json_string_case(self) -> None:
        import json

        res = bridge._handle_investigate(
            {"command": "investigate", "case": json.dumps(TestInvestigateTool.CASE)}
        )
        assert res["ok"] is True
        assert res["case"]["id"] == "INV-T"

    def test_quantify_accepts_json_string_budget(self) -> None:
        res = bridge._handle_quantify(
            {
                "command": "quantify",
                "budget": '{"lines": [{"name": "x", "amount": 5}]}',
                "currency": "USD",
            }
        )
        assert res["ok"] is True
        assert "5.00" in res["report"]


# --- skill surface -----------------------------------------------------------


class TestNewSkills:
    SKILLS = ("precision", "investigate", "teacher")

    def test_skills_exist_with_trigger_descriptions(self) -> None:
        from pathlib import Path

        root = Path(__file__).resolve().parents[2] / "skills"
        for name in self.SKILLS:
            text = (root / name / "SKILL.md").read_text(encoding="utf-8")
            fm = text.split("---", 2)[1]
            desc = next(ln for ln in fm.splitlines() if ln.startswith("description:"))
            assert "Use when" in desc, name
            assert "not only coding" in desc, name
            body = text.split("---", 2)[2]
            assert "## Suite map" in body, name
            assert "universal" in body.lower(), name

    def test_suite_maps_resolve_to_real_tools(self) -> None:
        from pathlib import Path

        root = Path(__file__).resolve().parents[2] / "skills"
        for name in self.SKILLS:
            body = (root / name / "SKILL.md").read_text(encoding="utf-8")
            for tool in re.findall(r"`(school_[a-z_]+)`", body):
                assert tool in mcp_server._TOOLS, f"{name}: phantom tool {tool}"
