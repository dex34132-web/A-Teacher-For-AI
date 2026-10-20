"""CLI `skills` subcommands: local list/search (offline) + fail-closed exits.

No network: these paths only touch the local registry under the cwd.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

from core.skillgen.registry import registry_for
from core.skillgen.types import Skill, SkillScope, SkillState
from school.cli import main


def _seed(worktree: Path) -> Skill:
    registry = registry_for(str(worktree))
    skill = Skill(
        name="agent-markdown-skill",
        description="Agent markdown capability for tidy tables",
        purpose="Prove the local CLI search works",
        triggers=["markdown", "tables"],
        procedure=["Format the table"],
        state=SkillState.ACTIVE,
        scope=SkillScope.AGENT,
        agent_id="opencode",
    )
    registry.add(skill)
    registry.save()
    return skill


class TestSkillsList:
    def test_list_prints_seeded_skills(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _seed(tmp_path)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["school", "skills", "list"])
        main()
        report = json.loads(capsys.readouterr().out)
        assert report["ok"] is True
        assert report["count"] == 1
        assert report["skills"][0]["name"] == "agent-markdown-skill"
        assert report["skills"][0]["state"] == "active"
        assert report["skills"][0]["source"] == "local"

    def test_list_on_empty_registry_is_ok_zero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["school", "skills", "list"])
        main()
        report = json.loads(capsys.readouterr().out)
        assert report["ok"] is True
        assert report["count"] == 0
        assert report["skills"] == []


class TestSkillsSearch:
    def test_search_returns_scope_visible_match(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _seed(tmp_path)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["school", "skills", "search", "markdown tables"])
        main()
        report = json.loads(capsys.readouterr().out)
        assert report["ok"] is True
        assert [m["name"] for m in report["matches"]] == ["agent-markdown-skill"]
        assert report["matches"][0]["score"] > 0.0

    def test_search_miss_returns_empty_matches(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _seed(tmp_path)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["school", "skills", "search", "quantum rocketry"])
        main()
        report = json.loads(capsys.readouterr().out)
        assert report["ok"] is True
        assert report["matches"] == []


class TestSkillsFailClosed:
    def test_missing_action_exits_nonzero(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["school", "skills"])
        monkeypatch.setattr("sys.stdin", io.StringIO(""))
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 1
        out = capsys.readouterr()
        assert "interactive menu" in out.out
        assert "no interactive input" in out.err

    def test_unknown_action_rejected_by_argparse(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["school", "skills", "frobnicate"])
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 2
        assert "invalid choice" in capsys.readouterr().err


class TestSkillsMenu:
    """Bare `school skills` opens an interactive menu over all 12 actions."""

    ACTIONS = (
        "list",
        "search",
        "create",
        "use",
        "feedback",
        "status",
        "evolve",
        "github-search",
        "discover",
        "analyze",
        "compare",
        "import",
    )

    def _run_menu(
        self,
        monkeypatch: pytest.MonkeyPatch,
        stdin_text: str,
        capsys: pytest.CaptureFixture[str],
    ) -> tuple[int, str]:
        monkeypatch.setattr(sys, "argv", ["school", "skills"])
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin_text))
        with pytest.raises(SystemExit) as excinfo:
            main()
        return excinfo.value.code, capsys.readouterr().out

    def test_menu_lists_all_twelve_actions_and_quits(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code, out = self._run_menu(monkeypatch, "0\n", capsys)
        assert code == 0
        assert "interactive menu" in out
        for name in self.ACTIONS:
            assert name in out
        assert "bye" in out

    def test_menu_runs_list_via_pipe(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _seed(tmp_path)
        code, out = self._run_menu(monkeypatch, "1\n0\n", capsys)
        assert code == 0
        assert "agent-markdown-skill" in out

    def test_menu_status_action_returns_engine_health(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        code, out = self._run_menu(monkeypatch, "6\n0\n", capsys)
        assert code == 0
        assert '"ok"' in out

    def test_menu_quit_by_name(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code, out = self._run_menu(monkeypatch, "quit\n", capsys)
        assert code == 0
        assert "bye" in out

    def test_menu_unknown_choice_reprompts(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code, out = self._run_menu(monkeypatch, "99\n0\n", capsys)
        assert code == 0
        assert "unknown choice" in out


class TestSkillRegistryActions:
    """Parser-level coverage for create/use/feedback/status/evolve."""

    def test_status_subcommand_runs(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["school", "skills", "status"])
        main()
        out = json.loads(capsys.readouterr().out)
        assert out.get("ok") is True

    def test_feedback_requires_outcome(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["school", "skills", "feedback", "--name", "x"])
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 2

    def test_create_requires_core_fields(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["school", "skills", "create", "my-skill"])
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 2

    def test_evolve_rejects_bad_changes_json(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "school",
                "skills",
                "evolve",
                "--action",
                "revise",
                "--name",
                "x",
                "--changes",
                "not-json",
            ],
        )
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 2
        assert "valid JSON" in capsys.readouterr().err
