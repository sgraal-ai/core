"""sgraal diagnose — test API connectivity, auth, and endpoint health."""
from __future__ import annotations

import sys
import time
from typing import Optional

TIMEOUT = 5
BASE_URL = "https://api.sgraal.com"

# ANSI colors
G = "\033[92m"  # green
Y = "\033[93m"  # yellow
R = "\033[91m"  # red
X = "\033[0m"   # reset


def _check(label: str, fn, timeout: float = TIMEOUT) -> bool:
    """Run a check with timeout. Returns True on success."""
    try:
        t0 = time.time()
        result = fn()
        elapsed = (time.time() - t0) * 1000
        if result is True or (isinstance(result, str) and result):
            print(f"  {G}✅{X} {label}: {result if isinstance(result, str) else 'OK'} ({elapsed:.0f}ms)")
            return True
        else:
            print(f"  {R}❌{X} {label}: FAILED — {result}")
            return False
    except Exception as e:
        err = str(e)[:80]
        print(f"  {R}❌{X} {label}: {err}")
        return False


def run_diagnose(api_key: str, base_url: str = BASE_URL) -> int:
    """Run all diagnostic checks. Returns exit code (0=pass, 1=fail)."""
    import requests

    print(f"\n  Sgraal Diagnose — {base_url}\n")
    all_pass = True

    # 1. API connection
    def check_health():
        r = requests.get(f"{base_url}/health", timeout=TIMEOUT)
        return f"OK ({base_url})" if r.ok else False
    all_pass &= _check("API connection", check_health)

    # 2. Authentication
    def check_auth():
        r = requests.post(f"{base_url}/v1/preflight",
            json={"memory_state": [{"id": "diag", "content": "test", "type": "semantic",
                "timestamp_age_days": 1, "source_trust": 0.9, "source_conflict": 0.1, "downstream_count": 0}]},
            headers={"Authorization": f"Bearer {api_key}"}, timeout=TIMEOUT)
        if r.status_code == 401:
            return False
        if r.status_code == 429:
            return "valid (rate limited)"
        d = r.json()
        tier = "demo" if d.get("demo") else "authenticated"
        omega = d.get("omega_mem_final", "?")
        action = d.get("recommended_action", "?")
        return f"valid ({tier})"
    all_pass &= _check("Authentication", check_auth)

    # 3. Preflight
    def check_preflight():
        r = requests.post(f"{base_url}/v1/preflight",
            json={"memory_state": [{"id": "diag", "content": "test", "type": "semantic",
                "timestamp_age_days": 1, "source_trust": 0.9, "source_conflict": 0.1, "downstream_count": 0}]},
            headers={"Authorization": f"Bearer {api_key}"}, timeout=TIMEOUT)
        if not r.ok:
            return False
        d = r.json()
        return f"working ({d.get('recommended_action')}, omega={d.get('omega_mem_final')})"
    all_pass &= _check("Preflight", check_preflight)

    # 4. Heal
    def check_heal():
        r = requests.post(f"{base_url}/v1/heal",
            json={"entry_id": "diag_test", "action": "REFETCH"},
            headers={"Authorization": f"Bearer {api_key}"}, timeout=TIMEOUT)
        if r.status_code == 403:
            return "blocked (demo key)"
        return "working" if r.ok else False
    all_pass &= _check("Heal", check_heal)

    # 5. Explain
    def check_explain():
        r = requests.post(f"{base_url}/v1/explain",
            json={"preflight_result": {"omega_mem_final": 30, "recommended_action": "WARN"}, "audience": "developer"},
            headers={"Authorization": f"Bearer {api_key}"}, timeout=TIMEOUT)
        return "working" if r.ok else False
    all_pass &= _check("Explain", check_explain)

    # 6. Batch
    def check_batch():
        r = requests.post(f"{base_url}/v1/preflight/batch",
            json={"entries": [{"id": f"d{i}", "content": "t", "type": "semantic",
                "timestamp_age_days": 1, "source_trust": 0.9, "source_conflict": 0.1, "downstream_count": 0} for i in range(3)]},
            headers={"Authorization": f"Bearer {api_key}"}, timeout=TIMEOUT)
        if r.status_code == 403:
            return "blocked (demo key)"
        return f"working (100 entries max)" if r.ok else False
    all_pass &= _check("Batch", check_batch)

    print()
    return 0 if all_pass else 1


def main():
    """CLI entry point: sgraal diagnose --api-key <key>"""
    import argparse
    parser = argparse.ArgumentParser(description="Sgraal API diagnostic tool")
    parser.add_argument("--api-key", required=True, help="Sgraal API key (sg_live_... or sg_demo_playground)")
    parser.add_argument("--api-url", default=BASE_URL, help=f"API base URL (default: {BASE_URL})")
    args = parser.parse_args()

    sys.exit(run_diagnose(args.api_key, args.api_url))


if __name__ == "__main__":
    main()
