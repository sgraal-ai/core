"""Sgraal Webhook Dispatch — outbound notifications for decisions and security events.

Pure dispatch functions that fire webhooks in background threads.
The webhook registry (_webhooks list) is owned by api/main.py and
passed to dispatch functions via parameter.

Formatters:
    - Slack: markdown blocks with emoji-coded decision
    - PagerDuty: v2 Events API trigger payload

Signing:
    - HMAC-SHA256 signature in X-Sgraal-Signature header
"""

import hashlib
import hmac as _hmac
import json as _json
import logging
import threading
import time as _time
import urllib.parse
from datetime import datetime, timezone

import requests as http_requests

from api.helpers import _dns_cache, _DNS_CACHE_TTL

logger = logging.getLogger("sgraal.webhooks")

__all__ = [
    "_dispatch_webhooks",
    "_dispatch_security_event",
    "_sign_payload",
    "_format_slack",
    "_format_pagerduty",
]


def _resolve_url_from_cache(url: str) -> str:
    """If the hostname has a cached DNS entry, substitute it to prevent DNS rebinding."""
    try:
        parsed = urllib.parse.urlparse(url)
        hostname = parsed.hostname
        if hostname and hostname in _dns_cache:
            cached_ip, cached_ts = _dns_cache[hostname]
            if _time.time() - cached_ts < _DNS_CACHE_TTL:
                # Replace hostname with cached IP, set Host header via the URL
                port = parsed.port
                port_str = f":{port}" if port else ""
                return url.replace(f"://{hostname}{port_str}", f"://{cached_ip}{port_str}"), hostname
        return url, None
    except Exception:
        return url, None


def _sign_payload(payload: str, secret: str) -> str:
    return _hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def _format_slack(payload: dict) -> dict:
    decision = payload["decision"]
    emoji = ":red_circle:" if decision == "BLOCK" else ":warning:"
    return {
        "text": f"{emoji} Sgraal {decision}: Ω={payload['omega_score']} | request={payload['request_id']}",
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": (
                f"*{decision}* — Ω_MEM = {payload['omega_score']}\n"
                f"Request: `{payload['request_id']}`\n"
                f"Time: {payload['timestamp']}"
            )}},
        ],
    }


def _format_pagerduty(payload: dict) -> dict:
    return {
        "routing_key": "",  # user provides in webhook URL
        "event_action": "trigger",
        "payload": {
            "summary": f"Sgraal {payload['decision']}: Ω={payload['omega_score']}",
            "severity": "critical" if payload["decision"] == "BLOCK" else "warning",
            "source": "sgraal",
            "custom_details": payload,
        },
    }


def _dispatch_webhooks(decision: str, request_id: str, omega: float, entry_ids: list[str],
                       webhooks: list[dict] = None):
    """Fire webhooks matching the decision. Runs in background thread.

    Args:
        decision: USE_MEMORY | WARN | ASK_USER | BLOCK
        request_id: Preflight request ID.
        omega: Final omega score.
        entry_ids: Memory entry IDs scored.
        webhooks: List of registered webhook dicts (from main.py _webhooks).
    """
    if not webhooks:
        return
    now = datetime.now(timezone.utc).isoformat()
    base_payload = {
        "request_id": request_id,
        "decision": decision,
        "omega_score": omega,
        "memory_ids": entry_ids,
        "timestamp": now,
    }

    for hook in webhooks:
        if decision not in hook["events"]:
            continue

        target = hook.get("target", "generic")
        if target == "slack":
            body = _format_slack(base_payload)
        elif target == "pagerduty":
            body = _format_pagerduty(base_payload)
        else:
            body = base_payload

        payload_str = _json.dumps(body, sort_keys=True)
        signature = _sign_payload(payload_str, hook["secret"])

        def _send(url=hook["url"], data=payload_str, sig=signature):
            try:
                resolved_url, original_host = _resolve_url_from_cache(url)
                headers = {
                    "Content-Type": "application/json",
                    "X-Sgraal-Signature": sig,
                }
                if original_host:
                    headers["Host"] = original_host
                http_requests.post(
                    resolved_url,
                    data=data,
                    headers=headers,
                    timeout=5,
                )
            except Exception as exc:
                logger.warning("Webhook dispatch failed for %s: %s", url, exc)

        threading.Thread(target=_send, daemon=True).start()


def _dispatch_security_event(event_type: str, details: dict, key_hash: str,
                              webhooks: list[dict] = None):
    """Dispatch security event to registered webhooks.

    Args:
        event_type: Event name (e.g. "circuit_breaker_open").
        details: Event details dict.
        key_hash: Tenant key hash (for logging context).
        webhooks: List of registered webhook dicts (from main.py _webhooks).
    """
    if not webhooks:
        return
    for wh in webhooks:
        events = wh.get("events", [])
        if event_type not in events and "security" not in events:
            continue
        payload = {"event": event_type, "details": details, "timestamp": datetime.now(timezone.utc).isoformat()}
        try:
            sig = _sign_payload(_json.dumps(payload, sort_keys=True), wh.get("secret", ""))
            def _send_sec(url=wh["url"], data=_json.dumps(payload, sort_keys=True), s=sig):
                try:
                    resolved_url, original_host = _resolve_url_from_cache(url)
                    headers = {"Content-Type": "application/json", "X-Sgraal-Signature": s}
                    if original_host:
                        headers["Host"] = original_host
                    http_requests.post(resolved_url, data=data, headers=headers, timeout=5)
                except Exception as exc:
                    logger.warning("Security event dispatch failed for %s: %s", url, exc)
            threading.Thread(target=_send_sec, daemon=True).start()
        except Exception as exc:
            logger.warning("Security event dispatch setup failed for %s: %s", event_type, exc)
