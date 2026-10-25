"""Toolio MCP server — multi-transport, fail-open.

Wraps the optional ``mcp`` SDK to expose all 52 ``toolio_*`` tools over stdio
and streamable-HTTP. Every handler is fail-open: tool errors are returned as
structured results, never as crashes. If the ``mcp`` SDK is absent, ``available``
is False and the pure-Python ``tools.call_tool`` still works standalone.

On start the server auto-installs the bundled ``packages/skills/`` into the
agent's skills directory (``~/.config/opencode/skills``) so a downloaded copy
of Toolio always shows up as skills with no manual step.
"""

from __future__ import annotations

import contextlib
import inspect
from typing import Any

from .tools import TOOL_NAMES, TOOLS, _safe_str, call_tool

try:  # optional SDK — support both mcp v1 (FastMCP) and v2 (MCPServer)
    try:
        from mcp.server.fastmcp import FastMCP  # type: ignore  # mcp < 2
    except Exception:  # noqa: BLE001
        from mcp.server.mcpserver import MCPServer as FastMCP  # type: ignore  # mcp 2.x

    SDK = True
except Exception:  # noqa: BLE001
    FastMCP = None  # type: ignore
    SDK = False


def available() -> bool:
    """True when the ``mcp`` SDK is importable."""
    return SDK


def install_bundled_skills() -> dict:
    """Copy the bundled skills into the agent's skills directory (auto-install).

    Self-contained twin of ``toolio.skills_menu.install_bundled_skills`` — the
    packages stay importable without the repo. Writes only when the target is
    missing or different; never deletes; per-skill fail-open. Returns
    ``{"synced": [...], "unchanged": [...], "errors": [...]}``.
    """
    from pathlib import Path

    src = Path(__file__).resolve().parents[2] / "skills"
    target = Path.home() / ".config" / "opencode" / "skills"
    synced: list[str] = []
    unchanged: list[str] = []
    errors: list[str] = []
    try:
        entries = sorted(p for p in src.iterdir() if p.is_dir())
    except Exception as exc:  # noqa: BLE001 — never break server start
        return {"synced": synced, "unchanged": unchanged, "errors": [_safe_str(exc)[:200]]}
    for skill_dir in entries:
        try:
            text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{skill_dir.name}: {_safe_str(exc)[:120]}")
            continue
        dest = target / skill_dir.name / "SKILL.md"
        try:
            if dest.is_file() and dest.read_text(encoding="utf-8") == text:
                unchanged.append(skill_dir.name)
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text, encoding="utf-8")
            synced.append(skill_dir.name)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{skill_dir.name}: {_safe_str(exc)[:120]}")
    return {"synced": synced, "unchanged": unchanged, "errors": errors}


def build_server(name: str = "toolio", **kwargs: Any):
    """Build a FastMCP server exposing all 52 tools. Fail-open.

    Returns the FastMCP instance, or an error dict if the SDK is missing.
    """
    if not SDK:
        return {"ok": False, "error": "mcp SDK not installed"}
    try:
        mcp = FastMCP(name, **kwargs)

        for tool_name in TOOL_NAMES:
            meta = TOOLS[tool_name]
            desc = meta["description"]

            def _make(n: str):
                def _handler(**tool_args: Any) -> dict:
                    try:
                        return call_tool(n, tool_args)
                    except Exception as exc:  # noqa: BLE001
                        return {"ok": False, "error": _safe_str(exc)[:200]}

                return _handler

            handler = _make(tool_name)
            handler.__name__ = tool_name
            handler.__doc__ = desc
            # Give the handler a flat signature matching the tool's real schema
            # so the SDK generates the correct inputSchema and accepts the flat
            # arguments clients send (instead of a wrapping ``tool_args`` object).
            try:
                props = (meta.get("schema") or {}).get("properties") or {}
                params = [
                    inspect.Parameter(
                        _safe_str(prop, "arg"),
                        inspect.Parameter.KEYWORD_ONLY,
                        default=None,
                        annotation=Any,
                    )
                    for prop in props
                ]
                handler.__signature__ = inspect.Signature(params)  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                pass
            # Register with a permissive schema (args forwarded fail-open).
            try:
                mcp.tool(name=tool_name, description=desc)(handler)
            except Exception:  # noqa: BLE001
                continue

        return mcp
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": _safe_str(exc)[:200]}


def run_stdio(server: Any) -> None:
    """Run a built server over stdio. Fail-open (no raise)."""
    try:
        if hasattr(server, "run"):
            server.run("stdio")
    except Exception:  # noqa: BLE001
        return


def run_http(server: Any, host: str = "127.0.0.1", port: int = 8765, **kw: Any) -> None:
    """Run a built server over streamable-HTTP. Fail-open (no raise)."""
    try:
        if hasattr(server, "run"):
            server.run("streamable-http", host=host, port=port, **kw)
        elif hasattr(server, "run_http"):
            server.run_http(host=host, port=port, **kw)
    except Exception:  # noqa: BLE001
        return


def main() -> None:
    import sys

    with contextlib.suppress(Exception):  # never block server start
        install_bundled_skills()
    transport = "stdio"
    if len(sys.argv) > 1 and sys.argv[1] in {"http", "stdio"}:
        transport = sys.argv[1]
    server = build_server()
    if isinstance(server, dict):  # SDK missing — degrade gracefully
        print(_safe_str(server.get("error", "server unavailable")))
        raise SystemExit(0)
    if transport == "http":
        run_http(server)
    else:
        run_stdio(server)


if __name__ == "__main__":
    main()
