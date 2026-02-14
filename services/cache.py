from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any


class JsonFileCache:
    def __init__(self, cache_dir: Path, ttl_seconds: int = 86400) -> None:
        self.cache_dir = cache_dir
        self.ttl_seconds = ttl_seconds
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _key_path(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.json"

    def get(self, key: str) -> Any | None:
        path = self._key_path(key)
        if not path.exists():
            return None

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            ts = float(payload["timestamp"])
            if (time.time() - ts) > self.ttl_seconds:
                return None
            return payload["value"]
        except Exception:
            return None

    def set(self, key: str, value: Any) -> None:
        path = self._key_path(key)
        payload = {"timestamp": time.time(), "value": value}
        path.write_text(json.dumps(payload), encoding="utf-8")
