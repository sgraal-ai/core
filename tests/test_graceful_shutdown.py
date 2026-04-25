"""Test graceful shutdown flushes state."""
import os
import sys

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.main import _flush_state_on_shutdown


class TestGracefulShutdown:
    def test_flush_completes_without_error(self):
        """_flush_state_on_shutdown runs without raising, even without Redis."""
        _flush_state_on_shutdown()  # Should not raise
