"""Tests for GET /v1/research/production-validation (#631)."""
import os
import sys

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


class TestProductionValidation:
    def test_returns_insufficient_data_with_small_sample(self):
        """In a test environment without Supabase, we have 0 rows → insufficient_data."""
        r = client.get("/v1/research/production-validation", headers=AUTH)
        assert r.status_code == 200
        d = r.json()
        # Either we have real data (unlikely in test env) or insufficient
        if d.get("status") == "insufficient_data":
            assert "calls_needed" in d
            assert "current" in d
            assert d["calls_needed"] > 0
            assert d["current"] >= 0
            assert "thresholds" in d
            assert d["thresholds"]["calibration_min"] == 50
            assert d["thresholds"]["pca_min"] == 100
        else:
            # If we DO have data, the response should have n_rows_analyzed
            assert "n_rows_analyzed" in d
            assert d["status"] in ("partial", "ok")

    def test_response_shape_when_sufficient_data(self):
        """Shape-check every expected field. Uses whatever data exists."""
        r = client.get("/v1/research/production-validation", headers=AUTH)
        assert r.status_code == 200
        d = r.json()
        # Every response must have a status
        assert "status" in d
        # Insufficient data path has a specific shape
        if d["status"] == "insufficient_data":
            assert set(d.keys()) >= {"status", "calls_needed", "current", "message", "thresholds"}
            return
        # Sufficient/partial data must have these fields
        assert "n_rows_analyzed" in d
        assert "thresholds_met" in d
        assert "calibration" in d["thresholds_met"]
        assert "pca" in d["thresholds_met"]
        # If calibration threshold met, there's a calibration_curve key
        assert "calibration_curve" in d
        # Omega distribution is computed once we've crossed calibration threshold
        if d["n_rows_analyzed"] > 0:
            assert "omega_distribution" in d
            od = d["omega_distribution"]
            assert set(od.keys()) >= {"n", "mean", "std", "min", "max", "p25", "p50", "p75", "p90", "p99"}

    def test_requires_auth(self):
        r = client.get("/v1/research/production-validation")
        assert r.status_code in (401, 403)
