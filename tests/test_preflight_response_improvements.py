"""Tests for 4 preflight response improvements:
- #455 days_until_block_ci (95% CI + confidence across 4 models)
- #456 confidence_calibration_explanation (human-readable)
- #457 knowledge_age_summary (effective age ± uncertainty + oldest trusted)
- #458 repair_plan ranking (rank, roi_percentile, repair_plan_summary)
"""
import os
import sys

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


_STALE_MULTI = [
    {"id": "m1", "content": "x", "type": "tool_state", "timestamp_age_days": 45,
     "source_trust": 0.6, "source_conflict": 0.4, "downstream_count": 2},
    {"id": "m2", "content": "y", "type": "tool_state", "timestamp_age_days": 25,
     "source_trust": 0.8, "source_conflict": 0.2, "downstream_count": 3},
]
_SCORE_HISTORY_RISING = [40, 42, 45, 48, 50, 52, 55, 58, 60, 62]

_HEALTHY_SINGLE = [{
    "id": "m1", "content": "fresh", "type": "preference",
    "timestamp_age_days": 1, "source_trust": 0.95, "source_conflict": 0.05, "downstream_count": 1,
}]


class TestDaysUntilBlockCI:
    def test_days_until_block_ci_structure(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": _STALE_MULTI,
            "action_type": "reversible",
            "domain": "general",
            "score_history": _SCORE_HISTORY_RISING,
        })
        assert r.status_code == 200
        d = r.json()
        assert "days_until_block" in d
        assert "days_until_block_ci" in d
        ci = d["days_until_block_ci"]
        if ci is not None:
            assert "low" in ci and "high" in ci
            assert ci["low"] <= ci["high"]
            # CI must always contain the reported point estimate (fixed in #455 revision:
            # CI is now centered on the bocpd-scaled point value, not the raw mean)
            assert ci["low"] <= d["days_until_block"] <= ci["high"]

    def test_no_block_sentinel_not_mixed_into_weighted_mean(self):
        """Bug D fix: when some models vote 'no block imminent' (999 sentinel),
        they MUST NOT be averaged in with real estimates. If at least one real
        estimator fires, dissent is flagged; if none fires, a clean null is
        emitted with a no_block_signals list.
        """
        # Falling history → Kalman reports downtrend (emits no-block vote).
        # Fresh healthy memory → low omega, no BLOCK risk on the horizon.
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [{
                "id": "m1", "content": "fresh", "type": "tool_state",
                "timestamp_age_days": 1, "source_trust": 0.95,
                "source_conflict": 0.05, "downstream_count": 1,
            }],
            "action_type": "reversible",
            "domain": "general",
            "score_history": [80, 75, 70, 65, 60, 55, 50, 45, 40, 35],  # clearly falling
        })
        assert r.status_code == 200
        d = r.json()
        # The old bug: weighted mean of [real_estimate, 999.0] = ~500, producing
        # a garbage point estimate. Verify the new behavior: either the estimate
        # is small (real model only, sentinel excluded) or null-with-no_block_signal.
        dub = d.get("days_until_block")
        nb_signals = d.get("days_until_block_no_block_signals")
        if dub is not None:
            # If there's a numeric estimate, it came from REAL models only —
            # it must not be a 999.0 sentinel-contaminated value.
            assert dub < 800.0, f"days_until_block={dub} looks like sentinel contamination"
        if nb_signals:
            # Explicit no-block signals list should name the model that voted
            assert isinstance(nb_signals, list)
            assert all(isinstance(s, str) for s in nb_signals)

    def test_days_until_block_contributing_models_reported(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": _STALE_MULTI,
            "action_type": "reversible",
            "domain": "general",
            "score_history": _SCORE_HISTORY_RISING,
        })
        d = r.json()
        if d.get("days_until_block_ci") is not None:
            # New field: explicit list of which models contributed
            assert "days_until_block_contributing_models" in d
            models = d["days_until_block_contributing_models"]
            assert isinstance(models, list) and len(models) >= 1
            # BOCPD only appears as a shrink marker, never as a standalone estimator
            for m in models:
                if m.startswith("BOCPD"):
                    assert "shrink" in m
                else:
                    assert m in ("OU", "Cox", "Kalman")

    def test_days_until_block_confidence_in_range(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": _STALE_MULTI,
            "action_type": "reversible",
            "domain": "general",
            "score_history": _SCORE_HISTORY_RISING,
        })
        d = r.json()
        conf = d.get("days_until_block_confidence")
        if conf is not None:
            assert 0.0 <= conf <= 1.0

    def test_days_until_block_zero_when_already_blocked(self):
        # High-risk memory — should already be at/above BLOCK threshold.
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [{
                "id": "m1", "content": "x", "type": "tool_state",
                "timestamp_age_days": 200, "source_trust": 0.1,
                "source_conflict": 0.9, "downstream_count": 10,
            }],
            "action_type": "irreversible",
            "domain": "fintech",
        })
        d = r.json()
        # Issue T fix: hard precondition — this test exists to verify the
        # already-blocked code path. If the input stops producing BLOCK (e.g.,
        # scoring logic changes), fail LOUDLY rather than silently pass.
        assert d.get("recommended_action") == "BLOCK", (
            f"Test setup invariant broken: expected BLOCK from stale fintech memory, "
            f"got {d.get('recommended_action')}. The rest of this test would silent-pass. "
            f"Either strengthen the memory staleness or re-design the test."
        )
        assert d["days_until_block"] == 0.0
        assert d["days_until_block_confidence"] == 1.0
        assert "days_until_block_ci" in d
        assert d["days_until_block_ci"] == {"low": 0.0, "high": 0.0}
        assert d["days_until_block_ci_method"] in (
            "already_blocked_no_time_remaining",
            "already_blocked_by_override",
        )
        assert d["days_until_block_n_models"] == 0
        assert d["days_until_block_contributing_models"] == []


