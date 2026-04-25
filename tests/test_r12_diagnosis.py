"""Test that R12 mismatch diagnosis research document is valid."""
import os
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"
from pathlib import Path


class TestR12Diagnosis:
    def test_diagnosis_file_exists(self):
        p = Path("research/r12_mismatch_diagnosis_2026_04_25.md")
        assert p.exists()

    def test_diagnosis_has_summary(self):
        p = Path("research/r12_mismatch_diagnosis_2026_04_25.md")
        content = p.read_text()
        assert "Category A" in content
        assert "Category B" in content
        assert "Recommendation" in content
