"""Tests for scripts/analyze_churn_risk.py."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestChurnAnalysis:
    def test_module_imports(self):
        """Script must be importable."""
        from scripts.analyze_churn_risk import compute_churn_risk, rank_by_risk
        assert callable(compute_churn_risk)
        assert callable(rank_by_risk)

    def test_basic_churn_detection(self):
        """Tenant with declining call rate should have positive risk score."""
        from scripts.analyze_churn_risk import compute_churn_risk

        now = time.time()
        # Tenant with lots of old calls, few recent calls -> churn risk
        history = []
        for i in range(50):
            history.append({"tenant": "declining_tenant", "timestamp": now - 86400 * 30 + i * 3600})
        # Only 2 recent calls
        history.append({"tenant": "declining_tenant", "timestamp": now - 3600})
        history.append({"tenant": "declining_tenant", "timestamp": now})

        results = compute_churn_risk(history)
        assert "declining_tenant" in results
        info = results["declining_tenant"]
        assert info["risk_score"] > 0
        assert info["trend"] in ("declining", "high_churn_risk")
