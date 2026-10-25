import sys
import json


def main():
    NL = chr(10)
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
            sys.stdout.write(json.dumps(resp) + NL)
            sys.stdout.flush()
            continue
        method = req.get("method", "")
        rid = req.get("id")
        params = req.get("params", {}) or {}
        if rid is None:
            continue
        if method == "initialize":
            result = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {"listChanged": True}, "resources": {"subscribe": True, "listChanged": True}, "prompts": {"listChanged": True}, "logging": {}}, "serverInfo": {"name": "fake-opencode", "version": "1.0.0"}}
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": [
                {"name": "bash", "description": "Run a shell command", "inputSchema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
                {"name": "read", "description": "Read a file", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
                {"name": "write", "description": "Write a file", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
                {"name": "grep", "description": "Search file contents", "inputSchema": {"type": "object", "properties": {"pattern": {"type": "string"}, "path": {"type": "string"}}, "required": ["pattern"]}},
                {"name": "glob", "description": "Find files by pattern", "inputSchema": {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]}},
            ]}
        elif method == "tools/call":
            name = params.get("name", "")
            args = params.get("arguments", {}) or {}
            if name == "bash":
                text = "$ " + args.get("command", "") + chr(10) + "(exit 0)"
            elif name == "read":
                text = "contents of " + args.get("path", "")
            elif name == "write":
                text = "wrote " + args.get("path", "")
            elif name == "grep":
                text = "matches for " + args.get("pattern", "") + " in " + args.get("path", ".")
            elif name == "glob":
                text = "files matching " + args.get("pattern", "")
            else:
                text = "unknown tool: " + name
            result = {"content": [{"type": "text", "text": text}], "isError": False}
        elif method == "resources/list":
            result = {"resources": [
                {"uri": "opencode://context", "name": "context", "mimeType": "text/plain"},
                {"uri": "opencode://session", "name": "session", "mimeType": "application/json"},
                {"uri": "opencode://config", "name": "config", "mimeType": "application/json"},
            ]}
        elif method == "resources/read":
            uri = params.get("uri", "")
            result = {"contents": [{"uri": uri, "mimeType": "text/plain", "text": "content of " + uri}]}
        elif method == "prompts/list":
            result = {"prompts": [
                {"name": "explain", "description": "Explain code", "arguments": [{"name": "code", "required": True}]},
                {"name": "refactor", "description": "Refactor code", "arguments": [{"name": "code", "required": True}]},
            ]}
        elif method == "prompts/get":
            name = params.get("name", "")
            result = {"description": "prompt " + name, "messages": [{"role": "user", "content": {"type": "text", "text": "Run " + name}}]}
        elif method == "logging/setLevel":
            result = {}
        else:
            resp = {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": "method not found: " + method}}
            sys.stdout.write(json.dumps(resp) + NL)
            sys.stdout.flush()
            continue
        resp = {"jsonrpc": "2.0", "id": rid, "result": result}
        sys.stdout.write(json.dumps(resp) + NL)
        sys.stdout.flush()


if __name__ == "__main__":
    main()
