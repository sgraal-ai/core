"""Tests for #796 IP allowlisting per API key."""
import os
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"

from fastapi.testclient import TestClient
from api.main import app, _check_ip_allowlist
from api.redis_state import redis_set, redis_delete, redis_available
from fastapi import HTTPException
import pytest

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


class TestIPAllowlistCheck:
    def test_allowed_ip_succeeds(self):
        """Request from an allowed IP passes the check."""
        if not redis_available():
            pytest.skip("Redis not available")
        import hashlib
        kh = hashlib.sha256("sg_test_key_001".encode()).hexdigest()
        redis_set(f"ip_allowlist:{kh}", ["127.0.0.0/8", "10.0.0.0/8"], ttl=60)
        try:
            result = _check_ip_allowlist(kh, "127.0.0.1")
            assert result is True
        finally:
            redis_delete(f"ip_allowlist:{kh}")

    def test_blocked_ip_returns_403(self):
        """Request from a non-allowed IP raises 403."""
        if not redis_available():
            pytest.skip("Redis not available")
        import hashlib
        kh = hashlib.sha256("sg_test_key_001".encode()).hexdigest()
        redis_set(f"ip_allowlist:{kh}", ["192.168.1.0/24"], ttl=60)
        try:
            with pytest.raises(HTTPException) as exc_info:
                _check_ip_allowlist(kh, "10.0.0.1")
            assert exc_info.value.status_code == 403
            assert exc_info.value.detail["error"] == "ip_not_allowed"
        finally:
            redis_delete(f"ip_allowlist:{kh}")

    def test_empty_allowlist_allows_all(self):
        """No allowlist set means all IPs are allowed."""
        import hashlib
        kh = hashlib.sha256("sg_test_key_001".encode()).hexdigest()
        # Ensure no allowlist in Redis
        try:
            redis_delete(f"ip_allowlist:{kh}")
        except Exception:
            pass
        result = _check_ip_allowlist(kh, "203.0.113.42")
        assert result is True

    def test_malformed_cidr_rejected(self):
        """Setting a malformed CIDR returns 400."""
        r = client.post("/v1/keys/test/allowlist", json={"cidrs": ["not-a-cidr"]},
                        headers=AUTH)
        assert r.status_code == 400
        assert "Invalid CIDR" in r.json()["detail"]