class TestConfidenceCalibrationExplanation:
    def test_explanation_field_present_and_non_empty(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": _HEALTHY_SINGLE,
            "action_type": "reversible",
            "domain": "general",
        })
        d = r.json()
        assert "confidence_calibration" in d
        cc = d["confidence_calibration"]
        assert "explanation" in cc
        assert isinstance(cc["explanation"], str)
        assert len(cc["explanation"]) > 20
        # Also mirrored at response root
        assert d.get("confidence_calibration_explanation") == cc["explanation"]

    def test_explanation_references_actual_values(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": _HEALTHY_SINGLE,
            "action_type": "reversible",
            "domain": "general",
        })
        d = r.json()
        explanation = d["confidence_calibration"]["explanation"]
        # Explanation should include at least one of the 3 concrete metrics by name
        assert any(key in explanation for key in ["r_belief", "s_drift", "H¹", "H1"])


class TestKnowledgeAgeSummary:
    def test_summary_string_present_and_formatted(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": _STALE_MULTI,
            "action_type": "reversible",
            "domain": "general",
        })
        d = r.json()
        assert "knowledge_age_summary" in d
        summary = d["knowledge_age_summary"]
        assert summary is not None
        assert "days old" in summary
        assert "±" in summary
        assert "Oldest trusted entry" in summary

    def test_oldest_trusted_entry_reported(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": _STALE_MULTI,
            "action_type": "reversible",
            "domain": "general",
        })
        d = r.json()
        oldest = d.get("knowledge_age_oldest_trusted_days")
        # STALE_MULTI has entries aged 45 and 25 both with trust >= 0.5 → oldest trusted = 45
        assert oldest == 45.0

    def test_no_trusted_entries_returns_null_oldest(self):
        """When every entry has source_trust < 0.5, do NOT fall back to the
        oldest untrusted entry — report None and note it in the summary."""
        untrusted = [
            {"id": "u1", "content": "x", "type": "tool_state", "timestamp_age_days": 50,
             "source_trust": 0.3, "source_conflict": 0.7, "downstream_count": 1},
            {"id": "u2", "content": "y", "type": "tool_state", "timestamp_age_days": 30,
             "source_trust": 0.4, "source_conflict": 0.6, "downstream_count": 1},
        ]
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": untrusted,
            "action_type": "reversible",
            "domain": "general",
        })
        d = r.json()
        # Explicitly null — do NOT report an untrusted entry as "trusted"
        assert d.get("knowledge_age_oldest_trusted_days") is None
        summary = d.get("knowledge_age_summary", "") or ""
        # Summary should flag the absence rather than invent a trusted entry
        assert "No trusted entries" in summary


