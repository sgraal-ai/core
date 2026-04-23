"""Sgraal Fleet Intelligence — circuit breaker and incident alerting.

Circuit breaker: 3-state machine (CLOSED → OPEN → HALF_OPEN → CLOSED)
that protects against Redis outages. When Redis fails 3 times in 30s,
the breaker opens and all Redis calls are skipped for 60s.

Block rate tracking: monitors the ratio of BLOCK decisions in a 5-minute
sliding window. When BLOCK rate exceeds 50% (with ≥10 decisions), triggers
PagerDuty or OpsGenie incident creation with deduplication (30 min cooldown).
"""

import logging
import os
import threading
import time as _time

import requests as http_requests

logger = logging.getLogger(__name__)

__all__ = [
    # Circuit breaker
    "_redis_cb_record_failure",
    "_redis_cb_record_success",
    "_redis_cb_should_skip",
    "_redis_cb_failures",
    "_redis_cb_state",
    "_redis_cb_open_until",
    "_REDIS_CB_THRESHOLD",
    "_REDIS_CB_WINDOW",
    "_REDIS_CB_RECOVERY",
    # Block rate + incident alerting
    "_track_block_rate",
    "_block_rate_window",
    "PAGERDUTY_ROUTING_KEY",
    "OPSGENIE_API_KEY",
]


# ---------------------------------------------------------------------------
# Redis circuit breaker (#386)
# ---------------------------------------------------------------------------

_redis_cb_lock = threading.Lock()
_redis_cb_failures: list[float] = []  # timestamps of recent failures
_redis_cb_state = "CLOSED"  # CLOSED | OPEN | HALF_OPEN
_redis_cb_open_until = 0.0
_REDIS_CB_THRESHOLD = 3  # failures to open
_REDIS_CB_WINDOW = 30  # seconds to count failures
_REDIS_CB_RECOVERY = 60  # seconds before half-open


def _redis_cb_record_failure():
    global _redis_cb_state, _redis_cb_open_until
    now = _time.time()
    with _redis_cb_lock:
        _redis_cb_failures.append(now)
        # Prune old failures
        _redis_cb_failures[:] = [t for t in _redis_cb_failures if now - t < _REDIS_CB_WINDOW]
        if len(_redis_cb_failures) >= _REDIS_CB_THRESHOLD and _redis_cb_state != "OPEN":
            _redis_cb_state = "OPEN"
            _redis_cb_open_until = now + _REDIS_CB_RECOVERY
            logger.warning("Redis circuit breaker OPEN — %d failures in %ds. Skipping Redis for %ds.",
                            len(_redis_cb_failures), _REDIS_CB_WINDOW, _REDIS_CB_RECOVERY)


def _redis_cb_record_success():
    global _redis_cb_state
    with _redis_cb_lock:
        if _redis_cb_state == "HALF_OPEN":
            _redis_cb_state = "CLOSED"
            _redis_cb_failures.clear()
            logger.info("Redis circuit breaker CLOSED — recovery successful.")


def _redis_cb_should_skip() -> bool:
    global _redis_cb_state, _redis_cb_open_until
    now = _time.time()
    with _redis_cb_lock:
        if _redis_cb_state == "CLOSED":
            return False
        if _redis_cb_state == "OPEN" and now >= _redis_cb_open_until:
            _redis_cb_state = "HALF_OPEN"
            return False  # Allow one probe
        if _redis_cb_state == "OPEN":
            return True  # Skip
        return False  # HALF_OPEN — allow probe


# ---------------------------------------------------------------------------
# PagerDuty / OpsGenie auto-incident (#395)
# ---------------------------------------------------------------------------

_block_rate_lock = threading.Lock()
_block_rate_window: list[tuple] = []  # (timestamp, is_block, agent_id, omega)
_last_incident_time = 0.0
_INCIDENT_DEDUP_SECONDS = 1800  # 30 minutes

PAGERDUTY_ROUTING_KEY = os.getenv("PAGERDUTY_ROUTING_KEY")
OPSGENIE_API_KEY = os.getenv("OPSGENIE_API_KEY")


def _track_block_rate(is_block: bool, agent_id: str = "", omega: float = 0):
    global _last_incident_time
    now = _time.time()
    incident_data = None
    with _block_rate_lock:
        _block_rate_window.append((now, is_block, agent_id, omega))
        # Prune older than 5 minutes
        _block_rate_window[:] = [e for e in _block_rate_window if now - e[0] < 300]

        total = len(_block_rate_window)
        if total < 10:
            return
        blocks = sum(1 for e in _block_rate_window if e[1])
        rate = blocks / total

        if rate > 0.5 and now - _last_incident_time > _INCIDENT_DEDUP_SECONDS:
            _last_incident_time = now
            # Top 3 affected agents — capture data inside lock
            agent_scores = {}
            for _, is_b, aid, om in _block_rate_window:
                if is_b and aid:
                    agent_scores[aid] = max(agent_scores.get(aid, 0), om)
            top3 = sorted(agent_scores.items(), key=lambda x: x[1], reverse=True)[:3]
            title = f"Sgraal BLOCK rate spike: {rate*100:.0f}% in last 5 minutes ({len(agent_scores)} agents affected)"
            body = "Top affected agents:\n" + "\n".join(f"  {a}: omega={o:.1f}" for a, o in top3)
            incident_data = {"title": title, "body": body, "rate": rate, "top3": top3}

    # HTTP calls outside the lock to avoid blocking concurrent callers
    if incident_data is not None:
        title = incident_data["title"]
        body = incident_data["body"]
        rate = incident_data["rate"]
        top3 = incident_data["top3"]
        if PAGERDUTY_ROUTING_KEY:
            try:
                http_requests.post("https://events.pagerduty.com/v2/enqueue", json={
                    "routing_key": PAGERDUTY_ROUTING_KEY,
                    "event_action": "trigger",
                    "payload": {"summary": title, "source": "sgraal-api", "severity": "critical",
                                "custom_details": {"block_rate": rate, "agents": dict(top3)}},
                }, timeout=5)
            except Exception as e:
                logger.error("PagerDuty incident creation failed: %s", e)
        elif OPSGENIE_API_KEY:
            try:
                http_requests.post("https://api.opsgenie.com/v2/alerts", json={
                    "message": title, "description": body, "priority": "P1",
                }, headers={"Authorization": f"GenieKey {OPSGENIE_API_KEY}"}, timeout=5)
            except Exception as e:
                logger.error("OpsGenie alert creation failed: %s", e)
        else:
            logger.warning("BLOCK RATE SPIKE: %s — no PagerDuty/OpsGenie configured", title)
