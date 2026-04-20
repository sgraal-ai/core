"""Tests for Round 6: Memory Time Attack — timestamp integrity detection."""
import pytest
from unittest.mock import patch
from datetime import datetime


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_entry(id="mem_001", content="Current policy for handling returns.",
                type="semantic", age=0, trust=0.9, conflict=0.05, downstream=1):
    return {
        "id": id, "content": content, "type": type,
        "timestamp_age_days": age, "source_trust": trust,
        "source_conflict": conflict, "downstream_count": downstream,
    }


def _call_check(entries):
    """Import and call the detection function directly."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from api.main import _check_timestamp_integrity
    return _check_timestamp_integrity(entries)


def _preflight(entries, domain="general", action_type="informational"):
    """Call full preflight via test client."""
    from fastapi.testclient import TestClient
    from api.main import app
    client = TestClient(app)
    payload = {
        "memory_state": entries,
        "domain": domain,
        "action_type": action_type,
    }
    resp = client.post("/v1/preflight", json=payload,
                       headers={"Authorization": "Bearer sg_demo_playground"})
    assert resp.status_code == 200, f"Preflight returned {resp.status_code}: {resp.text}"
    return resp.json()


# ── Pattern 1: Content-age mismatch ─────────────────────────────────────────

class TestContentAgeMismatch:
    def test_timestamp_zeroing_detected(self):
        """PATTERN 1: past-date content with age=0 → MANIPULATED."""
        entry = _make_entry(
            content="Per Q2 2024 SEC ruling and the 2023 Basel III update, crypto assets "
                    "were required to be reported under the deprecated v2.1 framework. "
                    "This legacy guidance was mandatory for all 2024 filings.",
            age=0, downstream=8,
        )
        result = _call_check([entry])
        assert result["timestamp_integrity"] == "MANIPULATED"
        assert any("content_age_mismatch:manipulated" in f for f in result["timestamp_flags"])
        assert result["timestamp_risk_score"] == 1.0

    def test_clean_fresh_memory_valid(self):
        """No past markers + age=0 → VALID."""
        entry = _make_entry(
            content="Current return policy allows refunds within 30 days of purchase. "
                    "Contact support for details on eligible items.",
            age=0, downstream=2,
        )
        result = _call_check([entry])
        assert result["timestamp_integrity"] == "VALID"
        assert result["timestamp_flags"] == []

    def test_two_markers_suspicious(self):
        """2 markers + age < 2 → SUSPICIOUS (not MANIPULATED)."""
        entry = _make_entry(
            content="The 2024 compliance framework was mandatory for reporting.",
            age=0.5, downstream=2,
        )
        result = _call_check([entry])
        assert result["timestamp_integrity"] == "SUSPICIOUS"
        assert any("suspicious" in f for f in result["timestamp_flags"])

    def test_old_age_skipped(self):
        """Entry with age >= 2 is not checked for content markers."""
        entry = _make_entry(
            content="Per Q2 2024 SEC ruling, the deprecated v2.1 framework was mandatory "
                    "for all 2023 filings under the legacy system.",
            age=30, downstream=8,
        )
        result = _call_check([entry])
        # Should not flag content-age mismatch since age is high
        assert not any("content_age_mismatch" in f for f in result["timestamp_flags"])


# ── Pattern 2: Fleet-wide age collapse ──────────────────────────────────────

class TestFleetAgeCollapse:
    def test_fleet_age_collapse_manipulated(self):
        """3+ entries age=0, one has conflict > 0.3 → MANIPULATED."""
        entries = [
            _make_entry(id="e1", age=0, conflict=0.05),
            _make_entry(id="e2", age=0, conflict=0.4),
            _make_entry(id="e3", age=0, conflict=0.05),
        ]
        result = _call_check(entries)
        assert result["timestamp_integrity"] == "MANIPULATED"
        assert any("fleet_age_collapse:manipulated" in f for f in result["timestamp_flags"])

    def test_fleet_age_collapse_suspicious(self):
        """3+ entries age < 0.5 but not all zero → SUSPICIOUS."""
        entries = [
            _make_entry(id="e1", age=0.1, conflict=0.05),
            _make_entry(id="e2", age=0.2, conflict=0.35),
            _make_entry(id="e3", age=0.4, conflict=0.05),
        ]
        result = _call_check(entries)
        assert result["timestamp_integrity"] == "SUSPICIOUS"
        assert any("fleet_age_collapse:suspicious" in f for f in result["timestamp_flags"])

    def test_fleet_age_collapse_clean(self):
        """3+ entries age=0, no conflict → SUSPICIOUS (not manipulated)."""
        entries = [
            _make_entry(id="e1", age=0, conflict=0.05),
            _make_entry(id="e2", age=0, conflict=0.1),
            _make_entry(id="e3", age=0, conflict=0.05),
        ]
        result = _call_check(entries)
        # All zero but no high conflict → suspicious (fleet collapse detected) but not manipulated
        assert result["timestamp_integrity"] == "SUSPICIOUS"
        assert any("fleet_age_collapse" in f for f in result["timestamp_flags"])
        assert not any("manipulated" in f for f in result["timestamp_flags"])

    def test_two_entries_no_fleet_collapse(self):
        """Only 2 entries → no fleet collapse flag."""
        entries = [
            _make_entry(id="e1", age=0, conflict=0.5),
            _make_entry(id="e2", age=0, conflict=0.5),
        ]
        result = _call_check(entries)
        assert not any("fleet_age_collapse" in f for f in result["timestamp_flags"])


# ── Pattern 4: Anchor inconsistency ────────────────────────────────────────

class TestAnchorInconsistency:
    def test_anchor_inconsistency(self):
        """downstream_count=10, age=0 → SUSPICIOUS."""
        entry = _make_entry(age=0, downstream=10)
        result = _call_check([entry])
        assert result["timestamp_integrity"] == "SUSPICIOUS"
        assert any("anchor_inconsistency" in f for f in result["timestamp_flags"])

    def test_anchor_low_downstream_valid(self):
        """downstream_count=2, age=0 → no anchor flag."""
        entry = _make_entry(age=0, downstream=2)
        result = _call_check([entry])
        assert not any("anchor_inconsistency" in f for f in result["timestamp_flags"])

    def test_anchor_high_age_valid(self):
        """downstream_count=10 but age=5 → no anchor flag."""
        entry = _make_entry(age=5, downstream=10)
        result = _call_check([entry])
        assert not any("anchor_inconsistency" in f for f in result["timestamp_flags"])


# ── Preflight integration ───────────────────────────────────────────────────

class TestPreflightIntegration:
    def test_manipulated_forces_block(self):
        """MANIPULATED always overrides to BLOCK."""
        entry = _make_entry(
            content="Per Q2 2024 SEC ruling and the 2023 Basel III update, crypto assets "
                    "were required under the deprecated v2.1 legacy framework as mandatory.",
            age=0, trust=0.95, conflict=0.01, downstream=8,
        )
        resp = _preflight([entry], domain="fintech", action_type="informational")
        assert resp["timestamp_integrity"] == "MANIPULATED"
        assert resp["recommended_action"] == "BLOCK"

    def test_suspicious_alone_does_not_escalate(self):
        """SUSPICIOUS alone does not escalate — requires corroboration from another layer.

        Phase 7b corroboration gate: fleet_age_collapse SUSPICIOUS without
        another detection layer co-firing is annotation only, not escalation.
        Prevents false positives on multi-entry controls with similar ages.
        """
        entry = _make_entry(
            content="Current policy for handling customer returns within 30 days.",
            age=0, trust=0.95, conflict=0.01, downstream=10,
        )
        resp = _preflight([entry], domain="general", action_type="informational")
        assert resp["timestamp_integrity"] == "SUSPICIOUS"
        # Corroboration gate: no other layer fires → no escalation
        assert resp["recommended_action"] == "USE_MEMORY"

    def test_timestamp_flags_in_response(self):
        """timestamp_flags populated in response."""
        entry = _make_entry(age=0, downstream=8)
        resp = _preflight([entry])
        assert "timestamp_flags" in resp
        assert isinstance(resp["timestamp_flags"], list)

    def test_repair_plan_includes_timestamp_advice(self):
        """SUSPICIOUS/MANIPULATED adds VERIFY_TIMESTAMP to repair_plan."""
        entry = _make_entry(
            content="Per Q2 2024 SEC ruling and the 2023 Basel III update, crypto assets "
                    "were required under the deprecated v2.1 legacy framework as mandatory.",
            age=0, downstream=8,
        )
        resp = _preflight([entry], domain="fintech")
        rp_actions = [r["action"] for r in resp.get("repair_plan", [])]
        assert "VERIFY_TIMESTAMP" in rp_actions

    def test_valid_no_escalation(self):
        """VALID entries get no timestamp escalation."""
        entry = _make_entry(
            content="Process refund requests within 3 business days.",
            age=5, trust=0.9, conflict=0.05, downstream=1,
        )
        resp = _preflight([entry])
        assert resp["timestamp_integrity"] == "VALID"
        assert resp["timestamp_flags"] == []

    def test_timestamp_integrity_always_present(self):
        """Every preflight response has timestamp_integrity."""
        entry = _make_entry(age=10, downstream=1)
        resp = _preflight([entry])
        assert "timestamp_integrity" in resp
        assert resp["timestamp_integrity"] in ("VALID", "SUSPICIOUS", "MANIPULATED")
