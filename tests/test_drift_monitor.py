"""Tests for D3: scoring drift monitor scheduler."""
import os
import sys

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app, _scheduler_status

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


class TestDriftMonitor:
    def test_scheduler_status_includes_scoring_drift(self):
        r = client.get("/v1/scheduler/status", headers=AUTH)
        assert r.status_code == 200
        d = r.json()
        assert "scoring_drift" in d["jobs"]
        assert d["jobs"]["scoring_drift"]["interval"] == "24h"
        assert d["jobs"]["scoring_drift"]["status"] == "running"

    def test_scheduler_status_includes_drift_alert_flag(self):
        r = client.get("/v1/scheduler/status", headers=AUTH)
        assert r.status_code == 200
        d = r.json()
        assert "scoring_drift_alert" in d
        assert isinstance(d["scoring_drift_alert"], bool)

    def test_drift_alert_true_when_scheduler_marks_alert(self):
        _scheduler_status["scoring_drift_alert"] = "true"
        try:
            r = client.get("/v1/scheduler/status", headers=AUTH)
            assert r.status_code == 200
            assert r.json()["scoring_drift_alert"] is True
        finally:
            _scheduler_status["scoring_drift_alert"] = "false"

    def test_drift_alert_false_when_no_drift(self):
        _scheduler_status["scoring_drift_alert"] = "false"
        r = client.get("/v1/scheduler/status", headers=AUTH)
        assert r.status_code == 200
        assert r.json()["scoring_drift_alert"] is False

    def test_drift_endpoint_requires_auth(self):
        r = client.get("/v1/scheduler/status")
        assert r.status_code in (401, 403)
