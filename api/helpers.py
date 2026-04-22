"""Sgraal Infrastructure Helpers — dict management, SSRF validation, anomaly detection.

Pure or near-pure utility functions extracted from api/main.py.
No FastAPI app registration, no Supabase clients, no scoring logic.

Groups:
    1. Dict management — size-capped eviction, TTL-tracked writes
    2. Tenant key derivation — safe_key_hash
    3. SSRF protection — webhook URL validation with DNS rebinding cache
    4. IP utilities — client IP extraction, whitelisting
    5. Anomaly detection — per-key activity tracking with LRU eviction
    6. Public rate limiting — IP-based rate limit for unauthenticated endpoints
"""

import collections as _collections
import hashlib
import ipaddress
import logging
import os
import socket
import threading
import time as _time
import urllib.parse

import requests as http_requests
from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)

__all__ = [
    # Dict management
    "_evict_if_full",
    "_tracked_write",
    "_DICT_MAX_SIZE",
    "_DICT_EVICT_BATCH",
    # Tenant key derivation
    "_safe_key_hash",
    # SSRF protection
    "_validate_webhook_url",
    "_dns_cache",
    "_DNS_CACHE_TTL",
    # IP utilities
    "_extract_client_ip",
    "_is_whitelisted_ip",
    "_WHITELISTED_IP_PREFIXES",
    # Anomaly detection
    "_track_key_activity",
    "_key_activity",
    "_key_activity_lock",
    "_KEY_ACTIVITY_MAX_KEYS",
    "_KEY_ACTIVITY_WINDOW_S",
    "_KEY_ACTIVITY_IP_THRESHOLD",
    "_KEY_ACTIVITY_RPM_MULTIPLIER",
    # Public rate limiting
    "_check_public_rate_limit",
    "_PUBLIC_RL_LIMIT",
    "_PUBLIC_RL_WINDOW",
]


# ---------------------------------------------------------------------------
# 1. Dict management — size-capped eviction
# ---------------------------------------------------------------------------

_DICT_MAX_SIZE = 10000
_DICT_EVICT_BATCH = 1000


def _evict_if_full(d: dict, name: str = "cache"):
    """Evict oldest entries if dict exceeds max size. Python 3.7+ dicts preserve insertion order."""
    if len(d) > _DICT_MAX_SIZE:
        keys_to_remove = list(d.keys())[:_DICT_EVICT_BATCH]
        for k in keys_to_remove:
            d.pop(k, None)
        logger.info("Cache eviction: removed %d oldest entries from %s (was %d)", _DICT_EVICT_BATCH, name, _DICT_MAX_SIZE + 1)


def _tracked_write(d: dict, key: str, value, dict_name: str, write_times: dict = None):
    """Write to dict with size eviction + TTL timestamp tracking.

    Args:
        d: Target dict to write to.
        key: Key to set.
        value: Value to set.
        dict_name: Name for eviction logging.
        write_times: Shared dict of {dict_name: {key: write_timestamp}}.
                     If None, only size eviction is applied (no TTL tracking).
    """
    _evict_if_full(d, dict_name)
    d[key] = value
    if write_times is not None:
        if dict_name not in write_times:
            write_times[dict_name] = {}
        write_times[dict_name][key] = _time.time()


# ---------------------------------------------------------------------------
# 2. Tenant key derivation
# ---------------------------------------------------------------------------

def _safe_key_hash(key_record: dict) -> str:
    """Return a tenant-scoped key_hash. Never returns 'default' or empty string.

    #15: Caches the result on key_record["_cached_hash"] so subsequent calls
    within the same request don't recompute SHA-256.
    """
    # Fast path: cached from a previous call in the same request
    cached = key_record.get("_cached_hash")
    if cached:
        return cached

    # Demo keys: always return "demo" bucket
    if key_record.get("demo"):
        key_record["_cached_hash"] = "demo"
        return "demo"
    kh = key_record.get("key_hash")
    if kh and kh != "default":
        key_record["_cached_hash"] = kh
        return kh
    # Fallback: derive from customer_id for test keys
    cid = key_record.get("customer_id", "")
    if cid:
        result = f"test_{hashlib.sha256(cid.encode()).hexdigest()[:16]}"
        key_record["_cached_hash"] = result
        return result
    raise HTTPException(status_code=403, detail="API key has no valid key_hash — cannot identify tenant")


# ---------------------------------------------------------------------------
# 3. SSRF protection — webhook URL validation
# ---------------------------------------------------------------------------

# FIX 12: DNS resolution cache to prevent rebinding attacks.
_dns_cache: dict[str, tuple[str, float]] = {}  # hostname → (ip, timestamp)
_DNS_CACHE_TTL = 60.0  # seconds


