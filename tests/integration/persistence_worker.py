"""Subprocess worker for persistence concurrency regression tests.

Runs the REAL production ScopeIsolatedStorage in a separate OS process,
mirroring the Teacher bridge model (one fresh Python process per tool call).

Modes (argv):
  load-wait-store <base> <mid> <content> <loaded_marker> <go_marker>
      Reload store, signal loaded, wait for go marker, then store.
  store <base> <mid> <content>
      Reload store then store one entry.
  store-many <base> <prefix> <n>
      Store n entries (prefix-000 ..) sequentially.
  hold-open <base> <seconds>
      Hold the store file open (forces Windows os.replace PermissionError).
  reload-loop <base> <n> <out_json>
      Reload n times, recording observed counts and errors.
  store-hang <base> <mid> <content>
      Store, print ACK, then hang (parent kills after ack).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.routing.v26.identity import AgentIdentity, MemoryScope  # noqa: E402
from core.routing.v26.memory_types import MemoryEntry, MemoryKind  # noqa: E402
from core.routing.v26.persistence import ScopeIsolatedStorage  # noqa: E402


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


def _store_path(base: str) -> Path:
    return Path(base) / "v26_memory.json"


def _wait_for(path: Path, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while not path.exists():
        if time.monotonic() > deadline:
            return False
        time.sleep(0.01)
    return True


def main(argv: list[str]) -> int:
    mode = argv[0]

    if mode == "load-wait-store":
        base, mid, content, loaded_marker, go_marker = argv[1:6]
        storage = ScopeIsolatedStorage(Path(base))
        storage.reload()
        Path(loaded_marker).write_text("1", encoding="utf-8")
        if not _wait_for(Path(go_marker), timeout=60.0):
            print(json.dumps({"error": "go marker timeout"}), flush=True)
            return 2
        storage.store(_entry(mid, content))
        print(
            json.dumps({"stored": True, "count": storage.size()}),
            flush=True,
        )
        return 0

    if mode == "store":
        base, mid, content = argv[1:4]
        storage = ScopeIsolatedStorage(Path(base))
        storage.reload()
        storage.store(_entry(mid, content))
        print(json.dumps({"stored": True}), flush=True)
        return 0

    if mode == "store-many":
        base, prefix, n_str = argv[1:4]
        n = int(n_str)
        storage = ScopeIsolatedStorage(Path(base))
        for i in range(n):
            storage.store(_entry(f"{prefix}-{i:03d}", f"stress fact {prefix}-{i}"))
        print(json.dumps({"stored": n, "count": storage.size()}), flush=True)
        return 0

    if mode == "hold-open":
        base, seconds_str = argv[1:3]
        seconds = float(seconds_str)
        handle = open(_store_path(base), "rb")  # noqa: SIM115 - must outlive this call
        try:
            print("HOLDING", flush=True)
            time.sleep(seconds)
        finally:
            handle.close()
        print("RELEASED", flush=True)
        return 0

    if mode == "reload-loop":
        base, n_str, out_path = argv[1:4]
        n = int(n_str)
        storage = ScopeIsolatedStorage(Path(base))
        counts: list[int] = []
        errors: list[str] = []
        for _ in range(n):
            try:
                counts.append(storage.reload())
            except Exception as exc:  # noqa: BLE001 - recording every failure
                errors.append(f"{type(exc).__name__}: {exc}")
            time.sleep(0.03)
        Path(out_path).write_text(
            json.dumps({"counts": counts, "errors": errors}), encoding="utf-8"
        )
        print(json.dumps({"done": True, "reads": len(counts)}), flush=True)
        return 0

    if mode == "store-hang":
        base, mid, content = argv[1:4]
        storage = ScopeIsolatedStorage(Path(base))
        storage.store(_entry(mid, content))
        print("ACK", flush=True)
        time.sleep(600)
        return 0

    print(json.dumps({"error": f"unknown mode {mode}"}), flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
