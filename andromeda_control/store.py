"""Small atomic JSON state store for the v0.2 reference controller."""

from __future__ import annotations

import json
import os
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


class StateStore:
    def __init__(self, state_dir: str | Path):
        self.state_dir = Path(state_dir)
        self.state_file = self.state_dir / "state.json"
        self._lock = threading.RLock()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        if not self.state_file.exists():
            self._write({"workers": {}, "tasks": {}})

    def _read(self) -> dict[str, Any]:
        with self.state_file.open(encoding="utf-8") as handle:
            return json.load(handle)

    def _write(self, data: dict[str, Any]) -> None:
        temporary = self.state_file.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(self.state_file)

    @contextmanager
    def transaction(self) -> Iterator[dict[str, Any]]:
        with self._lock:
            state = self._read()
            yield state
            self._write(state)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return self._read()
