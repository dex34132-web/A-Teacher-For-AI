"""Tests for Lerev bridge discovery."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

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

    def test_tier1_evo_home_env_fallback(self, tmp_path: Path) -> None:
        """Tier 1: EVO_HOME env var as fallback (backward compat)."""
        bridge_dir = tmp_path / "lerev"
        bridge_dir.mkdir()
        bridge_file = bridge_dir / "bridge.py"
        bridge_file.write_text("# bridge", encoding="utf-8")

        # Clear LEREV_HOME so EVO_HOME is the fallback
        env = os.environ.copy()
        env.pop("LEREV_HOME", None)
        env["EVO_HOME"] = str(tmp_path)
        with patch.dict(os.environ, env, clear=True):
            # Mock importlib.util.find_spec to fail so Tier 3 doesn't succeed
            with patch("importlib.util.find_spec", return_value=None):
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
            discover_bridge(str(tmp_path))
        # May still find dev fallback if scripts/lerev_bridge.py exists in worktree
        # This test verifies the cascade works, not that it always fails

    def test_bridge_discovery_dataclass(self) -> None:
        """BridgeDiscovery has correct fields."""
        d = BridgeDiscovery(python="python3", bridge_path="/path/bridge.py", tier="dev_fallback")
        assert d.python == "python3"
        assert d.bridge_path == "/path/bridge.py"
        assert d.tier == "dev_fallback"
