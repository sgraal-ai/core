"""Copy-on-read Redis snapshot for request-scoped consistency.

Prevents race conditions when parallel requests modify Redis state
during scoring. All reads within a request see the same frozen state.
"""
from __future__ import annotations
import logging
from typing import Optional

from api.redis_state import redis_get, redis_available

logger = logging.getLogger(__name__)


class RedisSnapshot:
    """Frozen point-in-time snapshot of Redis keys.

    Usage:
        snap = RedisSnapshot(["te_history:abc:fintech", "last_preflight:abc:agent-1"])
        val = snap.get("te_history:abc:fintech")
    """

    def __init__(self, keys: list[str]):
        self._data: dict = {}
        if not redis_available():
            return
        for key in keys:
            try:
                val = redis_get(key)
                if val is not None:
                    self._data[key] = val
            except Exception as e:
                logger.debug("RedisSnapshot: failed to read %s: %s", key, e)

    def get(self, key: str, default=None):
        """Get a value from the snapshot. Returns default if key not present."""
        return self._data.get(key, default)

    def exists(self, key: str) -> bool:
        """Check if key was present at snapshot time."""
        return key in self._data

    @property
    def keys_loaded(self) -> int:
        """Number of keys successfully loaded."""
        return len(self._data)
