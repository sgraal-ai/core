"""Tests for sgraal doctor CLI command."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "sdk", "cli"))

from sgraal_cli.doctor import _check_python, _check_api_key, _check_package


class TestDoctorChecks:
    def test_python_version_check(self):
        ok, msg, hint = _check_python()
        assert isinstance(ok, bool)
        assert "Python" in msg

    def test_api_key_missing(self):
        old = os.environ.pop("SGRAAL_API_KEY", None)
        try:
            ok, msg, hint = _check_api_key()
            assert ok is False
            assert "not set" in msg
        finally:
            if old:
                os.environ["SGRAAL_API_KEY"] = old

    def test_api_key_present(self):
        os.environ["SGRAAL_API_KEY"] = "sg_test_doctor_check"
        try:
            ok, msg, hint = _check_api_key()
            assert ok is True
            assert "set" in msg
        finally:
            del os.environ["SGRAAL_API_KEY"]
