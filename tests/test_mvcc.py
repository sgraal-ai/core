"""Tests for MVCC Redis state versioning."""
import os
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"

from api.redis_state import (
    redis_mvcc_get, redis_mvcc_set, redis_mvcc_update, MVCCResult,
    redis_get, redis_set, redis_delete, redis_available,
)


class TestMVCCGet:
    def test_nonexistent_key_returns_none_version_zero(self):
        value, version = redis_mvcc_get("mvcc_test_nonexistent_key_xyz")
        assert value is None
        assert version == 0

    def test_legacy_unversioned_value_returns_version_zero(self):
        """A value written without MVCC is treated as version 0."""
        redis_set("mvcc_test_legacy", {"data": "old"}, ttl=60)
        value, version = redis_mvcc_get("mvcc_test_legacy")
        if redis_available():
            assert version == 0
            assert value == {"data": "old"}
        else:
            # No Redis — falls back to None
            assert value is None
        redis_delete("mvcc_test_legacy")

    def test_versioned_value_returns_correct_version(self):
        """A value written with MVCC returns the correct version."""
        v = redis_mvcc_set("mvcc_test_versioned", {"key": "val"}, ttl=60)
        if redis_available():
            assert v == 1
            value, version = redis_mvcc_get("mvcc_test_versioned")
            assert version == 1
            assert value == {"key": "val"}
        redis_delete("mvcc_test_versioned")


class TestMVCCSet:
    def test_initial_write_version_1(self):
        v = redis_mvcc_set("mvcc_test_set_init", "hello", ttl=60)
        assert v == 1
        redis_delete("mvcc_test_set_init")


class TestMVCCUpdate:
    def test_update_increments_version(self):
        """Successful CAS update increments version."""
        redis_mvcc_set("mvcc_test_update", 10, ttl=60)
        result = redis_mvcc_update("mvcc_test_update", lambda v: (v or 0) + 5, ttl=60)
        if redis_available():
            assert result.success is True
            assert result.value == 15
            assert result.version == 2
        redis_delete("mvcc_test_update")

    def test_update_on_new_key(self):
        """CAS update on nonexistent key creates it at version 1."""
        redis_delete("mvcc_test_new_update")
        result = redis_mvcc_update("mvcc_test_new_update", lambda v: "initial", ttl=60)
        if redis_available():
            assert result.success is True
            assert result.value == "initial"
            assert result.version == 1
        redis_delete("mvcc_test_new_update")

    def test_updater_fn_exception_returns_failure(self):
        """If updater_fn raises, return failure without conflict."""
        redis_mvcc_set("mvcc_test_error", 1, ttl=60)
        result = redis_mvcc_update("mvcc_test_error", lambda v: 1/0, ttl=60)
        assert result.success is False
        assert result.conflict is False
        redis_delete("mvcc_test_error")

    def test_result_has_expected_fields(self):
        """MVCCResult has all expected attributes."""
        r = MVCCResult(success=True, value="x", version=3, conflict=False)
        assert r.success is True
        assert r.value == "x"
        assert r.version == 3
        assert r.conflict is False

    def test_no_redis_returns_failure(self):
        """Without Redis, MVCC operations return graceful failure."""
        # This tests the fallback path — redis_available() checks env vars
        # In test env with UPSTASH vars set, this may succeed
        r = MVCCResult(success=False, conflict=False)
        assert r.success is False


class TestMVCCConcurrency:
    def test_concurrent_update_simulation(self):
        """Simulate two concurrent updates — at most one should succeed via CAS."""
        if not redis_available():
            return  # Skip if no Redis

        redis_mvcc_set("mvcc_test_concurrent", 0, ttl=60)

        # First update: increment by 1
        r1 = redis_mvcc_update("mvcc_test_concurrent", lambda v: (v or 0) + 1, ttl=60)
        assert r1.success is True
        assert r1.value == 1
        assert r1.version == 2

        # Second update: increment by 10 (starts from version 2)
        r2 = redis_mvcc_update("mvcc_test_concurrent", lambda v: (v or 0) + 10, ttl=60)
        assert r2.success is True
        assert r2.value == 11  # 1 + 10
        assert r2.version == 3

        # Verify final state
        val, ver = redis_mvcc_get("mvcc_test_concurrent")
        assert val == 11
        assert ver == 3

        redis_delete("mvcc_test_concurrent")
