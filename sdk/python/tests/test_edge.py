"""Tests for the zero-dependency edge mode.

Run from /Users/zsobrakpeter/core/sdk/python:
    python3 -m pytest tests/test_edge.py -v
"""

from __future__ import annotations

import subprocess
import sys


def test_healthy_memory_returns_use_memory():
    """Fresh, high-trust tool_state should score low and USE_MEMORY."""
    from sgraal.edge import edge_preflight

    result = edge_preflight(
        [
            {
                "id": "m1",
                "content": "Customer's current cart",
                "type": "tool_state",
                "timestamp_age_days": 1,
                "source_trust": 0.95,
                "source_conflict": 0.05,
            }
        ],
        domain="general",
        action_type="standard",
    )
    assert result["decision"] == "USE_MEMORY"
    assert result["omega"] < 25.0
    assert result["edge_mode"] is True
    assert result["sdk_version"] == "0.3.1"
    assert set(result["five_signals"].keys()) == {
        "risk",
        "decay",
        "trust",
        "corruption",
        "belief",
    }


def test_stale_memory_returns_warn_or_block():
    """A stale, medium-trust tool_state should escalate beyond USE_MEMORY."""
    from sgraal.edge import edge_preflight

    result = edge_preflight(
        [
            {
                "id": "m2",
                "content": "Stale billing state",
                "type": "tool_state",
                "timestamp_age_days": 60,
                "source_trust": 0.5,
                "source_conflict": 0.3,
            }
        ],
        domain="fintech",
        action_type="standard",
    )
    assert result["decision"] in ("WARN", "ASK_USER", "BLOCK")
    assert result["omega"] > 25.0
    assert result["dominant_type"] == "tool_state"


def test_identity_type_stricter_threshold():
    """An identity entry with low omega should still BLOCK thanks to threshold=13."""
    from sgraal.edge import edge_preflight

    result = edge_preflight(
        [
            {
                "id": "m3",
                "content": "Agent identity attribute",
                "type": "identity",
                "timestamp_age_days": 50,
                "source_trust": 0.7,
                "source_conflict": 0.2,
            }
        ],
        domain="general",
        action_type="standard",
    )
    # Identity has lambda=0.002, so Risk stays low; omega lands ~17.
    # That's well below the global BLOCK (70), but above identity's 13.
    assert 13.0 <= result["omega"] < 25.0
    assert result["decision"] == "BLOCK"
    assert result["per_type_threshold_applied"] is True
    assert result["dominant_type"] == "identity"


def test_per_type_selection_with_mixed_entries():
    """Mixed fresh tool_state + stale identity should surface identity as dominant."""
    from sgraal.edge import edge_preflight

    result = edge_preflight(
        [
            {
                "id": "m4a",
                "content": "Current session state",
                "type": "tool_state",
                "timestamp_age_days": 1,
                "source_trust": 0.95,
                "source_conflict": 0.05,
            },
            {
                "id": "m4b",
                "content": "Agent's identity",
                "type": "identity",
                "timestamp_age_days": 500,
                "source_trust": 0.4,
                "source_conflict": 0.4,
            },
        ],
        domain="general",
        action_type="standard",
    )
    assert result["dominant_type"] == "identity"
    assert result["decision"] == "BLOCK"
    assert result["per_type_threshold_applied"] is True


def test_zero_dependencies():
    """`sgraal/edge.py` must load without any non-stdlib packages in sys.modules."""
    # Run a probe in a fresh, isolated subprocess that loads edge.py *directly*
    # via importlib (skipping the package __init__.py, which pulls in
    # requests-dependent modules like client.py). After loading, check that
    # no non-stdlib packages snuck into sys.modules.
    import pathlib

    edge_file = pathlib.Path(__file__).resolve().parent.parent / "sgraal" / "edge.py"
    assert edge_file.is_file(), f"edge.py not found at {edge_file}"

    probe = (
        "import sys, importlib.util\n"
        f"spec = importlib.util.spec_from_file_location('sgraal_edge', r'{edge_file}')\n"
        "mod = importlib.util.module_from_spec(spec)\n"
        "sys.modules['sgraal_edge'] = mod\n"
        "spec.loader.exec_module(mod)\n"
        "banned = {'requests', 'httpx', 'urllib3', 'redis', 'supabase',\n"
        "          'postgrest', 'numpy', 'scipy', 'pandas', 'pydantic',\n"
        "          'fastapi', 'starlette', 'uvicorn', 'google', 'openai',\n"
        "          'stripe'}\n"
        "leaked = sorted(banned & set(sys.modules))\n"
        "assert not leaked, f'non-stdlib modules leaked into edge import: {leaked}'\n"
        # Spot-check the module actually works
        "r = mod.edge_preflight([{'id':'x','type':'tool_state',\n"
        "    'timestamp_age_days':1,'source_trust':0.9,'source_conflict':0.1}])\n"
        "assert r['edge_mode'] is True\n"
        "assert r['decision'] in ('USE_MEMORY','WARN','ASK_USER','BLOCK')\n"
        "print('OK')\n"
    )
    completed = subprocess.run(
        [sys.executable, "-I", "-c", probe],
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, (
        "edge import smoke test failed:\n"
        f"stdout={completed.stdout}\nstderr={completed.stderr}"
    )
    assert "OK" in completed.stdout


def test_destructive_action_lowers_threshold():
    """Omega around 65 should BLOCK when action is destructive (threshold 60)."""
    from sgraal.edge import edge_preflight

    entry = {
        "id": "m6",
        "content": "Unknown-type memory",
        "type": "other",  # not in PER_TYPE_THRESHOLDS
        "timestamp_age_days": 60,
        "source_trust": 0.3,
        "source_conflict": 0.5,
    }

    baseline = edge_preflight([entry], domain="general", action_type="standard")
    destructive = edge_preflight([entry], domain="general", action_type="destructive")

    # Both calls see the same omega (action type doesn't move omega itself).
    assert baseline["omega"] == destructive["omega"]
    # Omega lands between the adjusted and unadjusted BLOCK thresholds.
    assert 60.0 <= baseline["omega"] < 70.0
    # Non-destructive keeps the global BLOCK at 70 so it must *not* BLOCK.
    assert baseline["decision"] != "BLOCK"
    # Destructive drops BLOCK to 60 so omega >= 60 must BLOCK.
    assert destructive["decision"] == "BLOCK"
    assert destructive["effective_block_threshold"] == 60.0
