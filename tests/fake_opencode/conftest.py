"""Pytest fixtures for the fake OpenCode environment.

Usage in tests:

    def test_something(fake_opencode):
        env = fake_opencode  # dict with paths + env vars
        # env["bin"] -> path to fake_opencode.py
        # env["config_dir"] -> ~/.config/opencode
        # env["data_dir"] -> ~/.local/share/opencode
        # env["env"] -> dict of env vars to pass to subprocesses
        ...
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

FAKE_DIR = Path(__file__).resolve().parent
CONFIG_SRC = FAKE_DIR / "config"
PLUGIN_SRC = FAKE_DIR / "plugins"


@pytest.fixture
def fake_opencode(tmp_path):
    """Set up a fully isolated fake OpenCode environment."""
    config_dir = tmp_path / ".config" / "opencode"
    data_dir = tmp_path / ".local" / "share" / "opencode"
    plugins_dir = config_dir / "plugins"
    skills_dir = config_dir / "skills"
    config_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    plugins_dir.mkdir(parents=True, exist_ok=True)
    skills_dir.mkdir(parents=True, exist_ok=True)

    # Copy config templates
    for f in CONFIG_SRC.iterdir():
        if f.is_file():
            if f.name == "auth.json":
                shutil.copy2(f, data_dir / f.name)
            else:
                shutil.copy2(f, config_dir / f.name)
    for f in PLUGIN_SRC.iterdir():
        if f.is_file():
            shutil.copy2(f, plugins_dir / f.name)

    # Create a sample plugin
    (plugins_dir / "sample.ts").write_text(
        "// Fake OpenCode plugin for testing\n"
        "export default {\n"
        "  name: 'sample-plugin',\n"
        "  version: '1.0.0',\n"
        "}\n",
        encoding="utf-8",
    )

    env = {
        **os.environ,
        "OPENCODE_CONFIG_DIR": str(config_dir),
        "OPENCODE_DATA_DIR": str(data_dir),
        "PATH": str(FAKE_DIR) + os.pathsep + os.environ.get("PATH", ""),
    }

    # Make fake_opencode.py executable via a wrapper named 'opencode'
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    wrapper = bin_dir / "opencode"
    wrapper.write_text(
        f'#!/usr/bin/env python3\nimport runpy, sys\nsys.argv[0] = {str(FAKE_DIR / "fake_opencode.py")!r}\nrunpy.run_path({str(FAKE_DIR / "fake_opencode.py")!r}, run_name="__main__")\n',
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    env["PATH"] = str(bin_dir) + os.pathsep + env["PATH"]

    return {
        "root": tmp_path,
        "bin": str(FAKE_DIR / "fake_opencode.py"),
        "wrapper": str(wrapper),
        "config_dir": str(config_dir),
        "data_dir": str(data_dir),
        "plugins_dir": str(plugins_dir),
        "skills_dir": str(skills_dir),
        "env": env,
    }


@pytest.fixture
def fake_mcp_server():
    """Return the path to the fake MCP server script."""
    return str(FAKE_DIR / "mcp_server.py")
