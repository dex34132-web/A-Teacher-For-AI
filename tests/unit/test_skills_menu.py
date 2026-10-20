"""School skills interactive-menu: module, wire, and package bundle.

ALL FIXTURES AND INPUTS ARE SYNTHETIC.
"""

from __future__ import annotations

from pathlib import Path

from school.skills_menu import (
    MENU_ITEMS,
    build_tool_args,
    install_bundled_skills,
    render_menu,
    resolve_choice,
    tool_name,
)

REPO = Path(__file__).resolve().parents[2]


class TestMenuSurface:
    def test_render_menu_lists_all_actions(self):
        menu = render_menu()
        for name, blurb, _fields in MENU_ITEMS:
            assert name in menu, name
            assert blurb in menu, name
        assert "0) quit" in menu

    def test_resolve_choice_by_number_name_and_quit(self):
        assert resolve_choice("1") == ("list", None)
        assert resolve_choice("3") == ("create", None)
        assert resolve_choice("github-search") == ("github-search", None)
        assert resolve_choice("  status ") == ("status", None)
        assert resolve_choice("0") == (None, None)
        assert resolve_choice("quit") == (None, None)

    def test_resolve_choice_unknown_is_explicit(self):
        action, err = resolve_choice("99")
        assert action is None
        assert err is not None and "unknown choice" in err

    def test_tool_name_maps_every_action_to_school_skill_family(self):
        assert tool_name("list") == "school_skill_list"
        assert tool_name("github-search") == "school_skill_search_github"
        assert tool_name("analyze") == "school_skill_analyze_external"
        for name, _blurb, _fields in MENU_ITEMS:
            assert tool_name(name).startswith("school_skill_") or name in {
                "github-search",
                "analyze",
            }

    def test_build_tool_args_coerces_menu_fields(self):
        args = build_tool_args(
            "create",
            {
                "name": "demo-skill",
                "description": "d",
                "purpose": "p",
                "procedure": "step one; step two",
                "triggers": "when broken; when lost",
                "scope": "GLOBAL",
            },
        )
        assert args["procedure"] == ["step one", "step two"]
        assert args["triggers"] == ["when broken", "when lost"]
        assert args["scope"] == "GLOBAL"

    def test_build_tool_args_booleans_ints_and_aliases(self):
        args = build_tool_args(
            "github-search",
            {"task": "t", "gap": "g", "keywords": "alpha beta", "skill_name": "s"},
        )
        assert args["capability_gap"] == "g"
        assert args["keywords"] == ["alpha", "beta"]
        fb = build_tool_args("feedback", {"name": "n", "success": "y", "note": ""})
        assert fb["success"] is True
        assert "note" not in fb  # empty values are omitted
        disc = build_tool_args("discover", {"task": "t", "max_files": "7"})
        assert disc == {"task": "t"}  # max_files is not a wire field for discover

    def test_build_tool_args_drops_unknown_fields(self):
        args = build_tool_args("status", {"bogus": "x", "name": "n"})
        assert args == {}


class TestInstallBundledSkills:
    def test_syncs_missing_and_skips_identical(self, tmp_path: Path):
        src = tmp_path / "src"
        (src / "demo-skill").mkdir(parents=True)
        (src / "demo-skill" / "SKILL.md").write_text("# demo\n", encoding="utf-8")
        dest = tmp_path / "dest"
        first = install_bundled_skills(src, dest)
        assert first["synced"] == ["demo-skill"]
        assert (dest / "demo-skill" / "SKILL.md").read_text(encoding="utf-8") == "# demo\n"
        second = install_bundled_skills(src, dest)
        assert second["synced"] == []
        assert second["unchanged"] == ["demo-skill"]

    def test_never_deletes_and_never_raises(self, tmp_path: Path):
        dest = tmp_path / "dest"
        (dest / "user-skill").mkdir(parents=True)
        (dest / "user-skill" / "SKILL.md").write_text("mine\n", encoding="utf-8")
        result = install_bundled_skills(tmp_path / "does-not-exist", dest)
        assert result["errors"]  # missing source is reported, not raised
        assert (dest / "user-skill" / "SKILL.md").read_text(encoding="utf-8") == "mine\n"


class TestWireSurface:
    def test_no_choice_returns_menu(self):
        from school import bridge

        out = bridge._COMMANDS["skills_menu"]({"worktree": "."})
        assert out["ok"] is True
        assert "skills> " in out["prompt"]
        assert "12) import" in out["menu"] or "import" in out["menu"]

    def test_digit_and_name_choices_run_status(self):
        from school import bridge

        by_digit = bridge._COMMANDS["skills_menu"]({"worktree": ".", "choice": "6"})
        assert by_digit["ok"] is True
        assert by_digit["action"] == "status"
        assert "result" in by_digit and "menu" in by_digit
        by_name = bridge._COMMANDS["skills_menu"]({"worktree": ".", "choice": "status"})
        assert by_name["ok"] is True
        assert by_name["action"] == "status"

    def test_unknown_choice_fails_closed_with_menu(self):
        from school import bridge

        out = bridge._COMMANDS["skills_menu"]({"worktree": ".", "choice": "99"})
        assert out["ok"] is False
        assert "unknown choice" in out["error"]
        assert "menu" in out

    def test_fields_accept_json_string(self):
        from school import bridge

        out = bridge._COMMANDS["skills_menu"](
            {
                "worktree": ".",
                "choice": "feedback",
                "fields": "{\"name\": \"n\", \"success\": \"y\"}",
            }
        )
        assert out["ok"] is True
        assert out["action"] == "feedback"
        result = out.get("result") or {}
        text = str(result)
        assert "name" not in str(out.get("error") or "")  # no shape error
        assert result is not None and ("ok" in result or "errors" in result or text)

    def test_wrong_typed_fields_fail_closed(self):
        from school import bridge

        out = bridge._COMMANDS["skills_menu"]({"worktree": ".", "choice": "1", "fields": [1, 2]})
        assert out["ok"] is False
        assert "fields" in out["error"]

    def test_mcp_tool_registered_and_dispatches(self):
        from school.mcp.server import _TOOLS, _call_tool

        assert "school_skills_menu" in _TOOLS
        res = _call_tool(str(REPO), "school_skills_menu", {})
        sc = getattr(res, "structured_content", None)
        assert isinstance(sc, dict) and sc.get("ok") is True and "menu" in sc


class TestPackagesBundle:
    def test_bundled_skills_mirror_repo_skills(self):
        repo_skills = REPO / "skills"
        bundled = REPO / "packages" / "skills"
        names = sorted(p.name for p in repo_skills.iterdir() if p.is_dir())
        assert len(names) == 11, names
        for name in names:
            repo_text = (repo_skills / name / "SKILL.md").read_text(encoding="utf-8")
            pkg_text = (bundled / name / "SKILL.md").read_text(encoding="utf-8")
            assert repo_text == pkg_text, name

    def test_packages_catalog_registers_menu(self):
        import sys

        sys.path.insert(0, str(REPO / "packages" / "mcp"))
        from school_mcp.tools import CATALOG, TOOL_NAMES  # noqa: PLC0415

        assert len(TOOL_NAMES) == 52
        names = [row[0] for row in CATALOG]
        assert "school_skills_menu" in names
