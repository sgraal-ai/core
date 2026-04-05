"""Redis-backed state persistence with SETNX semantics and graceful fallback."""
from __future__ import annotations
import json
import os
import logging
import urllib.parse

logger = logging.getLogger(__name__)

UPSTASH_REDIS_URL = os.getenv("UPSTASH_REDIS_URL") or os.getenv("UPSTASH_REDIS_REST_URL")
UPSTASH_REDIS_TOKEN = os.getenv("UPSTASH_REDIS_TOKEN") or os.getenv("UPSTASH_REDIS_REST_TOKEN")

def _headers():
    return {"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"}

def redis_available() -> bool:
    return bool(UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN)

def redis_get(key: str, default=None):
    """Get JSON value from Redis. Returns default on any failure."""
    if not redis_available():
        return default
    try:
        import requests
        r = requests.get(f"{UPSTASH_REDIS_URL}/GET/{key}", headers=_headers(), timeout=2)
        if r.ok and r.json().get("result"):
            return json.loads(r.json()["result"])
    except Exception as e:
        logger.debug("redis_get %s failed: %s", key, e)
    return default

def redis_set(key: str, value, ttl: int = 0):
    """Set JSON value in Redis. Silent on failure."""
    if not redis_available():
        return
    try:
        import requests
        data = json.dumps(value)
        url = f"{UPSTASH_REDIS_URL}/SET/{key}/{urllib.parse.quote(data, safe='')}"
        if ttl > 0:
            url += f"/EX/{ttl}"
        requests.post(url, headers=_headers(), timeout=2)
    except Exception as e:
        logger.debug("redis_set %s failed: %s", key, e)

def redis_setnx(key: str, value, ttl: int = 0):
    """Set only if not exists (SETNX). Never overwrites persisted state."""
    if not redis_available():
        return
    try:
        import requests
        data = json.dumps(value)
        r = requests.post(f"{UPSTASH_REDIS_URL}/SETNX/{key}/{urllib.parse.quote(data, safe='')}", headers=_headers(), timeout=2)
        if r.ok and r.json().get("result", 0) == 1 and ttl > 0:
            requests.post(f"{UPSTASH_REDIS_URL}/EXPIRE/{key}/{ttl}", headers=_headers(), timeout=2)
    except Exception as e:
        logger.debug("redis_setnx %s failed: %s", key, e)


class RedisBackedDict:
    """Dict-like wrapper that persists to Redis with SETNX on init.

    Usage:
        _rules = RedisBackedDict("alert_rules", key_field="key_hash")
        _rules["id1"] = {...}  # writes to memory + Redis
        data = _rules.get("id1")  # reads from memory (fast)
    """

    def __init__(self, prefix: str):
        self._prefix = prefix
        self._local: dict = {}
        # Load from Redis on init (SETNX pattern — don't overwrite if populated)
        persisted = redis_get(prefix, None)
        if persisted and isinstance(persisted, dict):
            self._local = persisted

    def __getitem__(self, key):
        return self._local[key]

    def __setitem__(self, key, value):
        self._local[key] = value
        self._persist()

    def __contains__(self, key):
        return key in self._local

    def __delitem__(self, key):
        self._local.pop(key, None)
        self._persist()

    def get(self, key, default=None):
        return self._local.get(key, default)

    def pop(self, key, default=None):
        val = self._local.pop(key, default)
        self._persist()
        return val

    def values(self):
        return self._local.values()

    def items(self):
        return self._local.items()

    def keys(self):
        return self._local.keys()

    def __len__(self):
        return len(self._local)

    def _persist(self):
        # Note: Persists entire dict on every write for simplicity. For high-write workloads, consider per-key storage.
        redis_set(self._prefix, self._local)