def _validate_webhook_url(url: str) -> str:
    """Validate a webhook URL for SSRF safety. Returns the URL if valid, raises 422 otherwise.
    DNS resolution check is skipped in test environments (SGRAAL_SKIP_DNS_CHECK=1).
    FIX 12: caches resolved IPs to prevent DNS rebinding between validation and dispatch."""
    if not url:
        raise HTTPException(status_code=422, detail="Webhook URL cannot be empty")
    parsed = urllib.parse.urlparse(url)
    # Scheme check
    if parsed.scheme != "https":
        raise HTTPException(status_code=422, detail="Invalid webhook URL: only https:// is allowed")
    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=422, detail="Invalid webhook URL: no hostname")
    # Block dangerous hostnames
    _blocked_hostnames = {"localhost", "ip6-localhost", "ip6-loopback"}
    _blocked_suffixes = (".local", ".internal", ".localhost", ".svc", ".cluster.local")
    if hostname.lower() in _blocked_hostnames or any(hostname.lower().endswith(s) for s in _blocked_suffixes):
        raise HTTPException(status_code=422, detail="Invalid webhook URL: blocked hostname")
    # Check if hostname is a raw IP address (no DNS needed)
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise HTTPException(status_code=422, detail="Invalid webhook URL: resolves to blocked IP range")
        return url
    except ValueError:
        pass  # Not an IP — proceed to DNS resolution
    # Skip DNS resolution in test environments (avoids flaky tests due to DNS)
    if os.getenv("SGRAAL_SKIP_DNS_CHECK") == "1":
        return url
    # Resolve and check IP
    try:
        addrs = socket.getaddrinfo(hostname, parsed.port or 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise HTTPException(status_code=422, detail="Invalid webhook URL: hostname cannot be resolved")
    for family, _, _, _, sockaddr in addrs:
        ip = ipaddress.ip_address(sockaddr[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise HTTPException(status_code=422, detail="Invalid webhook URL: resolves to blocked IP range")
    # FIX 12: cache the validated IP to prevent DNS rebinding at dispatch time
    if addrs:
        _dns_cache[hostname] = (addrs[0][4][0], _time.time())
    return url


# ---------------------------------------------------------------------------
# 4. IP utilities
# ---------------------------------------------------------------------------

# IPs to exclude from anomaly detection: load balancers, internal infra.
_WHITELISTED_IP_PREFIXES = ("100.64.", "100.65.", "100.66.", "100.67.", "100.68.", "100.69.",
                             "100.7", "100.8", "100.9", "100.10", "100.11", "100.12",
                             "127.", "10.", "172.16.", "172.17.", "172.18.", "172.19.",
                             "172.20.", "172.21.", "172.22.", "172.23.", "172.24.", "172.25.",
                             "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.",
                             "192.168.", "::1")


def _is_whitelisted_ip(ip: str) -> bool:
    """Return True if the IP is a known infrastructure address (load balancer,
    internal network, loopback) that should not count toward anomaly detection."""
    if ip in ("testclient", "internal", "unknown"):
        return True
    return any(ip.startswith(p) for p in _WHITELISTED_IP_PREFIXES)


def _extract_client_ip(request: Request) -> str:
    """Extract client IP from request, respecting X-Forwarded-For.

    Uses the RIGHTMOST non-private IP from X-Forwarded-For to prevent
    client-controlled spoofing (the leftmost entry is attacker-controlled,
    while the rightmost non-private entry is set by the last trusted proxy).
    """
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        # Walk from right to left; return the first non-private IP
        for ip in reversed(parts):
            if not _is_whitelisted_ip(ip):
                return ip
        # All IPs are private/internal — return the rightmost one
        return parts[-1] if parts else "unknown"
    xri = request.headers.get("x-real-ip", "")
    if xri:
        return xri
    return request.client.host if request.client else "unknown"


# ---------------------------------------------------------------------------
# 5. Anomaly detection — per-key activity tracking
# ---------------------------------------------------------------------------

# key_hash → deque of (timestamp, ip_address) tuples; auto-pruned to last 1 hour
# FIX 5: use OrderedDict for true LRU eviction (move_to_end on access)
_key_activity: _collections.OrderedDict = _collections.OrderedDict()
_key_activity_lock = threading.Lock()
_KEY_ACTIVITY_MAX_KEYS = 10000

_KEY_ACTIVITY_WINDOW_S = 3600  # 1 hour
_KEY_ACTIVITY_IP_THRESHOLD = 3  # 3+ unique IPs → suspicious
_KEY_ACTIVITY_RPM_MULTIPLIER = 10  # 10× historical average → suspicious


def _track_key_activity(key_hash: str, client_ip: str) -> dict:
    """Record a call for this key and return anomaly signals.

    Whitelisted IPs (Railway LB, private RFC1918, loopback) are recorded
    but excluded from the unique-IP count for anomaly detection.

    Returns {"suspicious": bool, "reason": str|None, "unique_ips": int, "calls_last_hour": int}
    """
    now = _time.time()
    cutoff = now - _KEY_ACTIVITY_WINDOW_S

    with _key_activity_lock:
        dq = _key_activity.get(key_hash)
        if dq is None:
            # FIX 5: LRU eviction — evict least-recently-accessed key when cap reached
            if len(_key_activity) >= _KEY_ACTIVITY_MAX_KEYS:
                _key_activity.popitem(last=False)  # pop oldest (LRU)
            dq = _collections.deque()
            _key_activity[key_hash] = dq
        else:
            # FIX 5: move to end on access (marks as most-recently-used)
            _key_activity.move_to_end(key_hash)

        # Prune old entries
        while dq and dq[0][0] < cutoff:
            dq.popleft()

        dq.append((now, client_ip))

        calls_last_hour = len(dq)
        # unique_ips: total distinct IPs seen (for reporting)
        all_ips = set(ip for _, ip in dq)
        unique_ips = len(all_ips)
        # suspicious_ips: only non-whitelisted IPs count toward the anomaly
        suspicious_ips = len(set(ip for ip in all_ips if not _is_whitelisted_ip(ip)))

        # Peak RPM: count calls in the busiest 60-second window (last 60s as proxy)
        one_min_ago = now - 60
        calls_last_minute = sum(1 for ts, _ in dq if ts >= one_min_ago)

        # Historical average RPM: calls_last_hour / 60
        avg_rpm = max(calls_last_hour / 60.0, 0.1)

    reasons = []
    if suspicious_ips >= _KEY_ACTIVITY_IP_THRESHOLD:
        reasons.append(f"{suspicious_ips} non-whitelisted IPs in last hour (threshold: {_KEY_ACTIVITY_IP_THRESHOLD})")
    # RPM anomaly only triggers for non-whitelisted IPs
    if not _is_whitelisted_ip(client_ip) and calls_last_minute > _KEY_ACTIVITY_RPM_MULTIPLIER * avg_rpm and calls_last_hour > 10:
        reasons.append(f"{calls_last_minute} RPM vs {avg_rpm:.1f} avg (>{_KEY_ACTIVITY_RPM_MULTIPLIER}x)")

    return {
        "suspicious": bool(reasons),
        "reason": "; ".join(reasons) if reasons else None,
        "unique_ips": unique_ips,
        "calls_last_hour": calls_last_hour,
        "calls_last_minute": calls_last_minute,
        "avg_rpm": round(avg_rpm, 2),
    }


# ---------------------------------------------------------------------------
# 6. Public rate limiting — IP-based for unauthenticated endpoints
# ---------------------------------------------------------------------------

_PUBLIC_RL_LIMIT = 60  # requests per minute per IP per endpoint
_PUBLIC_RL_WINDOW = 60  # seconds


def _check_public_rate_limit(request: Request, endpoint_name: str,
                              upstash_url: str = "", upstash_token: str = "") -> dict:
    """IP-based rate limit for public endpoints. 60 req/min per IP.

    Returns {"count": N, "remaining": N} on success.
    Raises HTTPException(429) when limit exceeded.
    Graceful fallback: if Redis unavailable, allows the request.

    Args:
        request: FastAPI Request object.
        endpoint_name: Name for the rate limit key namespace.
        upstash_url: Upstash Redis REST URL (passed from caller).
        upstash_token: Upstash Redis auth token (passed from caller).
    """
    client_ip = _extract_client_ip(request)
    # Skip rate limiting for localhost (testing)
    if client_ip in ("127.0.0.1", "::1", "testclient", "unknown"):
        return {"count": 0, "remaining": _PUBLIC_RL_LIMIT}

    rl_key = f"public_rl:{endpoint_name}:{client_ip}"
    try:
        if not upstash_url or not upstash_token:
            return {"count": 0, "remaining": _PUBLIC_RL_LIMIT}
        # Atomic INCR + conditional EXPIRE
        incr_r = http_requests.post(
            f"{upstash_url}/INCR/{rl_key}",
            headers={"Authorization": f"Bearer {upstash_token}"},
            timeout=2,
        )
        if not incr_r.ok:
            return {"count": 0, "remaining": _PUBLIC_RL_LIMIT}
        count = int(incr_r.json().get("result", 0))
        # Always renew TTL to prevent orphaned keys without expiry
        http_requests.post(
            f"{upstash_url}/EXPIRE/{rl_key}/{_PUBLIC_RL_WINDOW}",
            headers={"Authorization": f"Bearer {upstash_token}"},
            timeout=1,
        )
        remaining = max(0, _PUBLIC_RL_LIMIT - count)
        if count > _PUBLIC_RL_LIMIT:
            reset_ts = int(_time.time()) + _PUBLIC_RL_WINDOW
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {_PUBLIC_RL_LIMIT} requests per minute. Retry after {_PUBLIC_RL_WINDOW}s.",
                headers={
                    "Retry-After": str(_PUBLIC_RL_WINDOW),
                    "X-RateLimit-Limit": str(_PUBLIC_RL_LIMIT),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_ts),
                },
            )
        return {"count": count, "remaining": remaining}
    except HTTPException:
        raise
    except Exception as e:
        logger.debug("Public rate limit check failed (allowing request): %s", e)
        return {"count": 0, "remaining": _PUBLIC_RL_LIMIT}
