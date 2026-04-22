import asyncio
import hashlib
import time
from typing import Any


class TTLCache:
    def __init__(self, ttl_seconds: int = 300):
        self.ttl = ttl_seconds
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        async with self._lock:
            value = self._store.get(key)
            if not value:
                return None
            expires_at, payload = value
            if time.time() >= expires_at:
                del self._store[key]
                return None
            return payload

    async def set(self, key: str, value: Any) -> None:
        async with self._lock:
            self._store[key] = (time.time() + self.ttl, value)

    @staticmethod
    def make_key(*parts: str) -> str:
        hash_input = "||".join(parts).encode("utf-8")
        return hashlib.sha256(hash_input).hexdigest()
