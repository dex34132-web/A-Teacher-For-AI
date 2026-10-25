"""Fake OpenCode CLI — mimics opencode commands for testing.

Usage:
    python tests/fake_opencode/fake_opencode.py <command> [args...]

Supported commands:
    --version / -v / version
    run <prompt> [--model M] [--format json]
    session list / session new / session show <id>
    mcp list / mcp add <name> <cmd> / mcp remove <name>
    auth list / auth set <provider> <key>
    models [provider]
    config show / config get <key>
    tools list
    agent list
    context status / context compress
    plugin list / plugin install <name>
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("OPENCODE_CONFIG_DIR", Path.home() / ".config" / "opencode"))
DATA_DIR = Path(os.environ.get("OPENCODE_DATA_DIR", Path.home() / ".local" / "share" / "opencode"))
VERSION = "1.0.0-fake"


def _load_config() -> dict:
    cfg_path = CONFIG_DIR / "opencode.json"
    if cfg_path.exists():
        import json as _j
        try:
            return _j.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    # fallback: jsonc
    cfg_path = CONFIG_DIR / "opencode.jsonc"
    if cfg_path.exists():
        text = cfg_path.read_text(encoding="utf-8")
        # strip comments
        lines = [ln for ln in text.splitlines() if not ln.strip().startswith("//")]
        try:
            return json.loads("\n".join(lines))
        except Exception:
            return {}
    return {}


def _load_auth() -> dict:
    auth_path = DATA_DIR / "auth.json"
    if auth_path.exists():
        try:
            return json.loads(auth_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def cmd_version(args):
    print(f"opencode {VERSION}")


def cmd_run(args):
    prompt = " ".join(args.prompt) if args.prompt else ""
    if getattr(args, "format", None) == "json":
        print(json.dumps({"type": "text", "content": f"Fake response to: {prompt}"}))
    else:
        print(f"[fake-opencode] {prompt}")


def cmd_session(args):
    if args.session_cmd == "list":
        print(json.dumps([{"id": "sess-001", "title": "Test session", "messages": 5}]))
    elif args.session_cmd == "new":
        print(json.dumps({"id": "sess-new", "title": args.title or "New session"}))
    elif args.session_cmd == "show":
        print(json.dumps({"id": args.id, "messages": [{"role": "user", "content": "hello"}]}))
    else:
        print("Usage: opencode session {list|new|show}")


def cmd_mcp(args):
    if args.mcp_cmd == "list":
        cfg = _load_config()
        mcp = cfg.get("mcp", {})
        print(json.dumps(mcp))
    elif args.mcp_cmd == "add":
        print(json.dumps({"ok": True, "name": args.name, "command": args.command}))
    elif args.mcp_cmd == "remove":
        print(json.dumps({"ok": True, "name": args.name}))
    else:
        print("Usage: opencode mcp {list|add|remove}")


def cmd_auth(args):
    if args.auth_cmd == "list":
        print(json.dumps(list(_load_auth().keys())))
    elif args.auth_cmd == "set":
        print(json.dumps({"ok": True, "provider": args.provider}))
    else:
        print("Usage: opencode auth {list|set}")


def cmd_models(args):
    provider = getattr(args, "provider", None)
    models = {
        "anthropic": ["claude-sonnet-4-20250514", "claude-haiku-4-5-20251001"],
        "openai": ["gpt-4o", "gpt-4o-mini"],
        "groq": ["llama-3.3-70b-versatile"],
    }
    if provider:
        print(json.dumps(models.get(provider, [])))
    else:
        print(json.dumps(models))


def cmd_config(args):
    cfg = _load_config()
    if args.config_cmd == "show":
        print(json.dumps(cfg, indent=2))
    elif args.config_cmd == "get":
        keys = args.key.split(".")
        val = cfg
        for k in keys:
            val = val.get(k, {}) if isinstance(val, dict) else None
        print(json.dumps(val))


def cmd_tools(args):
    print(json.dumps(["bash", "read", "write", "edit", "grep", "glob", "webfetch", "task"]))


def cmd_agent(args):
    print(json.dumps(["build", "plan", "explore", "general"]))


def cmd_context(args):
    if args.context_cmd == "status":
        print(json.dumps({"blocks": 0, "tokens_saved": 0, "mode": "dcp"}))
    elif args.context_cmd == "compress":
        print(json.dumps({"blocks_added": 0, "tokens_saved": 0}))
    else:
        print("Usage: opencode context {status|compress}")


def cmd_plugin(args):
    if args.plugin_cmd == "list":
        plugins_dir = CONFIG_DIR / "plugins"
        if plugins_dir.exists():
            print(json.dumps([p.name for p in plugins_dir.iterdir()]))
        else:
            print(json.dumps([]))
    elif args.plugin_cmd == "install":
        print(json.dumps({"ok": True, "name": args.name}))
    else:
        print("Usage: opencode plugin {list|install}")


def main():
    parser = argparse.ArgumentParser(prog="opencode", description="Fake OpenCode CLI")
    parser.add_argument("--version", "-v", action="store_true")
    sub = parser.add_subparsers(dest="subcommand")

    # run
    p = sub.add_parser("run")
    p.add_argument("prompt", nargs="*")
    p.add_argument("--model", default=None)
    p.add_argument("--format", default=None)
    p.set_defaults(func=cmd_run)

    # session
    p = sub.add_parser("session")
    p.add_argument("session_cmd", choices=["list", "new", "show"])
    p.add_argument("id", nargs="?")
    p.add_argument("--title", default=None)
    p.set_defaults(func=cmd_session)

    # mcp
    p = sub.add_parser("mcp")
    p.add_argument("mcp_cmd", choices=["list", "add", "remove"])
    p.add_argument("name", nargs="?")
    p.add_argument("command", nargs="*")
    p.set_defaults(func=cmd_mcp)

    # auth
    p = sub.add_parser("auth")
    p.add_argument("auth_cmd", choices=["list", "set"])
    p.add_argument("provider", nargs="?")
    p.add_argument("key", nargs="?")
    p.set_defaults(func=cmd_auth)

    # models
    p = sub.add_parser("models")
    p.add_argument("provider", nargs="?")
    p.set_defaults(func=cmd_models)

    # config
    p = sub.add_parser("config")
    p.add_argument("config_cmd", choices=["show", "get"])
    p.add_argument("key", nargs="?")
    p.set_defaults(func=cmd_config)

    # tools
    p = sub.add_parser("tools")
    p.add_argument("tools_cmd", choices=["list"])
    p.set_defaults(func=cmd_tools)

    # agent
    p = sub.add_parser("agent")
    p.add_argument("agent_cmd", choices=["list"])
    p.set_defaults(func=cmd_agent)

    # context
    p = sub.add_parser("context")
    p.add_argument("context_cmd", choices=["status", "compress"])
    p.set_defaults(func=cmd_context)

    # plugin
    p = sub.add_parser("plugin")
    p.add_argument("plugin_cmd", choices=["list", "install"])
    p.add_argument("name", nargs="?")
    p.set_defaults(func=cmd_plugin)

    args = parser.parse_args()
    if args.version:
        cmd_version(args)
        return
    if not args.subcommand:
        print(f"opencode {VERSION}")
        return
    if not hasattr(args, "func"):
        print(f"NO FUNC for {args.subcommand}")
        return
    args.func(args)


if __name__ == "__main__":
    main()
