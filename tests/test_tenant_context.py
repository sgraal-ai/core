"""Unit tests for TenantContext — tenant isolation structural enforcement."""
import pytest
from fastapi import HTTPException
from api.tenant import TenantContext


def _ctx(key_hash="abc123", customer_id="cust_1", is_demo=False):
    return TenantContext(key_hash=key_hash, customer_id=customer_id, is_demo=is_demo)


class TestScopedKey:
    def test_single_part(self):
        assert _ctx().scoped_key("verdicts") == "abc123:verdicts"

    def test_multi_part(self):
        assert _ctx().scoped_key("agent", "a1") == "abc123:agent:a1"

    def test_empty_parts(self):
        assert _ctx().scoped_key() == "abc123"


class TestRedisKey:
    def test_basic(self):
        assert _ctx().redis_key("vaccine_index", "general") == "vaccine_index:abc123:general"

    def test_no_parts(self):
        assert _ctx().redis_key("prefix") == "prefix:abc123"


class TestFilterList:
    def test_filters_by_key_hash(self):
        items = [
            {"id": "1", "key_hash": "abc123"},
            {"id": "2", "key_hash": "other"},
            {"id": "3", "key_hash": "abc123"},
        ]
        result = _ctx().filter_list(items)
        assert len(result) == 2
        assert all(r["key_hash"] == "abc123" for r in result)

    def test_empty_list(self):
        assert _ctx().filter_list([]) == []

    def test_custom_key_field(self):
        items = [{"tenant": "abc123"}, {"tenant": "other"}]
        result = _ctx().filter_list(items, key_field="tenant")
        assert len(result) == 1

    def test_skips_non_dicts(self):
        items = [{"key_hash": "abc123"}, "not_a_dict", None, 42]
        result = _ctx().filter_list(items)
        assert len(result) == 1

    def test_missing_key_field_excluded(self):
        items = [{"id": "1"}, {"id": "2", "key_hash": "abc123"}]
        result = _ctx().filter_list(items)
        assert len(result) == 1


class TestOwns:
    def test_owns_matching(self):
        assert _ctx().owns({"key_hash": "abc123"}) is True

    def test_not_owns_different(self):
        assert _ctx().owns({"key_hash": "other"}) is False

    def test_not_owns_missing_field(self):
        assert _ctx().owns({"id": "1"}) is False

    def test_not_owns_none(self):
        assert _ctx().owns(None) is False

    def test_not_owns_non_dict(self):
        assert _ctx().owns("string") is False

    def test_custom_key_field(self):
        assert _ctx().owns({"tenant_id": "abc123"}, key_field="tenant_id") is True

    def test_empty_key_hash_returns_false(self):
        ctx = TenantContext(key_hash="", customer_id="c", is_demo=False)
        assert ctx.owns({"key_hash": ""}) is False


class TestAssertOwns:
    def test_passes_for_owner(self):
        _ctx().assert_owns({"key_hash": "abc123"})  # Should not raise

    def test_raises_403_for_other(self):
        with pytest.raises(HTTPException) as exc:
            _ctx().assert_owns({"key_hash": "other"})
        assert exc.value.status_code == 403

    def test_raises_404_for_none(self):
        with pytest.raises(HTTPException) as exc:
            _ctx().assert_owns(None)
        assert exc.value.status_code == 404

    def test_custom_detail(self):
        with pytest.raises(HTTPException) as exc:
            _ctx().assert_owns({"key_hash": "other"}, detail="Custom msg")
        assert "Custom msg" in exc.value.detail


class TestTag:
    def test_adds_key_hash(self):
        item = {"id": "1"}
        result = _ctx().tag(item)
        assert result["key_hash"] == "abc123"
        assert result is not item  # Returns new dict, does not mutate original

    def test_does_not_mutate_original(self):
        item = {"id": "1"}
        _ctx().tag(item)
        assert "key_hash" not in item  # Original unchanged

    def test_overwrites_existing(self):
        item = {"key_hash": "old"}
        result = _ctx().tag(item)
        assert result["key_hash"] == "abc123"
        assert item["key_hash"] == "old"  # Original unchanged


class TestSupabaseFilter:
    def test_appends_with_ampersand(self):
        url = "https://sb.co/rest/v1/table?id=eq.1"
        result = _ctx().supabase_filter(url)
        assert result == "https://sb.co/rest/v1/table?id=eq.1&api_key_hash=eq.abc123"

    def test_appends_with_question_mark(self):
        url = "https://sb.co/rest/v1/table"
        result = _ctx().supabase_filter(url)
        assert result == "https://sb.co/rest/v1/table?api_key_hash=eq.abc123"


class TestImmutability:
    def test_frozen(self):
        ctx = _ctx()
        with pytest.raises(AttributeError):
            ctx.key_hash = "new_value"
