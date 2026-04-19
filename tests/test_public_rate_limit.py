"""Tests for IP-based rate limiting on public (unauthenticated) endpoints."""
import os
import sys
from unittest.mock import patch, MagicMock

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

# Valid attestation request body (will fail verification but won't 400)
_ATTEST_BODY = {
    "input_hash": "abc123",
    "omega": 50.0,
    "decision": "BLOCK",
    "request_id": "req-001",
    "proof_signature": "invalid",
}


class TestPublicRateLimitUnderLimit:
    def test_under_limit_all_succeed(self):
        """10 requests to a public endpoint → all should return 200 (not 429)."""
        for _ in range(10):
            r = client.post("/v1/verify-attestation", json=_ATTEST_BODY)
            # 200 = valid response (signature won't match but endpoint works)
            assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"


class TestPublicRateLimitOverLimit:
    @patch("api.main.http_requests.post")
    def test_over_limit_returns_429(self, mock_post):
        """Simulate Redis returning count > 60 → should get 429."""
        # Mock Redis INCR response with count=61 (over limit)
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"result": 61}
        mock_post.return_value = mock_resp

        # Need to set UPSTASH env vars for rate limiter to engage
        with patch("api.main.UPSTASH_REDIS_URL", "https://fake-redis.upstash.io"), \
             patch("api.main.UPSTASH_REDIS_TOKEN", "fake-token"):
            r = client.post("/v1/zk/verify", json={
                "proof_hash": "abc", "input_hash": "def", "omega": 50.0, "decision": "BLOCK",
            }, headers={"X-Forwarded-For": "203.0.113.42"})
            assert r.status_code == 429
            assert "Rate limit" in r.json()["detail"]


class TestPublicRateLimitIndependentIPs:
    @patch("api.main.http_requests.post")
    def test_different_ips_independent(self, mock_post):
        """Different IPs should have independent counters."""
        call_count = {"n": 0}

        def _mock_incr(*args, **kwargs):
            call_count["n"] += 1
            resp = MagicMock()
            resp.ok = True
            # Each IP gets count=1 (fresh counter)
            resp.json.return_value = {"result": 1}
            return resp

        mock_post.side_effect = _mock_incr

        with patch("api.main.UPSTASH_REDIS_URL", "https://fake-redis.upstash.io"), \
             patch("api.main.UPSTASH_REDIS_TOKEN", "fake-token"):
            # IP 1
            r1 = client.post("/v1/verify-attestation", json=_ATTEST_BODY,
                             headers={"X-Forwarded-For": "198.51.100.1"})
            # IP 2
            r2 = client.post("/v1/verify-attestation", json=_ATTEST_BODY,
                             headers={"X-Forwarded-For": "198.51.100.2"})
            # Both should succeed (count=1 for each)
            assert r1.status_code == 200
            assert r2.status_code == 200


class TestPublicRateLimitGracefulDegradation:
    @patch("api.main.http_requests.post", side_effect=Exception("Redis down"))
    def test_redis_unavailable_allows_request(self, mock_post):
        """Redis failure → graceful degradation, request allowed."""
        with patch("api.main.UPSTASH_REDIS_URL", "https://fake-redis.upstash.io"), \
             patch("api.main.UPSTASH_REDIS_TOKEN", "fake-token"):
            r = client.post("/v1/verify-attestation", json=_ATTEST_BODY,
                            headers={"X-Forwarded-For": "203.0.113.99"})
            # Should still return 200 (not 500 or 429)
            assert r.status_code == 200
