"""Tests for the Supabase tenant isolation CI check extension."""
import os, tempfile
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"

from pathlib import Path
from scripts.check_tenant_isolation import _check_supabase_tenant, TENANT_SCOPED_TABLES


def _write_temp(code: str) -> Path:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False)
    f.write(code)
    f.close()
    return Path(f.name)


class TestSupabasePatternDetection:
    def test_detects_unscoped_table_access(self):
        code = 'supabase.table("audit_log").select("*").execute()'
        violations = _check_supabase_tenant(_write_temp(code))
        assert len(violations) == 1
        assert violations[0]["table"] == "audit_log"

    def test_passes_scoped_access(self):
        code = 'supabase.table("audit_log").select("*").eq("api_key_id", kh).execute()'
        violations = _check_supabase_tenant(_write_temp(code))
        assert len(violations) == 0

    def test_passes_exempt_marker(self):
        code = 'supabase.table("audit_log").select("id").limit(1).execute()  # CI_TENANT_SAFE: health check'
        violations = _check_supabase_tenant(_write_temp(code))
        assert len(violations) == 0

    def test_ignores_non_tenant_tables(self):
        code = 'supabase.table("some_other_table").select("*").execute()'
        violations = _check_supabase_tenant(_write_temp(code))
        assert len(violations) == 0

    def test_tenant_scoped_tables_list(self):
        assert "audit_log" in TENANT_SCOPED_TABLES
        assert "api_keys" in TENANT_SCOPED_TABLES
        assert "aging_rules" in TENANT_SCOPED_TABLES

    def test_detects_nearby_filter(self):
        """Filter within 3 lines should pass."""
        code = '''result = supabase.table("audit_log")
    .select("*")
    .eq("api_key_id", kh)
    .execute()'''
        violations = _check_supabase_tenant(_write_temp(code))
        assert len(violations) == 0
