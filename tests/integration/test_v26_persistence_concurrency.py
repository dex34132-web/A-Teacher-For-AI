"""Multi-process persistence concurrency regression tests (H1 + H2).

Root causes under test (forensic investigation, run_20260929_180514):

H1 — stale-cache lost update: each bridge call runs in a fresh Python
     process that loaded the store once; store() rewrote the whole file
     from that possibly-stale cache, silently destroying committed writes
     (FACT-000531, FACT-001366, FACT-001752).

H2 — catastrophic wipe: on Windows, a concurrently open file handle makes
     os.replace() raise PermissionError; the old code fell back to a
     truncate-in-place write_text(), a concurrent reader saw empty/partial
     JSON, _load_raw() silently returned an empty state, and store()
     rewrote the whole file from that empty base (1,373 -> 1 -> 383).

These tests use REAL separate OS processes (the actual bridge model) and
REAL Windows file-handle contention (hold-open mode) — not mocked
persistence. All stores live under pytest tmp_path.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from core.routing.v26.identity import AgentIdentity, MemoryScope
from core.routing.v26.memory_types import MemoryEntry, MemoryKind
from core.routing.v26.persistence import ScopeIsolatedStorage

WORKER = Path(__file__).resolve().parent / "persistence_worker.py"

# Stress parameters (per forensic regression-test design — do not weaken).
STRESS_REPS = 5
STRESS_SEED = 200
STRESS_PROCS = 10
STRESS_WRITES_PER_PROC = 5


def _entry(memory_id: str, content: str) -> MemoryEntry:
    scope = MemoryScope(
        agent=AgentIdentity(agent_id="stress"), project=None, session=None
    )
    base = MemoryEntry.create(content=content, kind=MemoryKind.EPISODIC, scope=scope)
    return MemoryEntry(
        memory_id=memory_id,
        content=content,
        kind=base.kind,
        scope=base.scope,
        timestamp=base.timestamp,
    )


def _seed(base: Path, n: int, prefix: str = "S") -> None:
    """Seed n entries through the production serializer (single write)."""
    storage = ScopeIsolatedStorage(base)
    entries = {
        f"{prefix}{i:04d}": _entry(f"{prefix}{i:04d}", f"seed fact {i}")
        for i in range(n)
    }
    storage._persist(entries)


def _spawn(mode: str, *args: str) -> subprocess.Popen[str]:
    return subprocess.Popen(
        [sys.executable, str(WORKER), mode, *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _finish(proc: subprocess.Popen[str], tag: str, timeout: float = 60.0) -> str:
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        pytest.fail(f"{tag}: timed out after {timeout}s")
    assert proc.returncode == 0, f"{tag}: rc={proc.returncode} err={err} out={out}"
    return out


def _wait_marker(path: Path, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while not path.exists():
        if time.monotonic() > deadline:
            pytest.fail(f"marker never appeared: {path}")
        time.sleep(0.01)


def _fresh_storage(base: Path) -> ScopeIsolatedStorage:
    storage = ScopeIsolatedStorage(base)
    storage.reload()
    return storage


def _assert_no_tmp_files(base: Path) -> None:
    leftovers = list(base.glob("*.tmp"))
    assert leftovers == [], f"temp files left behind: {leftovers}"


# ---------------------------------------------------------------------------
# Test 1: two-process stale writer must not destroy a committed write (H1)
# ---------------------------------------------------------------------------


class TestTwoProcessLostUpdate:
    def test_stale_second_writer_keeps_first_writers_commit(
        self, tmp_path: Path
    ) -> None:
        """Both processes preload state X; both must commit.

        Expected: 1,375 entries. Pre-fix: 1,374 (first writer's commit
        silently destroyed by the stale second writer).
        """
        base = tmp_path / "store"
        base.mkdir()
        _seed(base, 1373)

        go_a = base / "goA"
        go_b = base / "goB"
        loaded_a = base / "loadedA"
        loaded_b = base / "loadedB"

        a = _spawn(
            "load-wait-store",
            str(base), "W1", "writer one fact", str(loaded_a), str(go_a),
        )
        b = _spawn(
            "load-wait-store",
            str(base), "W2", "writer two fact", str(loaded_b), str(go_b),
        )

        # Both processes have loaded the SAME state (1,373) before either writes.
        _wait_marker(loaded_a)
        _wait_marker(loaded_b)

        go_a.touch()
        _finish(a, "writer A")
        go_b.touch()
        _finish(b, "writer B")

        fresh = _fresh_storage(base)
        count = len(fresh.list_keys())
        assert count == 1375, (
            f"expected 1373 seed + 2 commits = 1375, got {count} "
            "(stale writer destroyed a committed write)"
        )
        assert fresh.get("W1") is not None, "writer A's commit was lost"
        assert fresh.get("W2") is not None, "writer B's commit was lost"
        _assert_no_tmp_files(base)


# ---------------------------------------------------------------------------
# Test 2: catastrophic wipe under REAL Windows handle contention (H2)
# ---------------------------------------------------------------------------


class TestConcurrentWipeRegression:
    def test_open_handle_concurrent_writers_never_wipe_store(
        self, tmp_path: Path
    ) -> None:
        """Seed 1,373; holder keeps file open; 5 preloaded writers commit.

        Reproduces the exact forensic mechanism: os.replace ->
        PermissionError while another handle is open. Expected: final
        count == 1,378, readers never observe a smaller store, no corrupt
        or empty reads, no silent success.
        """
        base = tmp_path / "store"
        base.mkdir()
        _seed(base, 1373)

        holder = _spawn("hold-open", str(base), "4")
        line = holder.stdout.readline() if holder.stdout else ""
        assert line.strip() == "HOLDING", f"holder failed to open store: {line}"

        n_writers = 5
        writers: list[subprocess.Popen[str]] = []
        gos: list[Path] = []
        for i in range(n_writers):
            loaded = base / f"loadedW{i}"
            go = base / f"goW{i}"
            writers.append(
                _spawn(
                    "load-wait-store",
                    str(base), f"CW{i}", f"concurrent fact {i}", str(loaded), str(go),
                )
            )
            gos.append(go)
        for i in range(n_writers):
            _wait_marker(base / f"loadedW{i}")

        reader_out = base / "reader.json"
        reader = _spawn("reload-loop", str(base), "80", str(reader_out))

        # Release all writers at once while the holder keeps the file open.
        for go in gos:
            go.touch()
        for i, proc in enumerate(writers):
            _finish(proc, f"writer CW{i}", timeout=90.0)

        _finish(reader, "reader", timeout=90.0)
        _finish(holder, "holder", timeout=30.0)

        reader_data = json.loads(reader_out.read_text(encoding="utf-8"))
        assert reader_data["errors"] == [], (
            f"reader observed failures: {reader_data['errors']}"
        )
        assert reader_data["counts"], "reader performed no reads"
        assert min(reader_data["counts"]) >= 1373, (
            f"reader observed a shrunk store: {reader_data['counts']}"
        )

        fresh = _fresh_storage(base)
        count = len(fresh.list_keys())
        assert count == 1378, (
            f"expected 1373 seed + 5 commits = 1378, got {count} "
            "(catastrophic wipe or lost updates under Windows handle contention)"
        )
        for i in range(n_writers):
            assert fresh.get(f"CW{i}") is not None, f"commit CW{i} missing"
        _assert_no_tmp_files(base)

        # File must be a complete, parseable document.
        data = json.loads((base / "v26_memory.json").read_text(encoding="utf-8"))
        assert isinstance(data["entries"], list)
        assert len(data["entries"]) == 1378


# ---------------------------------------------------------------------------
# Test 6: kill-after-ack durability
# ---------------------------------------------------------------------------


class TestKillAfterAckDurability:
    def test_entry_survives_immediate_process_kill(self, tmp_path: Path) -> None:
        base = tmp_path / "store"
        base.mkdir()

        proc = _spawn("store-hang", str(base), "K1", "kill durable fact")
        assert proc.stdout is not None
        line = proc.stdout.readline()
        assert line.strip() == "ACK", f"no ack from worker: {line!r}"

        proc.kill()
        proc.wait(timeout=30)

        fresh = _fresh_storage(base)
        assert fresh.get("K1") is not None, "acked write lost after process death"
        assert len(fresh.list_keys()) == 1
        _assert_no_tmp_files(base)


# ---------------------------------------------------------------------------
# Test 7: 10-process concurrency stress, repeated
# ---------------------------------------------------------------------------


class TestTenProcessStress:
    @pytest.mark.parametrize("rep", range(STRESS_REPS))
    def test_ten_processes_multiple_writes_repeated(
        self, tmp_path: Path, rep: int
    ) -> None:
        """final_count == initial + successful_writes, every repetition."""
        base = tmp_path / f"rep{rep}"
        base.mkdir()
        _seed(base, STRESS_SEED)

        reader_out = base / "reader.json"
        reader = _spawn("reload-loop", str(base), "150", str(reader_out))

        writers = [
            _spawn(
                "store-many",
                str(base), f"R{rep}W{w}", str(STRESS_WRITES_PER_PROC),
            )
            for w in range(STRESS_PROCS)
        ]
        for w, proc in enumerate(writers):
            _finish(proc, f"rep{rep} writer {w}", timeout=180.0)
        _finish(reader, f"rep{rep} reader", timeout=180.0)

        reader_data = json.loads(reader_out.read_text(encoding="utf-8"))
        assert reader_data["errors"] == [], (
            f"rep{rep}: reader errors: {reader_data['errors']}"
        )
        assert min(reader_data["counts"]) >= STRESS_SEED, (
            f"rep{rep}: reader observed shrunk store: {reader_data['counts']}"
        )

        fresh = _fresh_storage(base)
        expected = STRESS_SEED + STRESS_PROCS * STRESS_WRITES_PER_PROC
        count = len(fresh.list_keys())
        assert count == expected, (
            f"rep{rep}: expected {expected}, got {count} "
            f"({expected - count} committed writes missing)"
        )
        for w in range(STRESS_PROCS):
            for i in range(STRESS_WRITES_PER_PROC):
                mid = f"R{rep}W{w}-{i:03d}"
                assert fresh.get(mid) is not None, f"rep{rep}: missing {mid}"
        _assert_no_tmp_files(base)
