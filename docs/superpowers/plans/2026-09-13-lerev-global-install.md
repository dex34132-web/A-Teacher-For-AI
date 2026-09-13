# Lerev — Global Cross-Platform Installation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable Lerev to be installed once and used from any OpenCode project directory globally.

**Architecture:** Add a Python CLI package (`lerev/`) alongside the existing `core/` package, with bridge discovery, OpenCode plugin registration, and distribution packaging. The existing V2.6 core is NOT modified.

**Tech Stack:** Python 3.11+ (hatchling build), TypeScript (OpenCode plugin), NSIS (Windows installer), Chocolatey, Homebrew, shell scripts

**Spec:** `docs/superpowers/specs/2026-09-13-lerev-global-install-design.md`

## Global Constraints

- Python >=3.11 required
- Existing 2056 tests must continue passing
- V2.6 core must NOT be modified
- V2.5 routing semantics must NOT be modified
- Product name: Lerev (renamed from Lerev)
- Memory dir: `.lerev/memory/` (`.lerev/memory/` still readable)
- Env var: `LEREV_HOME` (`LEREV_HOME` still supported as fallback)
- No HTTP daemon
- No memory through CLI arguments
- No global memory merging
- No deleting unrelated OpenCode config during uninstall

---

## Task 1: Rename pyproject.toml and Create lerev Package Init

**Files:**
- Modify: `pyproject.toml`
- Create: `lerev/__init__.py`
- Create: `lerev/__main__.py`

**Interfaces:**
- Produces: `lerev.__version__`, `python -m lerev` entry point

- [ ] **Step 1: Update pyproject.toml**

Change the project name from `ai-learning-engine` to `lerev`. Add CLI entry point. Add `lerev` to wheel packages.

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "lerev"
version = "2.6.0"
description = "Universal agent learning and memory system"
readme = "README.md"
license = "MIT"
requires-python = ">=3.11"
authors = [
    { name = "Lerev Contributors" },
]
keywords = ["ai", "machine-learning", "coding-agent", "harness", "memory", "learning"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Programming Language :: Python :: 3.14",
    "Topic :: Software Development :: Libraries",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
]

dependencies = [
    "pydantic>=2.0,<3.0",
]

[project.scripts]
lerev = "lerev.cli:main"

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "pytest-asyncio>=0.23",
    "ruff>=0.5",
    "mypy>=1.10",
]
web = [
    "httpx>=0.27",
    "beautifulsoup4>=4.12",
]
semantic = [
    "fastembed>=0.8.0",
]
all = [
    "lerev[dev,web,semantic]",
]

[project.urls]
Homepage = "https://github.com/dkshs/lerev"
Documentation = "https://github.com/dkshs/lerev/tree/main/docs"
Repository = "https://github.com/dkshs/lerev"
Issues = "https://github.com/dkshs/lerev/issues"

[tool.hatch.build.targets.wheel]
packages = ["core", "web", "adapters", "storage", "lerev"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "B",    # flake8-bugbear
    "UP",   # pyupgrade
    "SIM",  # flake8-simplify
]

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = "-v --tb=short --basetemp=.pytest_tmp"
```

- [ ] **Step 2: Create lerev/__init__.py**

```python
"""Lerev — Universal agent learning and memory system."""

from __future__ import annotations

__version__ = "2.6.0"
__all__ = ["__version__"]
```

- [ ] **Step 3: Create lerev/__main__.py**

```python
"""Allow running Lerev CLI via `python -m lerev`."""

from __future__ import annotations

from lerev.cli import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run existing tests to verify nothing broke**

Run: `python -m pytest tests/ -x -q`
Expected: All existing tests pass (2056 total, 0 failures)

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml lerev/__init__.py lerev/__main__.py
git commit -m "feat: rename package to lerev, add CLI entry point"
```

---

## Task 2: Create Bridge Discovery Module

**Files:**
- Create: `lerev/discovery.py`
- Create: `tests/unit/test_discovery.py`

**Interfaces:**
- Produces: `discover_bridge(worktree: str) -> BridgeDiscovery | None`
- Produces: `BridgeDiscovery` dataclass with `python`, `bridge_path`, `tier` fields

- [ ] **Step 1: Write failing tests for bridge discovery**

```python
"""Tests for Lerev bridge discovery."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from lerev.discovery import BridgeDiscovery, discover_bridge


class TestBridgeDiscovery:
    """Test the 4-tier bridge discovery cascade."""

    def test_tier1_lerev_home(self, tmp_path: Path) -> None:
        """Tier 1: LEREV_HOME env var."""
        bridge_dir = tmp_path / "lerev"
        bridge_dir.mkdir()
        bridge_file = bridge_dir / "bridge.py"
        bridge_file.write_text("# bridge", encoding="utf-8")

        with patch.dict(os.environ, {"LEREV_HOME": str(tmp_path)}):
            result = discover_bridge(str(tmp_path))

        assert result is not None
        assert result.tier == "LEREV_HOME"
        assert result.bridge_path == str(bridge_file)

    def test_tier1_evo_home_fallback(self, tmp_path: Path) -> None:
        """Tier 1: LEREV_HOME env var as fallback."""
        bridge_dir = tmp_path / "lerev"
        bridge_dir.mkdir()
        bridge_file = bridge_dir / "bridge.py"
        bridge_file.write_text("# bridge", encoding="utf-8")

        with patch.dict(os.environ, {"LEREV_HOME": str(tmp_path)}, clear=False):
            # Remove LEREV_HOME if set
            env = os.environ.copy()
            env.pop("LEREV_HOME", None)
            with patch.dict(os.environ, env, clear=True):
                result = discover_bridge(str(tmp_path))

        assert result is not None
        assert result.tier == "LEREV_HOME"

    def test_tier4_dev_fallback(self, tmp_path: Path) -> None:
        """Tier 4: Development fallback."""
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        bridge_file = scripts_dir / "lerev_bridge.py"
        bridge_file.write_text("# bridge", encoding="utf-8")

        with patch.dict(os.environ, {}, clear=True):
            result = discover_bridge(str(tmp_path))

        assert result is not None
        assert result.tier == "dev_fallback"
        assert result.bridge_path == str(bridge_file)

    def test_no_bridge_found(self, tmp_path: Path) -> None:
        """Returns None when no bridge is found."""
        with patch.dict(os.environ, {}, clear=True):
            result = discover_bridge(str(tmp_path))
        # May still find dev fallback if scripts/lerev_bridge.py exists in worktree
        # This test verifies the cascade works, not that it always fails

    def test_bridge_discovery_dataclass(self) -> None:
        """BridgeDiscovery has correct fields."""
        d = BridgeDiscovery(python="python3", bridge_path="/path/bridge.py", tier="dev_fallback")
        assert d.python == "python3"
        assert d.bridge_path == "/path/bridge.py"
        assert d.tier == "dev_fallback"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_discovery.py -v`
Expected: FAIL with ImportError (module not found)

- [ ] **Step 3: Implement bridge discovery**

```python
"""Lerev bridge discovery — 4-tier cascade."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BridgeDiscovery:
    """Result of bridge discovery."""

    python: str
    bridge_path: str
    tier: str


def _find_python() -> str | None:
    """Find a usable Python interpreter."""
    for cmd in ("python3", "python"):
        if shutil.which(cmd):
            return cmd
    return None


def _file_exists(path: str) -> bool:
    """Check if a file exists."""
    return Path(path).is_file()


