"""Sgraal RAG Filter — score and filter retrieved chunks before LLM consumption."""
from __future__ import annotations
import hashlib
import time
from typing import Optional

_cache: dict[str, tuple[float, float]] = {}  # content_hash → (omega, timestamp)
CACHE_TTL = 300  # 5 minutes


class SgraalRAGFilter:
    """Filter RAG chunks by Sgraal omega score.

    Usage:
        f = SgraalRAGFilter(api_key="sg_live_...", max_omega=60)
        safe_chunks = f.filter(retrieved_chunks)
    """

    def __init__(self, api_key: str, api_url: str = "https://api.sgraal.com",
                 max_omega: float = 60, on_unavailable: str = "passthrough"):
        self.api_key = api_key
        self.api_url = api_url.rstrip("/")
        self.max_omega = max_omega
        self.on_unavailable = on_unavailable  # "passthrough" or "block"

    def _score_chunk(self, content: str) -> float:
        """Get omega score for a chunk, with caching."""
        if len(content) < 10:
            return 0.0  # Short chunks pass through

        h = hashlib.sha256(content.encode()).hexdigest()[:16]
        cached = _cache.get(h)
        if cached and time.time() - cached[1] < CACHE_TTL:
            return cached[0]

        try:
            import requests
            r = requests.post(f"{self.api_url}/v1/preflight",
                json={"memory_state": [{"id": h, "content": content, "type": "semantic",
                    "timestamp_age_days": 0, "source_trust": 0.8, "source_conflict": 0.1, "downstream_count": 1}]},
                headers={"Authorization": f"Bearer {self.api_key}"}, timeout=5)
            omega = r.json().get("omega_mem_final", 0)
            _cache[h] = (omega, time.time())
            return omega
        except Exception:
            return 0.0 if self.on_unavailable == "passthrough" else 100.0

    def filter(self, chunks: list, query: Optional[str] = None) -> list:
        """Filter chunks by omega score. Returns chunks with omega <= max_omega."""
        result = []
        for chunk in chunks:
            content = chunk.get("content", chunk.get("text", str(chunk)))
            if len(content) < 10:
                chunk["sgraal_omega"] = 0
                result.append(chunk)
                continue
            omega = self._score_chunk(content)
            chunk["sgraal_omega"] = omega
            if omega <= self.max_omega:
                result.append(chunk)
        return result

    async def afilter(self, chunks: list, query: Optional[str] = None) -> list:
        """Async version — currently wraps sync (true async in next release)."""
        return self.filter(chunks, query)
