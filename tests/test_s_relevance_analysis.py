"""Test that the s_relevance analysis script runs without errors."""
import os
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"


class TestSRelevanceAnalysis:
    def test_script_imports(self):
        """Script should import cleanly."""
        import scripts.analyze_s_relevance_impact as script
        assert hasattr(script, "analyze_corpus")
        assert hasattr(script, "run_preflight")

    def test_single_preflight_runs(self):
        """Single preflight call should work with custom weights."""
        from scripts.analyze_s_relevance_impact import run_preflight
        r = run_preflight(
            [{"id": "e1", "content": "test", "type": "semantic",
              "timestamp_age_days": 5, "source_trust": 0.9,
              "source_conflict": 0.05, "downstream_count": 1}],
            "reversible", "general",
        )
        assert r.get("recommended_action") in ("USE_MEMORY", "WARN", "ASK_USER", "BLOCK")

    def test_zero_relevance_preflight_runs(self):
        """Preflight with s_relevance=0 should still produce a valid decision."""
        from scripts.analyze_s_relevance_impact import run_preflight
        from scoring_engine.omega_mem import WEIGHTS
        zero_weights = dict(WEIGHTS)
        zero_weights["s_relevance"] = 0.0
        r = run_preflight(
            [{"id": "e1", "content": "test", "type": "semantic",
              "timestamp_age_days": 5, "source_trust": 0.9,
              "source_conflict": 0.05, "downstream_count": 1}],
            "reversible", "general", custom_weights=zero_weights,
        )
        assert r.get("recommended_action") in ("USE_MEMORY", "WARN", "ASK_USER", "BLOCK")
