from __future__ import annotations

import json
import time
import threading
from pathlib import Path
from typing import Any, Dict, Optional


class JsonStateStore:
    def __init__(self, path: str | Path, default: Optional[Dict[str, Any]] = None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.default = dict(default or {})
        self._lock = threading.Lock()

        # RAM cache (dla snapshotu)
        self._snapshot_cache: Optional[Dict[str, Any]] = None

        if not self.path.exists():
            self._atomic_write({**self.default, "_ts": time.time()})

        # wczytaj cache na start (opcjonalnie)
        try:
            self._snapshot_cache = self.get("snapshot", None)
        except Exception:
            self._snapshot_cache = None

    # ---------- "normalny" KV store (dysk) ----------

    def get_all(self) -> Dict[str, Any]:
        with self._lock:
            return self._read()

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            data = self._read()
            return data.get(key, default)

    def set(self, key: str, value: Any) -> Dict[str, Any]:
        with self._lock:
            data = self._read()
            data[key] = value
            data["_ts"] = time.time()
            self._atomic_write(data)
            return data

    def patch(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(updates, dict):
            raise ValueError("updates must be a dict")
        with self._lock:
            data = self._read()
            data.update(updates)
            data["_ts"] = time.time()
            self._atomic_write(data)
            return data

    # ---------- snapshot cache (RAM) + flush ----------

    def set_snapshot(self, snapshot: Dict[str, Any]) -> None:
        with self._lock:
            self._snapshot_cache = snapshot

    def get_snapshot(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            return dict(self._snapshot_cache) if self._snapshot_cache else None

    def flush_snapshot(self) -> None:
        with self._lock:
            if self._snapshot_cache is None:
                return
            data = self._read()
            data["snapshot"] = self._snapshot_cache
            data["_ts"] = time.time()
            self._atomic_write(data)

    # ---------- internals ----------

    def _read(self) -> Dict[str, Any]:
        try:
            raw = self.path.read_text(encoding="utf-8")
            if not raw.strip():
                return {**self.default, "_ts": time.time()}
            return json.loads(raw)
        except FileNotFoundError:
            return {**self.default, "_ts": time.time()}
        except json.JSONDecodeError:
            self._backup_corrupted()
            return {**self.default, "_ts": time.time()}

    def _backup_corrupted(self) -> None:
        try:
            bad = self.path.with_suffix(self.path.suffix + ".corrupted")
            if self.path.exists():
                self.path.replace(bad)
        except Exception:
            pass

    def _atomic_write(self, data: Dict[str, Any]) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        tmp.replace(self.path)

    def update_dict(self, key: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(updates, dict):
            raise ValueError("updates must be a dict")
        with self._lock:
            data = self._read()
            current = data.get(key) or {}
            if not isinstance(current, dict):
                raise ValueError(f"{key} must be a dict in state")
            current.update(updates)
            data[key] = current
            data["_ts"] = time.time()
            self._atomic_write(data)
            return data