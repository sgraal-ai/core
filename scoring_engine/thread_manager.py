from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


@dataclass
class ThreadBucket:
    bucket_id: str
    thread_ids: list[str] = field(default_factory=list)
    shared_gsv: int = 0
    risk_level: str = "medium"  # "high", "medium", "low"


# Sample rates per domain: 1.0 = check every call, 0.1 = check 10%
DOMAIN_SAMPLE_RATES = {
    "medical": 1.0,
    "fintech": 1.0,
    "legal": 1.0,
    "customer_support": 0.1,
    "coding": 0.1,
    "general": 0.5,
}


class ThreadManager:
    """Thread bucketing + adaptive sampling for million-scale deployments.

    Assigns threads to buckets via consistent hashing. High-risk domains
    (medical, fintech, legal) always get full scoring. Low-risk domains
    are sampled at reduced rates.
    """

    def __init__(self, bucket_size: int = 1000) -> None:
        self._bucket_size = bucket_size
        self._buckets: dict[str, ThreadBucket] = {}

    def assign_bucket(self, thread_id: str, domain: str) -> str:
        """Assign a thread to a bucket via consistent hashing."""
        h = int(hashlib.sha256(thread_id.encode()).hexdigest(), 16)
        bucket_idx = h % self._bucket_size
        bucket_id = f"bucket:{bucket_idx}"

        if bucket_id not in self._buckets:
            risk = "high" if domain in ("medical", "fintech", "legal") else "medium" if domain in ("customer_support", "general") else "low"
            self._buckets[bucket_id] = ThreadBucket(bucket_id=bucket_id, risk_level=risk)

        bucket = self._buckets[bucket_id]
        if thread_id not in bucket.thread_ids:
            bucket.thread_ids.append(thread_id)

        return bucket_id

    def get_sample_rate(self, domain: str) -> float:
        """Get the sampling rate for a domain."""
        return DOMAIN_SAMPLE_RATES.get(domain, 0.5)

    def should_check(self, thread_id: str, domain: str) -> bool:
        """Determine if this thread should get full scoring.

        Uses deterministic hashing so the same thread_id + domain
        always produces the same decision (no randomness).
        """
        rate = self.get_sample_rate(domain)
        if rate >= 1.0:
            return True

        # Deterministic sampling: hash thread_id to a float in [0, 1)
        h = int(hashlib.sha256(f"{thread_id}:{domain}".encode()).hexdigest(), 16)
        sample_value = (h % 10000) / 10000.0
        return sample_value < rate
