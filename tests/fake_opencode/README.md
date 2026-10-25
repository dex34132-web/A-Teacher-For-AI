# Fake OpenCode Environment (testing only)

A self-contained fake OpenCode harness that mimics OpenCode's CLI, config files,
MCP server protocol, and plugin directory for testing Toolio's integration without
a real OpenCode installation.

## Contents

- `fake_opencode.py` — fake `opencode` CLI (version, run, session, mcp, auth, models, config, tools, agent, context, plugin)
- `mcp_server.py` — fake MCP server over stdio (JSON-RPC 2.0): initialize, tools/list, tools/call, resources/list, resources/read, prompts/list, prompts/get, ping
- `conftest.py` — pytest fixtures: `fake_opencode` (isolated env) and `fake_mcp_server` (path to server script)
- `config/opencode.json` — sample OpenCode config (model, providers, mcp, plugin, permissions, compaction)
- `config/auth.json` — sample auth (anthropic, openai, groq, openrouter keys)
- `plugins/sample.ts` — sample plugin
- `test_fake_opencode.py` — 15 smoke tests (all passing)

## Usage

### As pytest fixtures

```python
def test_something(fake_opencode):
    env = fake_opencode["env"]  # env vars for subprocesses
    # fake_opencode["config_dir"], ["data_dir"], ["plugins_dir"], ["skills_dir"]
    ...

def test_mcp(fake_mcp_server):
    # fake_mcp_server is a path string to the server script
    ...
```

### Standalone CLI

```bash
OPENCODE_CONFIG_DIR=/tmp/cfg OPENCODE_DATA_DIR=/tmp/data \
  python tests/fake_opencode/fake_opencode.py --version
python tests/fake_opencode/fake_opencode.py config show
python tests/fake_opencode/fake_opencode.py mcp list
python tests/fake_opencode/fake_opencode.py tools list
```

### Standalone MCP server

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | \
  python tests/fake_opencode/mcp_server.py
```

## Environment variables

- `OPENCODE_CONFIG_DIR` — overrides `~/.config/opencode` (default: `~/.config/opencode`)
- `OPENCODE_DATA_DIR` — overrides `~/.local/share/opencode` (default: `~/.local/share/opencode`)

## Running tests

```bash
python -m pytest tests/fake_opencode/ -q --basetemp=/tmp/pytestb
```
