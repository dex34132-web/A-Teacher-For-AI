"""Smoke tests for the fake OpenCode environment."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


def test_fake_cli_version(fake_opencode):
    result = subprocess.run(
        [sys.executable, fake_opencode["bin"], "--version"],
        capture_output=True, text=True, env=fake_opencode["env"],
    )
    assert result.returncode == 0
    assert "opencode" in result.stdout
    assert "fake" in result.stdout


def test_fake_cli_config_show(fake_opencode):
    result = subprocess.run(
        [sys.executable, fake_opencode["bin"], "config", "show"],
        capture_output=True, text=True, env=fake_opencode["env"],
    )
    assert result.returncode == 0
    cfg = json.loads(result.stdout)
    assert cfg["model"] == "anthropic/claude-sonnet-4-20250514"
    assert "toolio" in cfg["mcp"]


def test_fake_cli_auth_list(fake_opencode):
    result = subprocess.run(
        [sys.executable, fake_opencode["bin"], "auth", "list"],
        capture_output=True, text=True, env=fake_opencode["env"],
    )
    assert result.returncode == 0
    providers = json.loads(result.stdout)
    assert "anthropic" in providers
    assert "groq" in providers


def test_fake_cli_mcp_list(fake_opencode):
    result = subprocess.run(
        [sys.executable, fake_opencode["bin"], "mcp", "list"],
        capture_output=True, text=True, env=fake_opencode["env"],
    )
    assert result.returncode == 0
    mcp = json.loads(result.stdout)
    assert "toolio" in mcp


def test_fake_cli_models(fake_opencode):
    result = subprocess.run(
        [sys.executable, fake_opencode["bin"], "models", "anthropic"],
        capture_output=True, text=True, env=fake_opencode["env"],
    )
    assert result.returncode == 0
    models = json.loads(result.stdout)
    assert "claude-sonnet-4-20250514" in models


def test_fake_cli_tools_list(fake_opencode):
    result = subprocess.run(
        [sys.executable, fake_opencode["bin"], "tools", "list"],
        capture_output=True, text=True, env=fake_opencode["env"],
    )
    assert result.returncode == 0
    tools = json.loads(result.stdout)
    assert "bash" in tools
    assert "read" in tools


def test_fake_cli_context_status(fake_opencode):
    result = subprocess.run(
        [sys.executable, fake_opencode["bin"], "context", "status"],
        capture_output=True, text=True, env=fake_opencode["env"],
    )
    assert result.returncode == 0
    status = json.loads(result.stdout)
    assert "blocks" in status


def test_fake_cli_plugin_list(fake_opencode):
    result = subprocess.run(
        [sys.executable, fake_opencode["bin"], "plugin", "list"],
        capture_output=True, text=True, env=fake_opencode["env"],
    )
    assert result.returncode == 0
    plugins = json.loads(result.stdout)
    assert "sample.ts" in plugins


def test_fake_cli_run_json(fake_opencode):
    result = subprocess.run(
        [sys.executable, fake_opencode["bin"], "run", "hello", "--format", "json"],
        capture_output=True, text=True, env=fake_opencode["env"],
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["type"] == "text"


def test_fake_mcp_server_initialize(fake_mcp_server):
    req = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "1.0"},
    }}
    result = subprocess.run(
        [sys.executable, fake_mcp_server],
        input=json.dumps(req) + "\n", capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0
    resp = json.loads(result.stdout.strip().splitlines()[0])
    assert resp["result"]["serverInfo"]["name"] == "fake-opencode"
    assert "tools" in resp["result"]["capabilities"]


def test_fake_mcp_server_tools_list(fake_mcp_server):
    inp = (
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}) + "\n"
        + json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}) + "\n"
    )
    result = subprocess.run(
        [sys.executable, fake_mcp_server],
        input=inp, capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0
    lines = [l for l in result.stdout.strip().splitlines() if l.strip()]
    resp = json.loads(lines[-1])
    tool_names = [t["name"] for t in resp["result"]["tools"]]
    assert "bash" in tool_names
    assert "read" in tool_names


def test_fake_mcp_server_tools_call(fake_mcp_server):
    inp = (
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}) + "\n"
        + json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "bash", "arguments": {"command": "echo hi"}}}) + "\n"
    )
    result = subprocess.run(
        [sys.executable, fake_mcp_server],
        input=inp, capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0
    lines = [l for l in result.stdout.strip().splitlines() if l.strip()]
    resp = json.loads(lines[-1])
    assert "echo hi" in resp["result"]["content"][0]["text"]


def test_fake_mcp_server_resources(fake_mcp_server):
    inp = (
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}) + "\n"
        + json.dumps({"jsonrpc": "2.0", "id": 2, "method": "resources/list", "params": {}}) + "\n"
    )
    result = subprocess.run(
        [sys.executable, fake_mcp_server],
        input=inp, capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0
    lines = [l for l in result.stdout.strip().splitlines() if l.strip()]
    resp = json.loads(lines[-1])
    uris = [r["uri"] for r in resp["result"]["resources"]]
    assert "opencode://context" in uris


def test_config_files_exist(fake_opencode):
    assert (Path(fake_opencode["config_dir"]) / "opencode.json").exists()
    assert (Path(fake_opencode["data_dir"]) / "auth.json").exists()
    cfg = json.loads((Path(fake_opencode["config_dir"]) / "opencode.json").read_text())
    assert "mcp" in cfg
    assert "toolio" in cfg["mcp"]


def test_env_vars_set(fake_opencode):
    assert "OPENCODE_CONFIG_DIR" in fake_opencode["env"]
    assert "OPENCODE_DATA_DIR" in fake_opencode["env"]
