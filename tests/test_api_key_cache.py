"""Tests for Redis-cached API key validation."""
import hashlib
from unittest.mock import patch, MagicMock
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials


def _hash_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()


# Shared fixtures
FAKE_KEY = "sg_live_test_cached_key_abc123"
FAKE_HASH = _hash_key(FAKE_KEY)
CACHE_KEY = f"api_key_valid:{FAKE_HASH[:16]}"
SUPABASE_ROW = {"key_hash": FAKE_HASH, "customer_id": "cus_123", "tier": "pro", "calls_this_month": 42}
CACHED_VALUE = {"valid": True, "user_id": "cus_123", "plan": "pro"}


def _make_credentials(key: str = FAKE_KEY):
    creds = MagicMock(spec=HTTPAuthorizationCredentials)
    creds.credentials = key
    return creds


def _make_request(path: str = "/v1/preflight"):
    """Mock Request object for verify_api_key (needs request.url.path for demo scope check)."""
    req = MagicMock()
    req.url.path = path
    return req


@patch("api.main.redis_set")
@patch("api.main.redis_get", return_value=None)
@patch("api.main.supabase_service_client")
def test_cache_miss_then_supabase_hit_caches(mock_supa, mock_rget, mock_rset):
    """1. Valid key → Redis miss → Supabase hit → cached in Redis."""
    from api.main import verify_api_key
    mock_result = MagicMock()
    mock_result.data = [SUPABASE_ROW]
    mock_supa.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_result

    result = verify_api_key(_make_request(), _make_credentials())

    assert result["customer_id"] == "cus_123"
    mock_rget.assert_called_once_with(CACHE_KEY)
    mock_rset.assert_called_once_with(CACHE_KEY, CACHED_VALUE, ttl=300)


@patch("api.main.redis_set")
@patch("api.main.redis_get", return_value=CACHED_VALUE)
@patch("api.main.supabase_service_client")
def test_cache_hit_skips_supabase(mock_supa, mock_rget, mock_rset):
    """2. Valid key → Redis hit → Supabase NOT called."""
    from api.main import verify_api_key

    result = verify_api_key(_make_request(), _make_credentials())

    assert result["customer_id"] == "cus_123"
    assert result["tier"] == "pro"
    mock_rget.assert_called_once_with(CACHE_KEY)
    mock_supa.table.assert_not_called()
    mock_rset.assert_not_called()


@patch("api.main.redis_delete")
@patch("api.main._check_rate_limit")
def test_revoke_deletes_cache(mock_rate, mock_rdel):
    """3. Revoked key → cache deleted."""
    from api.main import app, verify_api_key
    from fastapi.testclient import TestClient

    fake_record = {"customer_id": "cus_123", "tier": "pro", "calls_this_month": 0, "key_hash": FAKE_HASH}
    app.dependency_overrides[verify_api_key] = lambda: fake_record
    try:
        client = TestClient(app)
        key_id = FAKE_HASH[:16]
        resp = client.delete(f"/v1/api-keys/{key_id}", headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 200
        mock_rdel.assert_called_once_with(f"api_key_valid:{key_id}")
    finally:
        app.dependency_overrides.pop(verify_api_key, None)


@patch("api.main.redis_set")
@patch("api.main.redis_get", side_effect=Exception("Redis down"))
@patch("api.main.supabase_service_client")
def test_redis_down_falls_through_to_supabase(mock_supa, mock_rget, mock_rset):
    """4. Redis unavailable → falls through to Supabase → works normally."""
    from api.main import verify_api_key
    mock_result = MagicMock()
    mock_result.data = [SUPABASE_ROW]
    mock_supa.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_result

    result = verify_api_key(_make_request(), _make_credentials())

    assert result["customer_id"] == "cus_123"
    # redis_set may still be attempted (Supabase succeeded), that's fine


@patch("api.main.redis_set")
@patch("api.main.redis_get", return_value=None)
@patch("api.main.supabase_service_client")
def test_invalid_key_not_cached(mock_supa, mock_rget, mock_rset):
    """5. Invalid key → not cached (don't cache negative results)."""
    from api.main import verify_api_key
    mock_result = MagicMock()
    mock_result.data = []  # no match
    mock_supa.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc_info:
        verify_api_key(_make_request(), _make_credentials("sg_live_bad_key"))
    assert exc_info.value.status_code == 401
    mock_rset.assert_not_called()


@patch("api.main.redis_set")
@patch("api.main.redis_get", return_value=None)
@patch("api.main.supabase_service_client")
def test_cache_ttl_is_300(mock_supa, mock_rget, mock_rset):
    """6. Cache TTL respected — entry set with TTL=300."""
    from api.main import verify_api_key
    mock_result = MagicMock()
    mock_result.data = [SUPABASE_ROW]
    mock_supa.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_result

    verify_api_key(_make_request(), _make_credentials())

    args, kwargs = mock_rset.call_args
    assert args[0] == CACHE_KEY
    assert kwargs.get("ttl") == 300 or args[2] == 300
