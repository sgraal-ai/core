"""sgraal doctor — environment health check."""
import os
import sys
import time

import click


def _check_python():
    v = sys.version_info
    version = f"{v.major}.{v.minor}.{v.micro}"
    ok = (v.major, v.minor) >= (3, 10)
    return ok, f"Python {version}", "Python >= 3.10 required" if not ok else None


def _check_package():
    try:
        import sgraal  # type: ignore[import-not-found]
        version = getattr(sgraal, "__version__", "unknown")
        return True, f"sgraal {version} installed", None
    except ImportError:
        return False, "sgraal not installed", "pip install sgraal"


def _check_api_key():
    key = os.environ.get("SGRAAL_API_KEY", "")
    if key:
        masked = key[:6] + "..." + key[-4:] if len(key) > 10 else "***"
        return True, f"SGRAAL_API_KEY set ({masked})", None
    return False, "SGRAAL_API_KEY not set", "export SGRAAL_API_KEY=sg_live_..."


def _check_api_reachable():
    url = os.environ.get("SGRAAL_API_URL", "https://api.sgraal.com")
    try:
        import requests
        t0 = time.monotonic()
        r = requests.get(f"{url}/health", timeout=5)
        ms = round((time.monotonic() - t0) * 1000)
        if r.status_code == 200:
            return True, f"API reachable ({url}, {ms}ms)", None
        return False, f"API returned HTTP {r.status_code}", None
    except ImportError:
        return None, "requests not installed", "pip install requests"
    except Exception as e:
        return False, f"API unreachable ({url})", str(e)[:80]


def _check_redis():
    url = os.environ.get("UPSTASH_REDIS_URL", "")
    if not url:
        return None, "Redis URL not configured (using fallback)", None
    try:
        import requests
        r = requests.get(url, timeout=3)
        return True, "Redis reachable", None
    except Exception as e:
        return False, "Redis unreachable", str(e)[:80]


def _check_supabase():
    url = os.environ.get("SUPABASE_URL", "")
    if not url:
        return None, "Supabase URL not configured", None
    try:
        import requests
        r = requests.get(f"{url}/rest/v1/", timeout=3,
                         headers={"apikey": os.environ.get("SUPABASE_KEY", "")})
        if r.status_code in (200, 401):  # 401 = reachable but needs auth
            return True, "Supabase reachable", None
        return False, f"Supabase returned HTTP {r.status_code}", None
    except Exception as e:
        return False, "Supabase unreachable", str(e)[:80]


_CHECKS = [
    ("Python version", _check_python),
    ("sgraal package", _check_package),
    ("API key", _check_api_key),
    ("API reachable", _check_api_reachable),
    ("Redis", _check_redis),
    ("Supabase", _check_supabase),
]

_ICONS = {True: "\u2713", False: "\u2717", None: "\u26A0"}


@click.command("doctor")
def doctor():
    """Check environment health for Sgraal CLI."""
    has_failure = False
    for name, check_fn in _CHECKS:
        ok, msg, hint = check_fn()
        icon = _ICONS.get(ok, "?")
        click.echo(f"  {icon} {msg}")
        if hint:
            click.echo(f"    {hint}")
        if ok is False:
            has_failure = True
    if has_failure:
        raise SystemExit(1)
