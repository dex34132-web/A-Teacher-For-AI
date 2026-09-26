"""Teacher bridge — development fallback wrapper.

This is the development fallback bridge. For installed usage,
use `python -m teacher.bridge` instead.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path so core.* imports work
_BRIDGE_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BRIDGE_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from teacher.bridge import main  # noqa: E402

if __name__ == "__main__":
    main()
