"""Shared skills interactive-menu surface.

One menu definition, one dispatch table — so the menu shows up identically
wherever School is installed:

- terminal: ``school skills`` (``school/cli.py`` renders this table)
- MCP:      the ``school_skills_menu`` tool (turn-based: choice + fields)
- bridge:   the ``skills_menu`` wire command
- packages: the downloadable distribution ships this module and the skills

It also owns ``install_bundled_skills`` — the auto-install that runs when an
MCP server starts, so a downloaded copy of School always shows up as skills
with no manual step.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MENU_ITEMS: tuple[tuple[str, str, tuple[tuple[str, str, str], ...]], ...] = (
    ("list", "List local skills (offline)", ()),
    ("search", "Search local skills", (("query", "Capability query", ""),)),
    (
        "create",
        "Create/validate/register a skill",
        (
            ("name", "Skill name (kebab-case)", ""),
            ("description", "One-line capability summary", ""),
            ("purpose", "Why it exists", ""),
            ("procedure", "Ordered steps (separate with ;)", ""),
            ("triggers", "When to use (separate with ;)", ""),
            ("scope", "Scope GLOBAL|AGENT|PROJECT|SESSION", "AGENT"),
        ),
    ),
    (
        "use",
        "Retrieve a skill + record reuse",
        (
            ("name", "Skill name (blank = search by query)", ""),
            ("query", "Task query (when name blank)", ""),
        ),
    ),
    (
        "feedback",
        "Report success/failure for a skill",
        (
            ("name", "Skill name", ""),
            ("success", "Did the reuse work? y/n", ""),
            ("note", "Optional note", ""),
        ),
    ),
    ("status", "Skill engine counters + health", ()),
    (
        "evolve",
        "Consolidate / revise / recompute",
        (
            ("action", "consolidate | revise | recompute", "consolidate"),
            ("name", "Skill to revise (blank otherwise)", ""),
        ),
    ),
    (
        "github-search",
        "Bounded GitHub search (read-only)",
        (
            ("task", "Current task", ""),
            ("gap", "Capability gap", ""),
            ("keywords", "Keywords (space-separated)", ""),
            ("skill_name", "Known skill name", ""),
        ),
    ),
    (
        "discover",
        "Skill-like files in GitHub results (read-only)",
        (
            ("task", "Current task", ""),
            ("gap", "Capability gap", ""),
            ("keywords", "Keywords (space-separated)", ""),
            ("max_files", "Max files", "5"),
        ),
    ),
    (
        "analyze",
        "Budgeted analysis of one GitHub candidate",
        (
            ("owner", "Repository owner", ""),
            ("repo", "Repository name", ""),
            ("file_path", "Skill file path", ""),
            ("task", "Capability gap context", ""),
        ),
    ),
    (
        "compare",
        "Compare a candidate against local skills",
        (
            ("owner", "Repository owner", ""),
            ("repo", "Repository name", ""),
            ("file_path", "Skill file path", ""),
        ),
    ),
    (
        "import",
        "Import an approved candidate (asks approval)",
        (
            ("owner", "Repository owner", ""),
            ("repo", "Repository name", ""),
            ("file_path", "Skill file path", ""),
            ("approve", "Approve? y/n", "n"),
            ("acknowledge_license", "Acknowledge license? y/n", "n"),
        ),
    ),
)

QUIT_CHOICES = frozenset({"0", "q", "quit", "exit"})

# menu action -> orchestrator tool suffix (school_<suffix>)
_TOOL_SUFFIX: dict[str, str] = {
    "github-search": "skill_search_github",
    "analyze": "skill_analyze_external",
}

# menu field name -> tool argument name
_FIELD_ALIASES: dict[str, str] = {"gap": "capability_gap"}

# fields that arrive as one string but mean a list
_LIST_SPLIT: dict[str, str] = {
    "keywords": " ",
    "procedure": ";",
    "triggers": ";",
    "inputs": ";",
    "constraints": ";",
    "examples": ";",
    "tags": ";",
}
_BOOL_FIELDS = frozenset({"success", "approve", "acknowledge_license", "include_unusable"})
_INT_FIELDS = frozenset({"limit", "max_files"})

# tool arguments accepted per action (wire schema names; extras are dropped)
_ACTION_FIELDS: dict[str, tuple[str, ...]] = {
    "list": ("state", "scope", "limit"),
    "search": ("query", "limit", "include_unusable", "agent_id", "project", "session"),
    "create": (
        "name",
        "description",
        "purpose",
        "triggers",
        "inputs",
        "procedure",
        "expected_output",
        "constraints",
        "examples",
        "scope",
        "tags",
        "agent_id",
        "project",
        "session",
    ),
    "use": ("name", "query", "agent_id", "project", "session"),
    "feedback": ("name", "success", "note", "agent_id"),
    "status": (),
    "evolve": ("action", "name", "changes", "agent_id"),
    "github-search": ("task", "capability_gap", "keywords", "skill_name"),
    "discover": ("task", "capability_gap", "keywords", "skill_name"),
    "analyze": ("owner", "repo", "file_path", "task"),
    "compare": ("owner", "repo", "file_path"),
    "import": (
        "owner",
        "repo",
        "file_path",
        "approve",
        "scope",
        "acknowledge_license",
        "agent_id",
        "project",
        "session",
    ),
}


def render_menu() -> str:
    """The numbered menu text — identical on every surface."""
    lines = ["school skills \u2014 interactive menu", ""]
    for i, (name, blurb, _fields) in enumerate(MENU_ITEMS, start=1):
        lines.append(f"  {i:2}) {name:<13} {blurb}")
    lines.append("   0) quit")
    return "\n".join(lines)


def resolve_choice(pick: object) -> tuple[str | None, str | None]:
    """Map a menu choice (number or action name) to an action name.

    Returns ``(action, None)``, ``(None, None)`` for quit, or
    ``(None, error)`` when the choice is unknown. Never raises.
    """
    text = str(pick or "").strip()
    if text.lower() in QUIT_CHOICES:
        return None, None
    if text.isdigit() and 1 <= int(text) <= len(MENU_ITEMS):
        return MENU_ITEMS[int(text) - 1][0], None
    for name, _blurb, _fields in MENU_ITEMS:
        if text == name:
            return name, None
    return None, f"unknown choice: {text!r}"


def tool_name(action: str) -> str:
    """Orchestrator tool for a menu action (``school_skill_*`` family)."""
    return "school_" + _TOOL_SUFFIX.get(action, f"skill_{action}")


def _yes(value: object) -> bool:
    return str(value or "").strip().lower() in {"y", "yes", "true", "1"}


def _split(value: object, sep: str) -> list[str]:
    return [s.strip() for s in str(value or "").split(sep) if s.strip()]


def _coerce(action: str, key: str, value: Any) -> Any:
    if key in _LIST_SPLIT:
        if isinstance(value, (list, tuple)):
            return [str(v) for v in value if str(v).strip()]
        return _split(value, _LIST_SPLIT[key])
    if key in _BOOL_FIELDS:
        if isinstance(value, bool):
            return value
        return _yes(value)
    if key in _INT_FIELDS:
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return None
    if key == "changes" and isinstance(value, str):
        try:
            parsed = json.loads(value)
        except Exception:  # noqa: BLE001 — keep the raw string for the tool to judge
            return value
        return parsed
    return value


def build_tool_args(action: str, values: dict[str, Any]) -> dict[str, Any]:
    """Coerce menu field values into tool args for :func:`tool_name`.

    Accepts plain strings (interactive / wire) and native lists, bools and
    ints. Empty values are omitted so tool defaults apply. Values whose names
    are not accepted by the action's tool schema are dropped (fail-closed
    silence at the field level, exactly like the wire boundary).
    """
    vals = dict(values or {})
    args: dict[str, Any] = {}
    for key in _ACTION_FIELDS.get(action, ()):
        if key in vals:
            raw = vals[key]
        elif key in _FIELD_ALIASES.values():
            alias = next((a for a, t in _FIELD_ALIASES.items() if t == key), None)
            raw = vals.get(alias) if alias else None
        else:
            raw = None
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            continue
        coerced = _coerce(action, key, raw)
        if coerced is None or coerced == [] or coerced == "":
            continue
        args[key] = coerced
    return args


def install_bundled_skills(
    skills_src: Path | None = None,
    dest: Path | None = None,
) -> dict[str, Any]:
    """Copy the bundled skills into the agent's skills directory.

    Runs on MCP server start so a downloaded copy of School always shows up
    as skills with no manual step. Writes only when the target is missing or
    different; never deletes; per-skill fail-open. Returns
    ``{"synced": [...], "unchanged": [...], "errors": [...]}``.
    """
    src = Path(skills_src) if skills_src else Path(__file__).resolve().parents[1] / "skills"
    target = Path(dest) if dest else Path.home() / ".config" / "opencode" / "skills"
    synced: list[str] = []
    unchanged: list[str] = []
    errors: list[str] = []
    try:
        entries = sorted(p for p in src.iterdir() if p.is_dir())
    except Exception as exc:  # noqa: BLE001 — never break server start
        return {"synced": synced, "unchanged": unchanged, "errors": [f"{src}: {exc}"]}
    for skill_dir in entries:
        try:
            text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{skill_dir.name}: {exc}")
            continue
        target_file = target / skill_dir.name / "SKILL.md"
        try:
            if target_file.is_file() and target_file.read_text(encoding="utf-8") == text:
                unchanged.append(skill_dir.name)
                continue
            target_file.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_text(text, encoding="utf-8")
            synced.append(skill_dir.name)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{skill_dir.name}: {exc}")
    return {"synced": synced, "unchanged": unchanged, "errors": errors}
