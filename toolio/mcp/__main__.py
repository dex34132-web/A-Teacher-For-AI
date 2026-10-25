"""Allow running the Toolio MCP server via ``python -m toolio.mcp``."""

from __future__ import annotations

import sys

try:
    from toolio.mcp.server import main
except ImportError as exc:
    sys.stderr.write(
        "Toolio MCP server requires the optional 'mcp' package.\n"
        "Install it with: pip install 'toolio[mcp]'\n"
        f"(import failed: {exc})\n"
    )
    raise SystemExit(1) from exc

if __name__ == "__main__":
    main()