class TestRepairPlanRanking:
    def test_rank_and_percentile_on_each_entry(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": _STALE_MULTI,
            "action_type": "reversible",
            "domain": "general",
            "score_history": _SCORE_HISTORY_RISING,
        })
        d = r.json()
        rp = d.get("repair_plan", [])
        if not rp:
            return  # no repair plan means nothing to rank
        # Ranks must be 1, 2, 3... in order (since plan is sorted by ROI descending)
        for i, item in enumerate(rp):
            assert item.get("rank") == i + 1, f"rank mismatch at index {i}"
            assert 0.0 <= item.get("roi_percentile", 0) <= 100.0
        # First entry is highest ROI → percentile 100 when n > 1
        if len(rp) > 1:
            assert rp[0]["roi_percentile"] == 100.0

    def test_all_days_until_block_fields_always_present(self):
        """Issue G fix: the full field schema must be present in every code path.
        Run a dry-run call (which takes the 'insufficient history' else branch)
        and verify all 7 days_until_block_* fields are populated."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": _HEALTHY_SINGLE,
            "action_type": "reversible",
            "domain": "general",
            "dry_run": True,
        })
        assert r.status_code == 200
        d = r.json()
        required = {
            "days_until_block",
            "days_until_block_confidence",
            "days_until_block_ci",
            "days_until_block_ci_method",
            "days_until_block_n_models",
            "days_until_block_contributing_models",
            "days_until_block_no_block_signals",
            "days_until_block_model_dissent",
        }
        missing = required - set(d.keys())
        assert not missing, f"missing schema fields: {missing}"

    def test_audit_log_uses_final_not_original_decision(self):
        """Issue R/S fix: audit_log must record the FINAL recommended_action
        after all override paths, not the decision at the mid-preflight
        checkpoint. We trigger a per-type threshold override and verify the
        response shows BLOCK (the override path logs this as final).

        Direct audit_log inspection requires Supabase; instead we assert the
        response structure that WOULD have been audited: final action consistent
        with thermodynamic_cost logging semantics (BLOCK → bits_erased logged).
        """
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [{
                "id": "m1", "content": "stale identity",
                "type": "identity", "timestamp_age_days": 50,
                "source_trust": 0.7, "source_conflict": 0.3, "downstream_count": 5,
            }],
            "action_type": "reversible",
            "domain": "general",
            "per_type_thresholds": True,
        })
        assert r.status_code == 200
        d = r.json()
        # Force BLOCK via per-type override; thermodynamic_cost on response
        # should show bits_erased > 0 (the audit extra gets the same value).
        if d.get("recommended_action") == "BLOCK":
            tc = d.get("thermodynamic_cost")
            assert tc is not None
            assert tc["bits_erased"] > 0
            assert tc["landauer_joules"] > 0
        # If the initial result was NOT BLOCK (check via per_type_original_action)
        # we have direct evidence the decision got overridden — and the audit
        # log, per the fix, records the FINAL decision.
        if d.get("per_type_override_triggered"):
            assert d.get("per_type_original_action") in ("USE_MEMORY", "WARN", "ASK_USER")
            assert d["recommended_action"] == "BLOCK", (
                "per_type override should produce BLOCK; audit_log must record this final state"
            )

    def test_days_until_block_reconciled_with_final_action(self):
        """Issue I fix: when recommended_action is BLOCK (by any override path),
        days_until_block must be 0.0, not a positive future time.

        Issue T: precondition enforced — if per-type override doesn't produce
        BLOCK, fail loudly rather than silent-pass.
        """
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [{
                "id": "m1", "content": "stale identity",
                "type": "identity", "timestamp_age_days": 50,
                "source_trust": 0.7, "source_conflict": 0.3, "downstream_count": 5,
            }],
            "action_type": "reversible",
            "domain": "general",
            "per_type_thresholds": True,
        })
        assert r.status_code == 200
        d = r.json()
        # Precondition: per-type threshold override must have fired
        assert d.get("recommended_action") == "BLOCK", (
            f"Test setup invariant broken: per_type_thresholds=True on stale identity "
            f"memory should produce BLOCK, got {d.get('recommended_action')}. "
            f"Per-type identity threshold is 13; raw omega {d.get('omega_mem_final')} "
            f"should have exceeded it."
        )
        assert d["days_until_block"] == 0.0, (
            f"days_until_block={d['days_until_block']} inconsistent with BLOCK"
        )
        assert d.get("days_until_block_ci_method") in (
            "already_blocked_no_time_remaining",
            "already_blocked_by_override",
        )

    def test_warning_actions_not_ranked_above_real_heals(self):
        """Bug E fix: warnings/monitor actions (SLA_WARNING, BANACH_WARNING,
        CHAOS_WARNING, MONITOR) must NOT outrank actual heal actions just
        because heal_cost was defaulting to 1.0. They now have cost=1000,
        producing near-zero heal_roi."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": _STALE_MULTI,
            "action_type": "reversible",
            "domain": "general",
            "score_history": _SCORE_HISTORY_RISING,
        })
        d = r.json()
        rp = d.get("repair_plan", [])
        if not rp:
            return
        # Every repair_plan item should have the new heal_cost field populated
        for item in rp:
            assert "heal_cost" in item
            assert item["heal_cost"] > 0
        # Warnings (if present anywhere in the list) must have a high cost
        for item in rp:
            action = item.get("action", "")
            if "WARNING" in action or action == "MONITOR":
                assert item["heal_cost"] >= 100.0, f"{action} cost too low: {item['heal_cost']}"

    def test_repair_plan_summary_string(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": _STALE_MULTI,
            "action_type": "reversible",
            "domain": "general",
            "score_history": _SCORE_HISTORY_RISING,
        })
        d = r.json()
        summary = d.get("repair_plan_summary")
        assert summary is not None
        rp = d.get("repair_plan", [])
        if rp:
            # Summary references a rank and the action or heal entry
            assert "Heal entry" in summary or "highest ROI" in summary
            assert "rank 1 of" in summary
        else:
            assert "healthy" in summary.lower()
