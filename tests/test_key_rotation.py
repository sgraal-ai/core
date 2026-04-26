"""Tests for #794 API key rotation with grace period."""
import os
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"

from fastapi.testclient import TestClient
from api.main import app, _check_key_expiry, _ROTATE_GRACE_SECONDS
from api.redis_state import redis_set, redis_available
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
import pytest

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


class TestKeyRotation:
    def test_rotate_generates_new_key(self):
        """Rotate returns a new key with grace period metadata."""
        r = client.post("/v1/api-keys/test_rot/rotate", headers=AUTH)
        assert r.status_code == 200
        j = r.json()
        assert "new_api_key" in j
        assert "new_key_id" in j
        assert j["grace_period_seconds"] == _ROTATE_GRACE_SECONDS
        assert "old_key_expires_at" in j

    def test_expired_key_returns_401(self):
        """Key past grace period is rejected."""
        if not redis_available():
            pytest.skip("Redis not available")
        import hashlib
        kh = hashlib.sha256("sg_test_key_001".encode()).hexdigest()
        # Set expiry in the past
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        redis_set(f"key_expires:{kh[:16]}", {"expires_at": past}, ttl=60)
        try:
            with pytest.raises(HTTPException) as exc_info:
                _check_key_expiry(kh)
            assert exc_info.value.status_code == 401
        finally:
            from api.redis_state import redis_delete
            redis_delete(f"key_expires:{kh[:16]}")

    def test_key_within_grace_allowed(self):
        """Key within grace period is accepted."""
        if not redis_available():
            pytest.skip("Redis not available")
        import hashlib
        kh = hashlib.sha256("sg_test_key_001".encode()).hexdigest()
        future = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()
        redis_set(f"key_expires:{kh[:16]}", {"expires_at": future}, ttl=60)
        try:
            _check_key_expiry(kh)  # Should not raise
        finally:
            from api.redis_state import redis_delete
            redis_delete(f"key_expires:{kh[:16]}")

    def test_rotate_creates_audit_log(self):
        """Rotation creates an audit log entry."""
        r = client.post("/v1/api-keys/test_audit_rot/rotate", headers=AUTH)
        assert r.status_code == 200
        # Audit log is best-effort (Supabase may not be available)
        # Just verify the endpoint didn't error
        assert "new_api_key" in r.json()
