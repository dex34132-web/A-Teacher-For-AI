"""Regression tests: teacher_learn must create durable, project-scoped memory.

Root cause under test (before fix):
- factory_tools.create_tools() built MemoryManager(storage=None), so
  store_experience skipped persistence; the bridge process died after the
  request and the learned fact was lost.
- RememberTool dropped agent/project/session scope, so even a persisted
  learn entry would be invisible to plugin recall (strict V2.6 scope filter).

Each bridge invocation runs in a REAL separate process
(write -> process death -> fresh process -> read), which is exactly the
failure mode observed with teacher_learn before the fix.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _bridge(req: dict) -> dict:
    """Run one bridge command in a fresh OS process (spawn-per-request)."""
    proc = subprocess.run(
        [sys.executable, "-m", "teacher.bridge"],
        input=json.dumps(req),
        capture_output=True,
        text=True,
        timeout=60,
        cwd=REPO_ROOT,
    )
    assert proc.returncode == 0, f"bridge failed: {proc.stderr}"
    return json.loads(proc.stdout)


def _learn(worktree: Path, content: str, project: str, session: str) -> dict:
    resp = _bridge({
        "command": "learn",
        "worktree": str(worktree),
        "agent": "opencode",
        "project": project,
        "session": session,
        "content": content,
        "outcome": "SUCCESS",
        "tags": ["persistence-test"],
    })
    assert resp.get("ok") is True, f"learn failed: {resp}"
    assert resp["result"]["stored"] is True, f"learn not stored: {resp}"
    return resp["result"]


def _recall(worktree: Path, query: str, project: str, session: str) -> list[dict]:
    resp = _bridge({
        "command": "recall",
        "worktree": str(worktree),
        "agent": "opencode",
        "project": project,
        "session": session,
        "query": query,
    })
    assert resp.get("ok") is True, f"recall failed: {resp}"
    return resp["memories"]


def _memory_file(worktree: Path) -> Path:
    return worktree / ".teacher" / "memory" / "v26_memory.json"


class TestLearnPersistsAcrossProcesses:
    def test_learn_writes_to_durable_store(self, tmp_path):
        result = _learn(
            tmp_path,
            "P15 marker ZEBRA-QUARTZ exists in this project.",
            "teacher-p15",
            "ses_p15_alpha",
        )
        memory_file = _memory_file(tmp_path)
        assert memory_file.exists(), "learn did not create .teacher/memory/v26_memory.json"
        serialized = memory_file.read_text(encoding="utf-8")
        assert result["experience_id"] in serialized, (
            "learn experience_id missing from durable store"
        )
        assert "ZEBRA-QUARTZ" in serialized

    def test_learn_survives_process_death_and_fresh_recall(self, tmp_path):
        _learn(
            tmp_path,
            "P15 marker ZEBRA-QUARTZ exists in this project.",
            "teacher-p15",
            "ses_p15_alpha",
        )
        # Fresh bridge process: no in-memory state from the learn call.
        memories = _recall(tmp_path, "ZEBRA-QUARTZ", "teacher-p15", "ses_p15_alpha")
        assert len(memories) >= 1, "fresh process could not recall learned fact"
        assert "ZEBRA-QUARTZ" in memories[0]["content"]

    def test_learn_survives_second_fresh_process_restart_analog(self, tmp_path):
        """Two independent fresh recalls (bridge spawn + OpenCode restart analog)."""
        _learn(
            tmp_path,
            "P15 marker CRIMSON-LANTERN exists in this project.",
            "teacher-p15b",
            "ses_p15b_alpha",
        )
        for _ in range(2):
            memories = _recall(
                tmp_path, "CRIMSON-LANTERN", "teacher-p15b", "ses_p15b_alpha"
            )
            assert len(memories) >= 1, "recall failed in fresh process"
            assert "CRIMSON-LANTERN" in memories[0]["content"]


class TestLearnProjectIsolation:
    def test_projects_do_not_see_each_others_memories(self, tmp_path):
        worktree_a = tmp_path / "A"
        worktree_b = tmp_path / "B"
        worktree_a.mkdir()
        worktree_b.mkdir()

        _learn(worktree_a, "ALPHA-MARBLE fact.", "teacher-p15-A", "ses_p15_A")
        _learn(worktree_b, "BETA-SLATE fact.", "teacher-p15-B", "ses_p15_B")

        # Own memory found from a fresh process.
        found_a = _recall(worktree_a, "ALPHA-MARBLE", "teacher-p15-A", "ses_p15_A")
        assert len(found_a) >= 1, "project A lost its own learned fact"
        assert any("ALPHA-MARBLE" in m["content"] for m in found_a)

        # Cross-project: B must NOT see A's memory (fresh processes both sides).
        # Semantic recall may return B's own in-scope candidates for any query,
        # but A's content must never appear in B's results.
        leak = _recall(worktree_b, "ALPHA-MARBLE", "teacher-p15-B", "ses_p15_B")
        assert not any("ALPHA-MARBLE" in m["content"] for m in leak), (
            f"project isolation violated: {leak}"
        )

        leak_reverse = _recall(worktree_a, "BETA-SLATE", "teacher-p15-A", "ses_p15_A")
        assert not any("BETA-SLATE" in m["content"] for m in leak_reverse), (
            f"reverse isolation violated: {leak_reverse}"
        )

    def test_other_project_cannot_read_via_same_worktree_store(self, tmp_path):
        """Scope filter blocks a foreign project id even on the same store."""
        _learn(tmp_path, "GAMMA-QUILL fact.", "teacher-p15-C", "ses_p15_C")
        leak = _recall(tmp_path, "GAMMA-QUILL", "teacher-p15-OTHER", "ses_p15_C")
        assert leak == [], f"project scope filter failed: {leak}"
