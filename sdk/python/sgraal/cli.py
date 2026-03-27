"""sgraal CLI — full command suite for Sgraal memory governance API."""
from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import time

BASE_URL = "https://api.sgraal.com"
CONFIG_DIR = os.path.expanduser("~/.sgraal")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

G = "\033[92m"
Y = "\033[93m"
R = "\033[91m"
B = "\033[94m"
X = "\033[0m"


def _color(enabled: bool) -> tuple:
    if enabled:
        return G, Y, R, B, X
    return "", "", "", "", ""


def _load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}


def _get_api_key(args) -> str:
    if getattr(args, "api_key", None):
        return args.api_key
    env = os.environ.get("SGRAAL_API_KEY")
    if env:
        return env
    cfg = _load_config()
    if cfg.get("api_key"):
        return cfg["api_key"]
    print(f"Error: No API key. Use --api-key, SGRAAL_API_KEY env, or run 'sgraal init'", file=sys.stderr)
    sys.exit(1)


def _get_url(args) -> str:
    return getattr(args, "api_url", None) or os.environ.get("SGRAAL_API_URL", BASE_URL)


def _request(method, url, api_key, data=None, timeout=30):
    import requests
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    if method == "GET":
        return requests.get(url, headers=headers, timeout=timeout)
    return requests.post(url, json=data, headers=headers, timeout=timeout)


def cmd_init(args):
    """Interactive setup — saves config to ~/.sgraal/config.json."""
    g, y, r, b, x = _color(not args.no_color)
    print(f"\n  {b}Sgraal CLI Setup{x}\n")

    api_key = input("  API key (sg_live_...): ").strip()
    if not api_key.startswith("sg_"):
        print(f"  {r}Invalid key format{x}")
        return 1

    domain = input("  Default domain [general]: ").strip() or "general"
    api_url = input(f"  API URL [{BASE_URL}]: ").strip() or BASE_URL

    os.makedirs(CONFIG_DIR, exist_ok=True)
    config = {"api_key": api_key, "domain": domain, "api_url": api_url}
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

    # Enforce 600 permissions
    os.chmod(CONFIG_FILE, stat.S_IRUSR | stat.S_IWUSR)
    print(f"\n  {g}✅{x} Config saved to {CONFIG_FILE} (chmod 600)")

    # Verify permissions
    mode = oct(os.stat(CONFIG_FILE).st_mode)[-3:]
    if mode != "600":
        print(f"  {y}⚠{x}  Permissions are {mode}, expected 600")

    return 0


def cmd_preflight(args):
    """Run preflight scoring."""
    g, y, r, b, x = _color(not args.no_color)
    key = _get_api_key(args)
    url = _get_url(args)

    with open(args.file) as f:
        data = json.load(f)

    payload = {"memory_state": data if isinstance(data, list) else data.get("memory_state", [data])}
    if args.domain:
        payload["domain"] = args.domain
    if args.action:
        payload["action_type"] = args.action

    t0 = time.time()
    resp = _request("POST", f"{url}/v1/preflight", key, payload, args.timeout)
    elapsed = (time.time() - t0) * 1000

    if not resp.ok:
        print(f"  {r}❌{x} Preflight failed: {resp.status_code} {resp.text[:200]}")
        return 1

    result = resp.json()
    if args.output == "json":
        print(json.dumps(result, indent=2))
    else:
        omega = result.get("omega_mem_final", 0)
        action = result.get("recommended_action", "?")
        ac = g if action == "USE_MEMORY" else y if action == "WARN" else r
        print(f"\n  {b}Preflight Result{x} ({elapsed:.0f}ms)")
        print(f"  Ω_MEM: {omega}/100")
        print(f"  Action: {ac}{action}{x}")
        print(f"  Assurance: {result.get('assurance_score', '?')}%")
        repairs = result.get("repair_plan", [])
        if repairs:
            print(f"  Repairs: {len(repairs)} actions")
    return 0


def cmd_heal(args):
    """Trigger healing actions."""
    key = _get_api_key(args)
    url = _get_url(args)

    with open(args.file) as f:
        memory = json.load(f)

    entries = memory if isinstance(memory, list) else [memory]
    for e in entries:
        resp = _request("POST", f"{url}/v1/heal", key, {"entry_id": e.get("id", "unknown"), "action": "REFETCH"}, args.timeout)
        if args.output == "json":
            print(json.dumps(resp.json(), indent=2))
        else:
            print(f"  Healed {e.get('id')}: {resp.json().get('action_taken', '?')}")
    return 0


def cmd_batch(args):
    """Run batch preflight."""
    key = _get_api_key(args)
    url = _get_url(args)

    with open(args.file) as f:
        data = json.load(f)

    entries = data if isinstance(data, list) else data.get("entries", [data])
    payload = {"entries": entries}
    if args.domain:
        payload["domain"] = args.domain

    resp = _request("POST", f"{url}/v1/preflight/batch", key, payload, args.timeout)
    if args.output == "json":
        print(json.dumps(resp.json(), indent=2))
    else:
        results = resp.json().get("results", [])
        print(f"  Batch: {len(results)} entries scored")
    return 0


def cmd_explain(args):
    """Get human-readable explanation."""
    key = _get_api_key(args)
    url = _get_url(args)

    with open(args.preflight_result) as f:
        pr = json.load(f)

    payload = {"preflight_result": pr, "audience": args.audience, "language": args.language}
    resp = _request("POST", f"{url}/v1/explain", key, payload, args.timeout)

    if args.output == "json":
        print(json.dumps(resp.json(), indent=2))
    else:
        d = resp.json()
        print(f"\n  {d.get('summary', '')}")
        print(f"  Root cause: {d.get('root_cause', '')}")
        print(f"  Action: {d.get('recommended_action_human', '')}")
    return 0


def cmd_status(args):
    """Check API status and usage."""
    from .diagnose import run_diagnose
    key = _get_api_key(args)
    url = _get_url(args)
    return run_diagnose(key, url)


def main():
    parser = argparse.ArgumentParser(prog="sgraal", description="Sgraal memory governance CLI")
    parser.add_argument("--api-key", help="Sgraal API key")
    parser.add_argument("--api-url", help=f"API base URL (default: {BASE_URL})")
    parser.add_argument("--output", choices=["text", "json"], default="text")
    parser.add_argument("--no-color", action="store_true")
    parser.add_argument("--timeout", type=int, default=30)

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("init", help="Interactive setup")

    p_pre = sub.add_parser("preflight", help="Run preflight scoring")
    p_pre.add_argument("--file", required=True, help="Memory state JSON file")
    p_pre.add_argument("--domain", default=None)
    p_pre.add_argument("--action", default=None)

    p_heal = sub.add_parser("heal", help="Trigger healing")
    p_heal.add_argument("--file", required=True)

    p_batch = sub.add_parser("batch", help="Batch preflight")
    p_batch.add_argument("--file", required=True)
    p_batch.add_argument("--domain", default=None)

    p_exp = sub.add_parser("explain", help="Human-readable explanation")
    p_exp.add_argument("--preflight-result", required=True)
    p_exp.add_argument("--audience", default="developer")
    p_exp.add_argument("--language", default="en")

    sub.add_parser("status", help="Check API status")
    sub.add_parser("diagnose", help="Run diagnostics")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 0

    cmds = {"init": cmd_init, "preflight": cmd_preflight, "heal": cmd_heal,
            "batch": cmd_batch, "explain": cmd_explain, "status": cmd_status, "diagnose": cmd_status}
    return cmds[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
