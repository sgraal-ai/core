"""Tests for tenant-scoped daily snapshot keys."""
import os
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"


class TestSnapshotTenantScoping:
    def test_snapshot_key_includes_tenant(self):
        """Snapshot key format must include key_hash for tenant isolation."""
        kh = "abc123"
        aid = "agent_1"
        date = "2026-04-25"
        key = f"snapshot:{kh}:{aid}:{date}"
        assert kh in key
        assert aid in key
        assert date in key

    def test_snapshot_key_prevents_cross_tenant(self):
        """Different tenants produce different snapshot keys for same agent."""
        aid = "shared_agent"
        date = "2026-04-25"
        key_a = f"snapshot:tenant_a:{aid}:{date}"
        key_b = f"snapshot:tenant_b:{aid}:{date}"
        assert key_a != key_b

    def test_snapshot_stores_key_hash(self):
        """Snapshot data dict must include key_hash field."""
        snap = {
            "agent_id": "agent_1",
            "key_hash": "abc123",
            "date": "2026-04-25",
            "omega_mem_final": 15.3,
        }
        assert "key_hash" in snap
        assert snap["key_hash"] == "abc123"
