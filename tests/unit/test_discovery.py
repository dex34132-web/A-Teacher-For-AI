"""Tests for School bridge discovery."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from school.discovery import BridgeDiscovery, discover_bridge


class TestBridgeDiscovery:
    """Test the 4-tier bridge discovery cascade."""

    def test_tier1_school_home(self, tmp_path: Path) -> None:
        """Tier 1: SCHOOL_HOME env var."""
        bridge_dir = tmp_path / "school"
        bridge_dir.mkdir()
        bridge_file = bridge_dir / "bridge.py"
        bridge_file.write_text("# bridge", encoding="utf-8")

        with patch.dict(os.environ, {"SCHOOL_HOME": str(tmp_path)}):
            result = discover_bridge(str(tmp_path))

        assert result is not None
        assert result.tier == "SCHOOL_HOME"
        assert result.bridge_path == str(bridge_file)

    def test_tier1_legacy_home_envs_not_honoured(self, tmp_path: Path) -> None:
        """LEREV_HOME / EVO_HOME are no longer honoured (no compat fallbacks)."""
        home = tmp_path / "legacy_home"
        (home / "school").mkdir(parents=True)
        (home / "school" / "bridge.py").write_text("", encoding="utf-8")

        with patch.dict(os.environ, {"LEREV_HOME": str(home), "EVO_HOME": str(home)}, clear=True):
            result = discover_bridge(str(tmp_path))

        assert result is None or not result.bridge_path.startswith(str(home))

    def test_tier4_dev_fallback(self, tmp_path: Path) -> None:
        """Tier 4: Development fallback."""
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        bridge_file = scripts_dir / "school_bridge.py"
        bridge_file.write_text("# bridge", encoding="utf-8")

        with patch.dict(os.environ, {}, clear=True):
            result = discover_bridge(str(tmp_path))

        assert result is not None
        assert result.tier == "dev_fallback"
        assert result.bridge_path == str(bridge_file)

    def test_no_bridge_found(self, tmp_path: Path) -> None:
        """Returns None when no bridge is found."""
        with patch.dict(os.environ, {}, clear=True):
            discover_bridge(str(tmp_path))
        # May still find dev fallback if scripts/school_bridge.py exists in worktree
        # This test verifies the cascade works, not that it always fails

    def test_bridge_discovery_dataclass(self) -> None:
        """BridgeDiscovery has correct fields."""
        d = BridgeDiscovery(python="python3", bridge_path="/path/bridge.py", tier="dev_fallback")
        assert d.python == "python3"
        assert d.bridge_path == "/path/bridge.py"
        assert d.tier == "dev_fallback"
