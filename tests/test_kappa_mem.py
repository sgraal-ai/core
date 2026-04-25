"""Tests for κ_MEM computation script."""
import os
import pytest
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"

_numpy_available = True
try:
    import numpy
except ImportError:
    _numpy_available = False


class TestKappaMem:
    @pytest.mark.skipif(not _numpy_available, reason="numpy not installed")
    def test_script_imports(self):
        import scripts.compute_kappa_mem as script
        assert hasattr(script, "main") or hasattr(script, "compute_kappa_mem")

    def test_kappa_mem_exists_in_codebase(self):
        """The κ_MEM script should exist and be executable."""
        from pathlib import Path
        script_path = Path("scripts/compute_kappa_mem.py")
        assert script_path.exists()
