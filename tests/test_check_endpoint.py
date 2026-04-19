"""Tests for POST /v1/check — the simple door into Sgraal."""
import os
import sys

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}
DEMO_AUTH = {"Authorization": "Bearer sg_demo_playground"}


class TestCheckCleanMemories:
    def test_clean_strings_safe(self):
        """Plain clean strings → safe=true, decision=USE_MEMORY."""
        r = client.post("/v1/check", headers=AUTH, json={
            "memories": [
                "The user prefers dark mode.",
                "Project uses React and TypeScript.",
                "Deploy target is staging.",
            ],
        })
        assert r.status_code == 200
        d = r.json()
        assert d["safe"] is True
        assert d["decision"] in ("USE_MEMORY", "WARN")
        assert "passed validation" in d["reason"] or "usable" in d["reason"]

    def test_demo_key_works(self):
        """Demo key should work on /v1/check."""
        r = client.post("/v1/check", headers=DEMO_AUTH, json={
            "memories": ["Simple test memory."],
        })
        assert r.status_code == 200
        assert r.json()["safe"] is True


class TestCheckSecretDetection:
    def test_api_key_blocked(self):
        """Memory containing sk-... API key → immediate BLOCK."""
        r = client.post("/v1/check", headers=AUTH, json={
            "memories": [
                "The API key is sk-proj-abc123def456ghi789jkl012mno345",
                "Deploy to production.",
            ],
        })
        assert r.status_code == 200
        d = r.json()
        assert d["safe"] is False
        assert d["decision"] == "BLOCK"
        assert d["omega"] == 100.0
        assert "secret" in d["reason"].lower()
        assert d["secret_detected"] is True

    def test_bearer_token_blocked(self):
        """Memory containing Bearer token → BLOCK."""
        r = client.post("/v1/check", headers=AUTH, json={
            "memories": ["Authorization header is Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abc123"],
        })
        assert r.status_code == 200
        d = r.json()
        assert d["safe"] is False
        assert d["decision"] == "BLOCK"
        assert "secret" in d["reason"].lower() or "token" in d["reason"].lower()

    def test_aws_key_blocked(self):
        """Memory containing AWS access key → BLOCK."""
        r = client.post("/v1/check", headers=AUTH, json={
            "memories": ["AWS credentials: AKIAIOSFODNN7EXAMPLE"],
        })
        assert r.status_code == 200
        d = r.json()
        assert d["safe"] is False
        assert d["decision"] == "BLOCK"


class TestCheckResponseStructure:
    def test_full_response_shape(self):
        """Response must contain all required fields."""
        r = client.post("/v1/check", headers=AUTH, json={
            "memories": ["The weather is sunny today."],
        })
        assert r.status_code == 200
        d = r.json()
        assert "safe" in d
        assert "reason" in d
        assert "action" in d
        assert "omega" in d
        assert "decision" in d
        assert "request_id" in d
        assert isinstance(d["safe"], bool)
        assert isinstance(d["reason"], str)
        assert isinstance(d["action"], str)
        assert isinstance(d["omega"], (int, float))
        assert d["decision"] in ("USE_MEMORY", "WARN", "ASK_USER", "BLOCK")

    def test_details_url_present(self):
        """Response should include details_url for full preflight result."""
        r = client.post("/v1/check", headers=AUTH, json={
            "memories": ["Some memory content."],
        })
        d = r.json()
        assert "details_url" in d
        assert "/v1/check/" in d["details_url"]
        assert "/details" in d["details_url"]

    def test_empty_memories_rejected(self):
        """Empty memories list → 400."""
        r = client.post("/v1/check", headers=AUTH, json={"memories": []})
        assert r.status_code == 400
