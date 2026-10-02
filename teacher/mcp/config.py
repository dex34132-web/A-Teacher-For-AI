"""Client configuration presets for the Teacher MCP server.

Builds copy-paste configuration for common MCP clients. Does NOT import
the ``mcp`` SDK — ``teacher mcp config`` must work without the optional
dependency installed.
"""

from __future__ import annotations

import json
import sys
from typing import Any

#: Config file (or location) each preset belongs to.
CLIENT_PATHS: dict[str, str] = {
    "generic": "any MCP client that speaks the mcpServers schema",
    "claude": ".mcp.json (project) or ~/.claude.json (local/user scope)",
    "codex": "~/.codex/config.toml",
    "opencode": "~/.config/opencode/opencode.jsonc",
    "cursor": "~/.cursor/mcp.json or .cursor/mcp.json",
    "windsurf": "~/.codeium/windsurf/mcp_config.json",
    "cline": (
        "cline_mcp_settings.json — VS Code: %APPDATA%/Code/User/globalStorage/"
        "saoudrizwan.claude-dev/settings/, CLI: ~/.cline/data/settings/"
    ),
    "roo": "mcp_settings.json (Roo Code → Settings → MCP Servers → Edit Global Config)",
    "gemini": "~/.gemini/settings.json (user) or .gemini/settings.json (project)",
    "vscode": ".vscode/mcp.json",
}

_FORMATS: dict[str, str] = {name: ("toml" if name == "codex" else "json")
                            for name in CLIENT_PATHS}


def _command(python: str | None = None) -> tuple[str, list[str]]:
    return (python or sys.executable, ["-m", "teacher.mcp"])


def _toml_string(value: str) -> str:
    """Render *value* as a valid TOML basic string (escapes \\ and ")."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _mcp_servers_block(exe: str, args: list[str], **extra: Any) -> dict[str, Any]:
    server: dict[str, Any] = {"command": exe, "args": args, **extra}
    return {"mcpServers": {"teacher": server}}


def build_client_config(client: str, python: str | None = None) -> dict[str, Any]:
    """Return preset metadata for *client*.

    Returns a dict with keys: ``name``, ``path``, ``format``, ``config``
    (the exact text to paste), and ``cli`` (optional one-liner command).
    Raises ``ValueError`` for unknown clients.
    """
    exe, args = _command(python)
    name = client.lower().strip()
    if name not in CLIENT_PATHS:
        supported = ", ".join(sorted(CLIENT_PATHS))
        raise ValueError(f"Unknown MCP client {client!r}. Supported: {supported}")

    cli: str | None = None
    if name == "codex":
        # TOML basic strings: escape backslashes and quotes so Windows
        # paths (C:\Users\...) stay valid TOML.
        args_toml = ", ".join(_toml_string(a) for a in args)
        config = f"[mcp_servers.teacher]\ncommand = {_toml_string(exe)}\nargs = [{args_toml}]\n"
        cli = f"codex mcp add teacher -- {exe} -m teacher.mcp"
    elif name == "claude":
        block = _mcp_servers_block(exe, args, type="stdio")
        config = json.dumps(block, indent=2)
        cli = f"claude mcp add teacher -- {exe} -m teacher.mcp"
    elif name == "opencode":
        block = {
            "$schema": "https://opencode.ai/config.json",
            "mcp": {
                "teacher": {
                    "type": "local",
                    "command": [exe, *args],
                    "enabled": True,
                }
            },
        }
        config = json.dumps(block, indent=2)
    elif name == "vscode":
        block = {"servers": {"teacher": {"type": "stdio", "command": exe, "args": args}}}
        config = json.dumps(block, indent=2)
    elif name == "cline":
        block = _mcp_servers_block(
            exe, args, disabled=False, autoApprove=[]
        )
        config = json.dumps(block, indent=2)
    elif name == "gemini":
        block = _mcp_servers_block(exe, args)
        config = json.dumps(block, indent=2)
        cli = f"gemini mcp add teacher {exe} -m teacher.mcp"
    else:  # generic, cursor, windsurf, roo — shared mcpServers schema
        block = _mcp_servers_block(exe, args, type="stdio")
        config = json.dumps(block, indent=2)

    result: dict[str, Any] = {
        "name": name,
        "path": CLIENT_PATHS[name],
        "format": _FORMATS[name],
        "config": config,
    }
    if cli:
        result["cli"] = cli
    return result