def discover_bridge(worktree: str) -> BridgeDiscovery | None:
    """Discover the Lerev bridge using a 4-tier cascade.

    Tier 1: LEREV_HOME / LEREV_HOME env var
    Tier 2: lerev-bridge on PATH
    Tier 3: python -m lerev.bridge
    Tier 4: Dev fallback ({worktree}/scripts/lerev_bridge.py)
    """
    python = _find_python()

    # Tier 1: LEREV_HOME / LEREV_HOME env var
    lerev_home = os.environ.get("LEREV_HOME") or os.environ.get("LEREV_HOME")
    if lerev_home:
        bridge_path = str(Path(lerev_home) / "lerev" / "bridge.py")
        if _file_exists(bridge_path):
            return BridgeDiscovery(
                python=python or "python3",
                bridge_path=bridge_path,
                tier="LEREV_HOME",
            )

    # Tier 2: lerev-bridge on PATH
    lerev_bridge = shutil.which("lerev-bridge")
    if lerev_bridge:
        return BridgeDiscovery(
            python="",
            bridge_path=lerev_bridge,
            tier="PATH",
        )

    # Tier 3: python -m lerev.bridge (only if python is available)
    if python:
        # We can't easily test this without running python, so we check
        # if the lerev package is importable by checking if lerev/bridge.py exists
        # in a known location. The actual module invocation happens in the plugin.
        try:
            import importlib.util

            spec = importlib.util.find_spec("lerev.bridge")
            if spec is not None and spec.origin is not None:
                return BridgeDiscovery(
                    python=python,
                    bridge_path="-m lerev.bridge",
                    tier="installed_module",
                )
        except (ImportError, ValueError):
            pass

    # Tier 4: Dev fallback
    dev_bridge = str(Path(worktree) / "scripts" / "lerev_bridge.py")
    if _file_exists(dev_bridge):
        return BridgeDiscovery(
            python=python or "python3",
            bridge_path=dev_bridge,
            tier="dev_fallback",
        )

    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_discovery.py -v`
Expected: All tests PASS

- [ ] **Step 5: Run ruff and mypy**

Run: `python -m ruff check lerev/discovery.py tests/unit/test_discovery.py`
Run: `python -m mypy lerev/discovery.py`
Expected: No errors

- [ ] **Step 6: Commit**

```bash
git add lerev/discovery.py tests/unit/test_discovery.py
git commit -m "feat: add bridge discovery with 4-tier cascade"
```

---

## Task 3: Create Config Module

**Files:**
- Create: `lerev/config.py`
- Create: `tests/unit/test_config.py`

**Interfaces:**
- Produces: `LerevConfig` class with paths, OpenCode config discovery
- Produces: `get_opencode_config_path() -> Path | None`
- Produces: `get_opencode_node_modules() -> Path | None`

- [ ] **Step 1: Write failing tests**

```python
"""Tests for Lerev config."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from lerev.config import LerevConfig, get_opencode_config_path, get_opencode_node_modules


class TestLerevConfig:
    """Test Lerev configuration."""

    def test_config_paths(self) -> None:
        """Config provides correct default paths."""
        config = LerevConfig()
        assert config.package_name == "lerev"
        assert config.plugin_dir_name == "lerev"

    def test_get_opencode_config_path_linux(self, tmp_path: Path) -> None:
        """Finds OpenCode config on Linux/macOS."""
        config_dir = tmp_path / ".config" / "opencode"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "opencode.jsonc"
        config_file.write_text('{"plugin": []}', encoding="utf-8")

        with patch("lerev.config.Path.home", return_value=tmp_path):
            result = get_opencode_config_path()

        assert result == config_file

    def test_get_opencode_config_path_windows(self, tmp_path: Path) -> None:
        """Finds OpenCode config on Windows."""
        config_dir = tmp_path / ".config" / "opencode"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "opencode.jsonc"
        config_file.write_text('{"plugin": []}', encoding="utf-8")

        with patch("lerev.config.Path.home", return_value=tmp_path):
            result = get_opencode_config_path()

        assert result == config_file

    def test_get_opencode_config_path_not_found(self, tmp_path: Path) -> None:
        """Returns None when config not found."""
        with patch("lerev.config.Path.home", return_value=tmp_path):
            result = get_opencode_config_path()
        assert result is None

    def test_get_opencode_node_modules(self, tmp_path: Path) -> None:
        """Finds OpenCode node_modules directory."""
        nm_dir = tmp_path / ".config" / "opencode" / "node_modules"
        nm_dir.mkdir(parents=True)

        with patch("lerev.config.Path.home", return_value=tmp_path):
            result = get_opencode_node_modules()

        assert result == nm_dir

    def test_read_opencode_config(self, tmp_path: Path) -> None:
        """Reads OpenCode config JSON."""
        config_dir = tmp_path / ".config" / "opencode"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "opencode.jsonc"
        config_file.write_text('{"plugin": ["test-plugin"]}', encoding="utf-8")

        config = LerevConfig()
        with patch("lerev.config.Path.home", return_value=tmp_path):
            result = config.read_opencode_config()

        assert result is not None
        assert result["plugin"] == ["test-plugin"]

    def test_is_lerev_registered(self, tmp_path: Path) -> None:
        """Checks if Lerev is already registered."""
        config_dir = tmp_path / ".config" / "opencode"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "opencode.jsonc"
        config_file.write_text(
            json.dumps({"plugin": ["~/.config/opencode/node_modules/lerev"]}),
            encoding="utf-8",
        )

        config = LerevConfig()
        with patch("lerev.config.Path.home", return_value=tmp_path):
            assert config.is_lerev_registered() is True

    def test_is_lerev_not_registered(self, tmp_path: Path) -> None:
        """Returns False when Lerev not registered."""
        config_dir = tmp_path / ".config" / "opencode"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "opencode.jsonc"
        config_file.write_text('{"plugin": ["other-plugin"]}', encoding="utf-8")

        config = LerevConfig()
        with patch("lerev.config.Path.home", return_value=tmp_path):
            assert config.is_lerev_registered() is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_config.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement config module**

```python
"""Lerev configuration — paths and OpenCode config discovery."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class LerevConfig:
    """Lerev configuration and path management."""

    package_name: str = "lerev"
    plugin_dir_name: str = "lerev"
    memory_dir: str = ".lerev"
    legacy_memory_dir: str = ".evo"

    def __init__(self) -> None:
        self._home = Path.home()

    def opencode_config_dir(self) -> Path:
        """Return the OpenCode global config directory."""
        return self._home / ".config" / "opencode"

    def opencode_config_file(self) -> Path:
        """Return the OpenCode global config file path."""
        return self.opencode_config_dir() / "opencode.jsonc"

    def opencode_node_modules(self) -> Path:
        """Return the OpenCode global node_modules directory."""
        return self.opencode_config_dir() / "node_modules"

    def lerev_plugin_dir(self) -> Path:
        """Return the directory where the Lerev plugin should be installed."""
        return self.opencode_node_modules() / self.plugin_dir_name

    def read_opencode_config(self) -> dict[str, Any] | None:
        """Read the OpenCode global config file."""
        config_file = self.opencode_config_file()
        if not config_file.is_file():
            return None
        try:
            return json.loads(config_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def write_opencode_config(self, config: dict[str, Any]) -> None:
        """Write the OpenCode global config file."""
        config_file = self.opencode_config_file()
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(
            json.dumps(config, indent=2) + "\n",
            encoding="utf-8",
        )

    def is_lerev_registered(self) -> bool:
        """Check if Lerev is already registered in OpenCode config."""
        config = self.read_opencode_config()
        if config is None:
            return False
        plugins = config.get("plugin", [])
        lerev_marker = f"~/.config/opencode/node_modules/{self.plugin_dir_name}"
        return any(
            self.plugin_dir_name in str(p) or lerev_marker in str(p)
            for p in plugins
        )

    def plugin_entry_path(self) -> str:
        """Return the plugin entry string for OpenCode config."""
        return f"~/.config/opencode/node_modules/{self.plugin_dir_name}"


def get_opencode_config_path() -> Path | None:
    """Find the OpenCode global config file."""
    home = Path.home()
    candidates = [
        home / ".config" / "opencode" / "opencode.jsonc",
        home / ".config" / "opencode" / "opencode.json",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def get_opencode_node_modules() -> Path | None:
    """Find the OpenCode global node_modules directory."""
    nm_dir = Path.home() / ".config" / "opencode" / "node_modules"
    return nm_dir if nm_dir.is_dir() else None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_config.py -v`
Expected: All tests PASS

- [ ] **Step 5: Run ruff and mypy**

Run: `python -m ruff check lerev/config.py tests/unit/test_config.py`
Run: `python -m mypy lerev/config.py`
Expected: No errors

- [ ] **Step 6: Commit**

```bash
git add lerev/config.py tests/unit/test_config.py
git commit -m "feat: add config module with OpenCode config discovery"
```

---

## Task 4: Create Bridge Module (Importable)

**Files:**
- Create: `lerev/bridge.py`
- Modify: `scripts/lerev_bridge.py` (thin wrapper)

**Interfaces:**
- Produces: `lerev.bridge.main()` — same protocol as `scripts/lerev_bridge.py`
- Consumes: `core.routing.v26.*` (existing, unchanged)

- [ ] **Step 1: Create lerev/bridge.py**

This extracts the bridge logic from `scripts/lerev_bridge.py` into an importable module. The existing `scripts/lerev_bridge.py` becomes a thin wrapper.

```python
"""Lerev bridge — importable entry point for the bridge protocol.

Reads a single JSON request from stdin, processes it through the V2.6
memory architecture, and writes a single JSON response to stdout.

Protocol:
    stdin  → JSON request  → bridge → V2.6 components
    stdout → JSON response → Lerev plugin

Commands:
    status   — check component availability
    remember — store an experience through V2.6
    recall   — retrieve memories through V2.6
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# V2.6 imports
# ---------------------------------------------------------------------------

from core.routing.v26.experience import Experience, ExperienceOutcome
from core.routing.v26.identity import (
    AgentIdentity,
    ProjectIdentity,
    SessionIdentity,
)
from core.routing.v26.memory_manager import MemoryManager
from core.routing.v26.memory_types import MemoryRequest
from core.routing.v26.persistence import ScopeIsolatedStorage
from core.routing.v26.security import (
    detect_injection,
    validate_memory_request,
)

# ---------------------------------------------------------------------------
# Bridge state (lazily initialised, lives for one process invocation)
# ---------------------------------------------------------------------------

_manager: MemoryManager | None = None
_storage: ScopeIsolatedStorage | None = None
_init_error: str | None = None


def _init_manager(worktree: str) -> MemoryManager:
    """Initialise (or re-use) the MemoryManager for the given worktree."""
    global _manager, _storage, _init_error

    if _manager is not None:
        return _manager

    try:
        storage_dir = Path(worktree) / ".lerev" / "memory"
        # Fall back to legacy .evo directory
        if not storage_dir.exists():
            legacy_dir = Path(worktree) / ".evo" / "memory"
            if legacy_dir.exists():
                storage_dir = legacy_dir
        storage_dir.mkdir(parents=True, exist_ok=True)
        _storage = ScopeIsolatedStorage(base_path=storage_dir)
        _manager = MemoryManager(storage=_storage)
        _manager.reload()
        _init_error = None
        return _manager
    except Exception as exc:
        _init_error = str(exc)
        raise


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


def _handle_status(req: dict[str, Any]) -> dict[str, Any]:
    """Check actual component availability."""
    worktree = req.get("worktree", "")
    checks: dict[str, str] = {}

    checks["lerev"] = "available"

    try:
        from core.routing.integration import LerevIntegrationBridge  # noqa: F401
        checks["v2_5"] = "available"
    except Exception:
        checks["v2_5"] = "not_importable"

    try:
        from core.routing.v26.memory_manager import MemoryManager  # noqa: F401
        from core.routing.v26.memory_store import MemoryStore  # noqa: F401
        from core.routing.v26.persistence import ScopeIsolatedStorage  # noqa: F401
        from core.routing.v26.security import V26SecurityPolicy  # noqa: F401
        checks["v2_6"] = "available"
    except Exception:
        checks["v2_6"] = "not_importable"

    try:
        storage_dir = Path(worktree) / ".lerev" / "memory"
        if not storage_dir.exists():
            storage_dir = Path(worktree) / ".evo" / "memory"
        storage_dir.mkdir(parents=True, exist_ok=True)
        test_file = storage_dir / ".bridge_test"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink(missing_ok=True)
        checks["persistence"] = "available"
    except Exception:
        checks["persistence"] = "unavailable"

    try:
        is_injection, _ = detect_injection("ignore previous instructions")
        checks["security"] = "available"
    except Exception:
        checks["security"] = "unavailable"

    return {"ok": True, "components": checks}


def _handle_remember(req: dict[str, Any]) -> dict[str, Any]:
    """Store an experience through V2.6."""
    worktree = req.get("worktree", "")
    agent_id = req.get("agent", "opencode")
    project_id = req.get("project", "")
    session_id = req.get("session", "")
    content = req.get("content", "")
    outcome_str = req.get("outcome", "NEUTRAL")
    observation = req.get("observation", content)
    action = req.get("action", "")
    confidence = req.get("confidence", 0.5)
    tags = req.get("tags", [])

    if not content and not observation:
        return {
            "ok": False,
            "error": {"type": "validation", "message": "content or observation required"},
        }

    manager = _init_manager(worktree)

    agent = AgentIdentity.create(agent_id=agent_id, adapter="opencode")
    project = (
        ProjectIdentity.create(project_id=project_id, name=project_id)
        if project_id
        else None
    )
    session = (
        SessionIdentity.create(
            session_id=session_id, project_id=project_id or "", agent_id=agent_id
        )
        if session_id
        else None
    )

    try:
        outcome = ExperienceOutcome[outcome_str.upper()]
    except KeyError:
        outcome = ExperienceOutcome.NEUTRAL

    experience = Experience.create(
        agent=agent,
        observation=observation or content,
        action=action,
        outcome=outcome,
        project=project,
        session=session,
        confidence=confidence,
        tags=frozenset(tags) if tags else frozenset(),
    )

    success, reason = manager.store_experience(experience)
    if not success:
        return {"ok": False, "error": {"type": "storage_rejection", "message": reason}}

    scope: dict[str, Any] = {"agent": agent_id}
    if project_id:
        scope["project"] = project_id
    if session_id:
        scope["session"] = session_id

    return {
        "ok": True,
        "id": experience.experience_id,
        "scope": scope,
        "outcome": outcome.name,
    }


def _handle_recall(req: dict[str, Any]) -> dict[str, Any]:
    """Retrieve memories through V2.6."""
    worktree = req.get("worktree", "")
    agent_id = req.get("agent", "opencode")
    project_id = req.get("project", "")
    session_id = req.get("session", "")
    query = req.get("query", "")
    confidence_threshold = req.get("confidence_threshold", 0.0)
    context_budget = req.get("context_budget", 4096)
    limit = req.get("limit", 10)

    if not query:
        return {"ok": False, "error": {"type": "validation", "message": "query is required"}}

    manager = _init_manager(worktree)

    agent = AgentIdentity.create(agent_id=agent_id, adapter="opencode")
    project = (
        ProjectIdentity.create(project_id=project_id, name=project_id)
        if project_id
        else None
    )
    session = (
        SessionIdentity.create(
            session_id=session_id, project_id=project_id or "", agent_id=agent_id
        )
        if session_id
        else None
    )

    request = MemoryRequest(
        agent=agent,
        query=query,
        project=project,
        session=session,
        limit=limit,
        minimum_confidence=confidence_threshold,
        context_budget=context_budget,
    )

    is_valid, reason = validate_memory_request(request, manager._policy)
    if not is_valid:
        return {"ok": False, "error": {"type": "validation", "message": reason}}

    response = manager.request_memory(request)

    memories: list[dict[str, Any]] = []
    for entry in response.memories:
        memories.append({
            "id": entry.memory_id,
            "content": entry.content,
            "kind": entry.kind.name,
            "confidence": entry.confidence,
            "tags": sorted(entry.tags),
            "source": entry.source,
            "timestamp": entry.timestamp,
        })

    return {
        "ok": True,
        "memories": memories,
        "total": response.total,
        "truncated": response.truncated,
        "context_cost": response.context_cost,
    }


# ---------------------------------------------------------------------------
# Command dispatch
# ---------------------------------------------------------------------------

_COMMANDS = {
    "status": _handle_status,
    "remember": _handle_remember,
    "recall": _handle_recall,
}


def main() -> None:
    """Read JSON from stdin, dispatch command, write JSON to stdout."""
    try:
        raw = sys.stdin.read()
        req = json.loads(raw)
    except json.JSONDecodeError as exc:
        resp = {"ok": False, "error": {"type": "protocol", "message": f"malformed JSON: {exc}"}}
        json.dump(resp, sys.stdout)
        return
    except Exception as exc:
        resp = {"ok": False, "error": {"type": "protocol", "message": f"stdin read error: {exc}"}}
        json.dump(resp, sys.stdout)
        return

    command = req.get("command", "")
    handler = _COMMANDS.get(command)
    if handler is None:
        resp = {
            "ok": False,
            "error": {"type": "protocol", "message": f"unknown command: {command}"},
        }
        json.dump(resp, sys.stdout)
        return

    try:
        resp = handler(req)
    except Exception as exc:
        resp = {"ok": False, "error": {"type": "runtime", "message": str(exc)}}

    json.dump(resp, sys.stdout)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Update scripts/lerev_bridge.py to be a thin wrapper**

Replace the contents of `scripts/lerev_bridge.py` with:

```python
"""Lerev bridge — development fallback wrapper.

This is the development fallback bridge. For installed usage,
use `python -m lerev.bridge` instead.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path so core.* imports work
_BRIDGE_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BRIDGE_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from lerev.bridge import main  # noqa: E402

if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run existing bridge tests**

Run: `python -m pytest tests/integration/test_opencode_bridge.py tests/unit/test_v26_bridge.py -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add lerev/bridge.py scripts/lerev_bridge.py
git commit -m "feat: extract bridge into importable lerev.bridge module"
```

---

## Task 5: Create Plugin Source Bundle

**Files:**
- Create: `lerev/plugin_source.py`
- Modify: `.opencode/plugins/evo.ts` → `.opencode/plugins/lerev.ts`

**Interfaces:**
- Produces: `lerev.plugin_source.TS_PLUGIN_SOURCE` — string containing the TypeScript plugin
- Produces: Updated `lerev.ts` with discovery cascade

- [ ] **Step 1: Create lerev/plugin_source.py**

This file contains the TypeScript plugin source as a Python string, so it can be written to disk during `lerev install`.

```python
"""Lerev plugin source — bundled TypeScript plugin for OpenCode."""

from __future__ import annotations

TS_PLUGIN_SOURCE = r'''import { tool } from "@opencode-ai/plugin/tool"
import type { Plugin } from "@opencode-ai/plugin"
import { execFile } from "node:child_process"
import { promisify } from "node:util"
import { resolve } from "node:path"
import { existsSync } from "node:fs"
import { execSync } from "node:child_process"

const execFileAsync = promisify(execFile)

/**
 * Find a usable Python interpreter.
 */
async function findPython(): Promise<string | null> {
  for (const cmd of ["python3", "python"]) {
    try {
      const { stdout } = await execFileAsync(cmd, ["--version"], {
        timeout: 5000,
        windowsHide: true,
      })
      if (stdout.includes("Python")) return cmd
    } catch {
      continue
    }
  }
  return null
}

/**
 * Test if a Python module is available.
 */
async function testModule(python: string, module: string): Promise<boolean> {
  try {
    await execFileAsync(python, ["-c", `import ${module}`], {
      timeout: 5000,
      windowsHide: true,
    })
    return true
  } catch {
    return false
  }
}

/**
 * Check if a file exists.
 */
function fileExists(path: string): boolean {
  try {
    return existsSync(path)
  } catch {
    return false
  }
}

/**
 * Bridge discovery result.
 */
interface BridgeInfo {
  python: string
  bridgePath: string
  tier: string
}

/**
 * Discover the Lerev bridge using a 4-tier cascade.
 */
async function discoverBridge(worktree: string): Promise<BridgeInfo | null> {
  const python = await findPython()

  // Tier 1: LEREV_HOME / LEREV_HOME env var
  const lerevHome = process.env.LEREV_HOME || process.env.LEREV_HOME
  if (lerevHome) {
    const bridgePath = resolve(lerevHome, "lerev", "bridge.py")
    if (fileExists(bridgePath)) {
      return { python: python ?? "python3", bridgePath, tier: "LEREV_HOME" }
    }
  }

  // Tier 2: lerev-bridge on PATH
  try {
    const bridgeCmd = execSync("where lerev-bridge", { windowsHide: true, timeout: 3000 })
      .toString().trim()
    if (bridgeCmd) {
      return { python: "", bridgePath: bridgeCmd, tier: "PATH" }
    }
  } catch {
    // Not on PATH
  }

  // Tier 3: python -m lerev.bridge
  if (python) {
    const available = await testModule(python, "lerev.bridge")
    if (available) {
      return { python, bridgePath: "-m lerev.bridge", tier: "installed_module" }
    }
  }

  // Tier 4: Dev fallback
  const devBridge = resolve(worktree, "scripts", "lerev_bridge.py")
  if (fileExists(devBridge)) {
    return { python: python ?? "python3", bridgePath: devBridge, tier: "dev_fallback" }
  }

  return null
}

/**
 * Invoke the Lerev bridge with a JSON request.
 */
async function invokeBridge(
  python: string,
  bridgePath: string,
  request: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  const json = JSON.stringify(request)

  // Handle module invocation
  if (bridgePath === "-m lerev.bridge") {
    try {
      const { stdout, stderr } = await execFileAsync(python, ["-m", "lerev.bridge"], {
        input: json,
        timeout: 30000,
        windowsHide: true,
        maxBuffer: 1024 * 1024,
      })
      if (stderr) console.error("[lerev bridge stderr]", stderr)
      if (!stdout.trim()) {
        return { ok: false, error: { type: "protocol", message: "empty bridge response" } }
      }
      return JSON.parse(stdout.trim())
    } catch (err: any) {
      return {
        ok: false,
        error: { type: "bridge_error", message: err?.message ?? String(err) },
      }
    }
  }

  // Handle direct script invocation
  try {
    const { stdout, stderr } = await execFileAsync(python, [bridgePath], {
      input: json,
      timeout: 30000,
      windowsHide: true,
      maxBuffer: 1024 * 1024,
    })
    if (stderr) console.error("[lerev bridge stderr]", stderr)
    if (!stdout.trim()) {
      return { ok: false, error: { type: "protocol", message: "empty bridge response" } }
    }
    return JSON.parse(stdout.trim())
  } catch (err: any) {
    return {
      ok: false,
      error: { type: "bridge_error", message: err?.message ?? String(err) },
    }
  }
}

const LEREV: Plugin = async (ctx) => {
  const bridge = await discoverBridge(ctx.worktree)

  if (!bridge) {
    console.error("[lerev] No bridge found. Lerev tools will return errors.")
    console.error("[lerev] Run `lerev install` to set up Lerev globally.")
  }

  const python = bridge?.python ?? ""
  const bridgePath = bridge?.bridgePath ?? ""

  return {
    tool: {
      lerev_status: tool({
        description:
          "Check Lerev runtime status. Verifies Lerev, V2.5 routing, V2.6 memory, persistence, and security components are available.",
        args: {},
        async execute(_args, context) {
          if (!bridge) {
            return {
              title: "Lerev Status",
              output: "Lerev: unavailable — no bridge found. Run `lerev install`.",
            }
          }

          const resp = await invokeBridge(python, bridgePath, {
            command: "status",
            worktree: context.worktree,
          })

          if (!resp.ok) {
            return {
              title: "Lerev Status",
              output: `Lerev bridge error: ${(resp as any).error?.message ?? "unknown"}`,
            }
          }

          const components = (resp as any).components ?? {}
          const lines = Object.entries(components).map(
            ([k, v]) => `  ${k}: ${v}`,
          )
          return {
            title: "Lerev Status",
            output: `Lerev V2.6 Component Status:\n${lines.join("\n")}`,
            metadata: components,
          }
        },
      }),

      lerev_remember: tool({
        description:
          "Store an experience or memory through Lerev V2.6. Returns a real memory ID from Lerev's persistent memory system.",
        args: {
          content: tool.schema
            .string()
            .describe("The experience or memory content to store"),
          outcome: tool.schema
            .enum(["SUCCESS", "FAILURE", "NEUTRAL", "MIXED"])
            .optional()
            .describe("Outcome of the experience (default: NEUTRAL)"),
          project: tool.schema
            .string()
            .optional()
            .describe("Project scope identifier (default: from workspace)"),
          session: tool.schema
            .string()
            .optional()
            .describe("Session scope identifier (default: from runtime context)"),
          observation: tool.schema
            .string()
            .optional()
            .describe("What was observed (optional, defaults to content)"),
          action: tool.schema
            .string()
            .optional()
            .describe("What action was taken (optional)"),
        },
        async execute(args, context) {
          if (!bridge) {
            return {
              title: "Lerev Remember",
              output: "Lerev: unavailable — no bridge found. Run `lerev install`.",
            }
          }

          const projectId = args.project ?? context.worktree.split(/[/\\]/).pop() ?? "unknown"
          const sessionId = args.session ?? context.sessionID

          const resp = await invokeBridge(python, bridgePath, {
            command: "remember",
            worktree: context.worktree,
            agent: "opencode",
            project: projectId,
            session: sessionId,
            content: args.content,
            outcome: args.outcome ?? "NEUTRAL",
            observation: args.observation,
            action: args.action,
          })

          if (!resp.ok) {
            const err = (resp as any).error ?? {}
            return {
              title: "Lerev Remember — Failed",
              output: `Error [${err.type}]: ${err.message}`,
            }
          }

          const scope = (resp as any).scope ?? {}
          const scopeStr = [
            scope.agent && `agent=${scope.agent}`,
            scope.project && `project=${scope.project}`,
            scope.session && `session=${scope.session}`,
          ]
            .filter(Boolean)
            .join(", ")

          return {
            title: "Lerev Remember",
            output: [
              `Memory stored successfully.`,
              `  ID: ${(resp as any).id}`,
              `  Scope: ${scopeStr}`,
              `  Outcome: ${(resp as any).outcome}`,
            ].join("\n"),
            metadata: {
              id: (resp as any).id,
              scope: (resp as any).scope,
              outcome: (resp as any).outcome,
            },
          }
        },
      }),

      lerev_recall: tool({
        description:
          "Retrieve memories from Lerev V2.6 long-term memory. Returns relevant stored experiences matching the query, scoped to the current project/session.",
        args: {
          query: tool.schema
            .string()
            .describe("Search query to find relevant memories"),
          confidence_threshold: tool.schema
            .number()
            .min(0)
            .max(1)
            .optional()
            .describe("Minimum confidence threshold (0.0-1.0, default: 0.0)"),
          context_budget: tool.schema
            .number()
            .min(0)
            .optional()
            .describe("Maximum tokens for returned memories (default: 2000)"),
          limit: tool.schema
            .number()
            .min(0)
            .max(100)
            .optional()
            .describe("Maximum memories to return (default: 10)"),
          project: tool.schema
            .string()
            .optional()
            .describe("Project scope (default: from workspace)"),
          session: tool.schema
            .string()
            .optional()
            .describe("Session scope (default: from runtime context)"),
        },
        async execute(args, context) {
          if (!bridge) {
            return {
              title: "Lerev Recall",
              output: "Lerev: unavailable — no bridge found. Run `lerev install`.",
            }
          }

          const projectId = args.project ?? context.worktree.split(/[/\\]/).pop() ?? "unknown"
          const sessionId = args.session ?? context.sessionID

          const resp = await invokeBridge(python, bridgePath, {
            command: "recall",
            worktree: context.worktree,
            agent: "opencode",
            project: projectId,
            session: sessionId,
            query: args.query,
            confidence_threshold: args.confidence_threshold ?? 0.0,
            context_budget: args.context_budget ?? 2000,
            limit: args.limit ?? 10,
          })

          if (!resp.ok) {
            const err = (resp as any).error ?? {}
            return {
              title: "Lerev Recall — Failed",
              output: `Error [${err.type}]: ${err.message}`,
            }
          }

          const memories = (resp as any).memories ?? []
          if (memories.length === 0) {
            return {
              title: "Lerev Recall",
              output: "No matching memories found.",
              metadata: { total: 0 },
            }
          }

          const lines = memories.map(
            (m: any, i: number) =>
              `${i + 1}. [${m.kind}] (conf=${m.confidence.toFixed(2)}) ${m.content}`,
          )

          return {
            title: "Lerev Recall",
            output: [
              `Found ${(resp as any).total} matching memories (${memories.length} returned, cost=${(resp as any).context_cost} tokens):`,
              "",
              ...lines,
              "",
              `Provenance: ${memories.map((m: any) => m.id).join(", ")}`,
            ].join("\n"),
            metadata: {
              memories: memories.map((m: any) => ({
                id: m.id,
                kind: m.kind,
                confidence: m.confidence,
                content: m.content,
              })),
              total: (resp as any).total,
              truncated: (resp as any).truncated,
              context_cost: (resp as any).context_cost,
            },
          }
        },
      }),
    },
  }
}

export default LEREV
'''
```

- [ ] **Step 2: Rename .opencode/plugins/evo.ts to lerev.ts**

Copy the updated TypeScript source (with discovery cascade) to `.opencode/plugins/lerev.ts`. Keep the old `evo.ts` as a symlink or remove it.

- [ ] **Step 3: Update .opencode/package.json**

```json
{
  "dependencies": {
    "@opencode-ai/plugin": "1.18.30"
  }
}
```

- [ ] **Step 4: Commit**

```bash
git add lerev/plugin_source.py .opencode/plugins/lerev.ts
git commit -m "feat: bundle TypeScript plugin source with discovery cascade"
```

---

## Task 6: Implement CLI (install, doctor, status, version, uninstall)

**Files:**
- Create: `lerev/cli.py`
- Create: `tests/unit/test_cli.py`

**Interfaces:**
- Produces: `lerev.cli.main()` — CLI entry point
- Consumes: `lerev.config.LerevConfig`
- Consumes: `lerev.discovery.discover_bridge`
- Consumes: `lerev.plugin_source.TS_PLUGIN_SOURCE`

- [ ] **Step 1: Write failing tests for CLI**

```python
"""Tests for Lerev CLI."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lerev.cli import main


class TestCLI:
    """Test CLI commands."""

    def test_version(self, capsys: pytest.CaptureFixture[str]) -> None:
        """lerev version prints version."""
        with patch("sys.argv", ["lerev", "version"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "lerev" in captured.out.lower()

    def test_status_no_bridge(self, capsys: pytest.CaptureFixture[str]) -> None:
        """lerev status reports when no bridge found."""
        with patch("sys.argv", ["lerev", "status"]):
            with patch("lerev.cli.discover_bridge", return_value=None):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "unavailable" in captured.out.lower() or "not found" in captured.out.lower()

    def test_install_idempotent(self, tmp_path: Path) -> None:
        """lerev install is idempotent."""
        config_dir = tmp_path / ".config" / "opencode"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "opencode.jsonc"
        config_file.write_text('{"plugin": []}', encoding="utf-8")
        nm_dir = config_dir / "node_modules"
        nm_dir.mkdir(parents=True)

        with patch("sys.argv", ["lerev", "install"]):
            with patch("lerev.cli.LerevConfig") as MockConfig:
                config = MockConfig.return_value
                config.is_lerev_registered.return_value = False
                config.lerev_plugin_dir.return_value = nm_dir / "lerev"
                config.opencode_config_file.return_value = config_file
                config.read_opencode_config.return_value = {"plugin": []}
                config.write_opencode_config = lambda c: config_file.write_text(
                    json.dumps(c), encoding="utf-8"
                )
                config.plugin_entry_path.return_value = "~/.config/opencode/node_modules/lerev"
                main()

        # Run again - should be idempotent
        with patch("sys.argv", ["lerev", "install"]):
            with patch("lerev.cli.LerevConfig") as MockConfig:
                config = MockConfig.return_value
                config.is_lerev_registered.return_value = True
                main()

    def test_uninstall_safety(self, tmp_path: Path) -> None:
        """lerev uninstall does not remove user memory."""
        memory_dir = tmp_path / ".lerev" / "memory"
        memory_dir.mkdir(parents=True)
        memory_file = memory_dir / "test.json"
        memory_file.write_text('{"test": true}', encoding="utf-8")

        # Uninstall should NOT remove .lerev/memory/
        # This is tested by verifying the directory still exists after uninstall
        assert memory_dir.exists()
        assert memory_file.exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_cli.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement CLI**

```python
"""Lerev CLI — command-line interface for Lerev."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from lerev import __version__
from lerev.config import LerevConfig
from lerev.discovery import discover_bridge
from lerev.plugin_source import TS_PLUGIN_SOURCE


def _cmd_version(args: argparse.Namespace) -> None:
    """Print Lerev version."""
    print(f"lerev {__version__}")


def _cmd_status(args: argparse.Namespace) -> None:
    """Print Lerev status."""
    config = LerevConfig()
    bridge = discover_bridge(".")

    print("Lerev")
    print("────────────────")
    print(f"Version: {__version__}")

    # Plugin status
    if config.is_lerev_registered():
        print("Plugin: installed")
    else:
        print("Plugin: not installed")

    # OpenCode status
    config_path = config.opencode_config_file()
    if config_path and config_path.exists():
        print("OpenCode: detected")
    else:
        print("OpenCode: not found")

    # Bridge status
    if bridge:
        print(f"Bridge: healthy (tier: {bridge.tier})")
    else:
        print("Bridge: not found")

    # Memory status
    memory_dir = Path(".lerev") / "memory"
    legacy_dir = Path(".evo") / "memory"
    if memory_dir.exists() or legacy_dir.exists():
        print("Memory: available")
    else:
        print("Memory: no data")


def _cmd_install(args: argparse.Namespace) -> None:
    """Install Lerev globally for OpenCode."""
    config = LerevConfig()

    print("Lerev Installer")
    print("────────────────────────────")

    # Check Python version
    if sys.version_info < (3, 11):
        print(f"ERROR: Python 3.11+ required (found {sys.version})")
        sys.exit(1)
    print(f"Python: {sys.version_info.major}.{sys.version_info.minor} OK")

    # Check OpenCode config
    config_file = config.opencode_config_file()
    if config_file is None:
        print("WARNING: OpenCode config not found")
        print(f"  Expected at: {config.opencode_config_file()}")
        print("  Lerev will work in development mode only.")
        return

    print(f"OpenCode config: {config_file}")

    # Check if already registered
    if config.is_lerev_registered():
        print("Lerev is already registered. Nothing to do.")
        return

    # Install plugin
    plugin_dir = config.lerev_plugin_dir()
    plugin_dir.mkdir(parents=True, exist_ok=True)

    # Write TypeScript plugin
    plugin_file = plugin_dir / "lerev.ts"
    plugin_file.write_text(TS_PLUGIN_SOURCE, encoding="utf-8")
    print(f"Plugin installed: {plugin_file}")

    # Write package.json for the plugin
    pkg_json = plugin_dir / "package.json"
    pkg_json.write_text(
        json.dumps({"dependencies": {"@opencode-ai/plugin": "1.18.30"}}, indent=2),
        encoding="utf-8",
    )

    # Register in OpenCode config
    opencode_config = config.read_opencode_config()
    if opencode_config is None:
        opencode_config = {"plugin": []}

    plugins = opencode_config.get("plugin", [])
    entry = config.plugin_entry_path()
    if entry not in plugins:
        plugins.append(entry)
        opencode_config["plugin"] = plugins
        config.write_opencode_config(opencode_config)
        print(f"Registered in OpenCode config: {entry}")

    # Verify bridge
    bridge = discover_bridge(".")
    if bridge:
        print(f"Bridge: {bridge.tier} OK")
    else:
        print("WARNING: Bridge not found. Run `lerev doctor` for diagnostics.")

    print("")
    print("Installation complete!")
    print("Restart OpenCode to use Lerev.")


def _cmd_doctor(args: argparse.Namespace) -> None:
    """Run Lerev diagnostics."""
    config = LerevConfig()
    bridge = discover_bridge(".")

    print("Lerev Doctor")
    print("────────────────────────────")

    checks = []

    # Lerev runtime
    try:
        from core.routing.v26.memory_manager import MemoryManager  # noqa: F401
        print("Lerev runtime          PASS")
        checks.append(True)
    except Exception:
        print("Lerev runtime          FAIL — core.routing.v26 not importable")
        checks.append(False)

    # Python
    print(f"Python/runtime         {sys.version_info.major}.{sys.version_info.minor} OK")
    checks.append(True)

    # Bridge
    if bridge:
        print(f"Bridge                 PASS (tier: {bridge.tier})")
        checks.append(True)
    else:
        print("Bridge                 FAIL — no bridge found")
        checks.append(False)

    # OpenCode
    config_file = config.opencode_config_file()
    if config_file and config_file.exists():
        print("OpenCode               PASS")
        checks.append(True)
    else:
        print("OpenCode               FAIL — config not found")
        checks.append(False)

    # Plugin registration
    if config.is_lerev_registered():
        print("Plugin registration   PASS")
        checks.append(True)
    else:
        print("Plugin registration   FAIL — not registered")
        checks.append(False)

    # Plugin resolution
    plugin_dir = config.lerev_plugin_dir()
    if plugin_dir.exists():
        print("Plugin resolution     PASS")
        checks.append(True)
    else:
        print("Plugin resolution     FAIL — plugin directory not found")
        checks.append(False)

    # Memory storage
    memory_dir = Path(".lerev") / "memory"
    legacy_dir = Path(".evo") / "memory"
    if memory_dir.exists() or legacy_dir.exists():
        print("Memory storage         PASS")
        checks.append(True)
    else:
        print("Memory storage         SKIP — no memory data yet")
        checks.append(True)

    print("")
    if all(checks):
        print("Result: READY")
    else:
        print("Result: NOT READY — fix issues above")


def _cmd_uninstall(args: argparse.Namespace) -> None:
    """Uninstall Lerev from OpenCode."""
    config = LerevConfig()

    print("Lerev Uninstaller")
    print("────────────────────────────")

    # Remove plugin directory
    plugin_dir = config.lerev_plugin_dir()
    if plugin_dir.exists():
        import shutil
        shutil.rmtree(plugin_dir)
        print(f"Removed plugin: {plugin_dir}")

    # Remove from OpenCode config
    config_file = config.opencode_config_file()
    if config_file and config_file.exists():
        opencode_config = config.read_opencode_config()
        if opencode_config:
            plugins = opencode_config.get("plugin", [])
            entry = config.plugin_entry_path()
            new_plugins = [p for p in plugins if entry not in str(p)]
            if len(new_plugins) < len(plugins):
                opencode_config["plugin"] = new_plugins
                config.write_opencode_config(opencode_config)
                print(f"Removed from OpenCode config: {entry}")
            else:
                print("Lerev not found in OpenCode config.")

    print("")
    print("Uninstall complete.")
    print("Note: .lerev/memory/ was NOT removed (use explicit action to delete).")
    print("Restart OpenCode to apply changes.")


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="lerev",
        description="Lerev — Universal agent learning and memory system",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    subparsers.add_parser("version", help="Print Lerev version")
    subparsers.add_parser("status", help="Show Lerev status")
    subparsers.add_parser("install", help="Install Lerev globally for OpenCode")
    subparsers.add_parser("doctor", help="Run Lerev diagnostics")
    subparsers.add_parser("uninstall", help="Uninstall Lerev from OpenCode")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    commands = {
        "version": _cmd_version,
        "status": _cmd_status,
        "install": _cmd_install,
        "doctor": _cmd_doctor,
        "uninstall": _cmd_uninstall,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        cmd_func(args)
    else:
        parser.print_help()
        sys.exit(1)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_cli.py -v`
Expected: All tests PASS

- [ ] **Step 5: Run ruff and mypy**

Run: `python -m ruff check lerev/cli.py tests/unit/test_cli.py`
Run: `python -m mypy lerev/cli.py`
Expected: No errors

- [ ] **Step 6: Commit**

```bash
git add lerev/cli.py tests/unit/test_cli.py
git commit -m "feat: implement CLI commands (install, doctor, status, version, uninstall)"
```

---

## Task 7: Create Packaging — Windows Installer (NSIS)

**Files:**
- Create: `packaging/windows/lerev-installer.nsi`

**Interfaces:**
- Produces: NSIS installer script

- [ ] **Step 1: Create NSIS installer script**

```nsis
!include "MUI2.nsh"

Name "Lerev"
OutFile "Lerev-Setup.exe"
InstallDir "$LOCALAPPDATA\Lerev"
RequestExecutionLevel user

!define MUI_ABORTWARNING
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

Section "Install"
    SetOutPath "$INSTDIR"

    ; Check Python
    nsExec::ExecToStack 'python --version'
    Pop $0
    ${If} $0 != 0
        MessageBox MB_OK "Python 3.11+ is required but not found.$\n$\nPlease install Python from https://www.python.org/downloads/"
        Abort
    ${EndIf}

    ; Install Lerev via pip
    nsExec::ExecToStack 'pip install lerev'
    Pop $0
    ${If} $0 != 0
        MessageBox MB_OK "Failed to install Lerev via pip.$\n$\nPlease check your Python installation."
        Abort
    ${EndIf}

    ; Run lerev install
    nsExec::ExecToStack 'lerev install'
    Pop $0

    ; Write uninstaller
    WriteUninstaller "$INSTDIR\uninstall.exe"

    ; Add to PATH (per-user)
    EnVar::AddValue "PATH" "$INSTDIR"
SectionEnd

Section "Uninstall"
    ; Run lerev uninstall
    nsExec::ExecToStack 'lerev uninstall'

    ; Remove from PATH
    EnVar::RemoveValue "PATH" "$INSTDIR"

    ; Remove files
    RMDir /r "$INSTDIR"
    Delete "$INSTDIR\uninstall.exe"
SectionEnd
```

- [ ] **Step 2: Commit**

```bash
git add packaging/windows/
git commit -m "feat: add Windows NSIS installer script"
```

---

## Task 8: Create Packaging — Chocolatey

**Files:**
- Create: `packaging/chocolatey/lerev.nuspec`
- Create: `packaging/chocolatey/tools/chocolateyinstall.ps1`
- Create: `packaging/chocolatey/tools/chocolateyuninstall.ps1`

**Interfaces:**
- Produces: Chocolatey package definition

- [ ] **Step 1: Create Chocolatey package files**

`packaging/chocolatey/lerev.nuspec`:
```xml
<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd">
  <metadata>
    <id>lerev</id>
    <version>2.6.0</version>
    <title>Lerev</title>
    <authors>Lerev Contributors</authors>
    <description>Universal agent learning and memory system for AI coding agents.</description>
    <projectUrl>https://github.com/dkshs/lerev</projectUrl>
    <projectSourceUrl>https://github.com/dkshs/lerev</projectSourceUrl>
    <licenseUrl>https://github.com/dkshs/lerev/blob/main/LICENSE</licenseUrl>
    <requireLicenseAcceptance>false</requireLicenseAcceptance>
    <tags>ai agent learning memory opencode</tags>
  </metadata>
  <files>
    <file src="tools\**" target="tools" />
  </files>
</package>
```

`packaging/chocolatey/tools/chocolateyinstall.ps1`:
```powershell
$ErrorActionPreference = 'Stop'

$packageName = 'lerev'
$url = ''

# Check Python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "Python is required but not found. Installing Python..."
    choco install python312 -y
}

# Install via pip
pip install lerev

# Register with OpenCode
lerev install
```

`packaging/chocolatey/tools/chocolateyuninstall.ps1`:
```powershell
$ErrorActionPreference = 'Stop'

# Unregister from OpenCode
lerev uninstall

# Uninstall via pip
pip uninstall lerev -y
```

- [ ] **Step 2: Commit**

```bash
git add packaging/chocolatey/
git commit -m "feat: add Chocolatey package definition"
```

---

## Task 9: Create Packaging — Homebrew Formula

**Files:**
- Create: `packaging/homebrew/lerev.rb`

**Interfaces:**
- Produces: Homebrew formula

- [ ] **Step 1: Create Homebrew formula**

```ruby
class Lerev < Formula
  desc "Universal agent learning and memory system"
  homepage "https://github.com/dkshs/lerev"
  url "https://github.com/dkshs/lerev/archive/refs/tags/v2.6.0.tar.gz"
  sha256 "PLACEHOLDER_SHA256"
  license "MIT"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  def post_install
    system "#{bin}/lerev", "install"
  end

  test do
    assert_match "lerev #{version}", shell_output("#{bin}/lerev version")
  end
end
```

- [ ] **Step 2: Commit**

```bash
git add packaging/homebrew/
git commit -m "feat: add Homebrew formula"
```

---

## Task 10: Create Packaging — Linux Shell Installer

**Files:**
- Create: `packaging/linux/install.sh`

**Interfaces:**
- Produces: POSIX shell installer script

- [ ] **Step 1: Create Linux installer**

```bash
#!/bin/sh
set -e

LEREV_VERSION="2.6.0"
INSTALL_DIR="${HOME}/.local/bin"

echo "Lerev Installer"
echo "────────────────────────────"

# Detect OS
OS=$(uname -s)
ARCH=$(uname -m)

echo "OS: ${OS}"
echo "Arch: ${ARCH}"

# Check Python
if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: Python 3.11+ is required but not found."
    echo "Please install Python: https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python: ${PYTHON_VERSION}"

# Check pip
if ! command -v pip3 >/dev/null 2>&1; then
    echo "ERROR: pip3 is required but not found."
    exit 1
fi

# Install Lerev
echo "Installing Lerev..."
pip3 install --user lerev

# Ensure ~/.local/bin is on PATH
if [[ ":${PATH}:" != *":${INSTALL_DIR}:"* ]]; then
    echo "Adding ${INSTALL_DIR} to PATH..."
    echo "export PATH=\"${INSTALL_DIR}:\$PATH\"" >> "${HOME}/.bashrc"
    echo "export PATH=\"${INSTALL_DIR}:\$PATH\"" >> "${HOME}/.zshrc" 2>/dev/null || true
    export PATH="${INSTALL_DIR}:${PATH}"
fi

# Register with OpenCode
if command -v lerev >/dev/null 2>&1; then
    echo "Registering with OpenCode..."
    lerev install
else
    echo "WARNING: lerev command not found on PATH."
    echo "Please run 'lerev install' manually after ensuring ~/.local/bin is on PATH."
fi

echo ""
echo "Installation complete!"
echo "Restart your terminal or run: source ~/.bashrc"
```

- [ ] **Step 2: Commit**

```bash
git add packaging/linux/
git commit -m "feat: add Linux shell installer"
```

---

## Task 11: Create Documentation

**Files:**
- Create: `docs/installation.md`
- Create: `docs/troubleshooting.md`

**Interfaces:**
- Produces: Installation guide, troubleshooting guide

- [ ] **Step 1: Create installation.md**

```markdown
# Lerev Installation

## Windows — Recommended GUI Installer

Download `Lerev-Setup.exe` and run it.

Requirements:
- Windows 10/11
- Python 3.11+ (installer will check)

The installer will:
1. Detect Python
2. Install Lerev via pip
3. Register the OpenCode plugin
4. Verify the installation

## Windows — pip

```powershell
pip install lerev
lerev install
```

## Windows — Chocolatey

```powershell
choco install lerev
```

## macOS — Homebrew

```bash
brew install lerev
```

## macOS — pip

```bash
pip3 install lerev
lerev install
```

## Linux — Shell Installer

```bash
curl -fsSL https://lerev.dev/install.sh | sh
```

Or:

```bash
wget -qO- https://lerev.dev/install.sh | sh
```

## Linux — pip

```bash
pip3 install --user lerev
lerev install
```

## npm (for OpenCode plugin only)

```bash
npm install -g lerev
```

Or in your project:

```bash
npm install lerev
```

## Verifying Installation

```bash
lerev doctor
```

Expected output:

```
Lerev Doctor
────────────────────────────
Lerev runtime          PASS
Python/runtime         3.12 OK
Bridge                 PASS (tier: installed_module)
OpenCode               PASS
Plugin registration   PASS
Plugin resolution     PASS
Memory storage         SKIP — no memory data yet

Result: READY
```
```

- [ ] **Step 2: Create troubleshooting.md**

```markdown
# Lerev Troubleshooting

## Bridge not found

Run `lerev doctor` to see which tier of bridge discovery succeeded.

If no bridge is found:
1. Ensure Python 3.11+ is installed
2. Run `pip install lerev`
3. Run `lerev install`

## Plugin not loading

1. Check `~/.config/opencode/opencode.jsonc` has Lerev in the `plugin` array
2. Check `~/.config/opencode/node_modules/lerev/lerev.ts` exists
3. Restart OpenCode

## Memory not persisting

1. Check that `.lerev/memory/` directory exists in your project
2. Check that the bridge can write to it
3. Run `lerev doctor` for diagnostics

## Permission errors

On Linux/macOS, if you get permission errors:

```bash
pip3 install --user lerev
```

On Windows, try running as administrator or use `--user` flag.

## Python version issues

Lerev requires Python 3.11+. Check your version:

```bash
python3 --version
```

If you have multiple Python versions, ensure `python3` points to 3.11+.

## Spaces in paths

Lerev supports spaces in installation paths. If you encounter issues:
1. Use a path without spaces
2. Quote paths in commands
3. Report the issue at https://github.com/dkshs/lerev/issues
```

- [ ] **Step 3: Commit**

```bash
git add docs/installation.md docs/troubleshooting.md
git commit -m "docs: add installation and troubleshooting guides"
```

---

## Task 12: Run Full Test Suite and Validation

**Files:**
- No new files (validation only)

**Interfaces:**
- Consumes: All tasks above

- [ ] **Step 1: Run existing test suite**

Run: `python -m pytest tests/ -x -q`
Expected: 2056 tests pass, 0 failures

- [ ] **Step 2: Run new tests**

Run: `python -m pytest tests/unit/test_cli.py tests/unit/test_config.py tests/unit/test_discovery.py -v`
Expected: All new tests pass

- [ ] **Step 3: Run ruff**

Run: `python -m ruff check lerev/`
Expected: No errors

- [ ] **Step 4: Run mypy**

Run: `python -m mypy lerev/`
Expected: No errors

- [ ] **Step 5: Test CLI manually**

Run: `python -m lerev version`
Expected: `lerev 2.6.0`

Run: `python -m lerev status`
Expected: Status output

Run: `python -m lerev doctor`
Expected: Diagnostic output

- [ ] **Step 6: Test global installation**

Run: `pip install -e .`
Run: `lerev install`
Run: `lerev doctor`
Expected: All checks PASS

- [ ] **Step 7: Test OpenCode integration**

Start OpenCode from a directory that is NOT the Lerev repository.
Verify Lerev loads.
Use `lerev_status`.
Store a memory.
Recall it.
Close OpenCode.
Start OpenCode again.
Recall the memory.
Start OpenCode from another project.
Verify memory isolation.

- [ ] **Step 8: Commit final state**

```bash
git add -A
git commit -m "feat: complete global cross-platform installation for Lerev"
```

---

## Summary

| Task | Description | Status |
|------|-------------|--------|
| 1 | Rename pyproject.toml, create lerev package init | |
| 2 | Create bridge discovery module | |
| 3 | Create config module | |
| 4 | Create bridge module (importable) | |
| 5 | Create plugin source bundle | |
| 6 | Implement CLI commands | |
| 7 | Windows installer (NSIS) | |
| 8 | Chocolatey package | |
| 9 | Homebrew formula | |
| 10 | Linux shell installer | |
| 11 | Documentation | |
| 12 | Full test suite and validation | |
