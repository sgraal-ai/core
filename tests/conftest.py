"""Shared test configuration — sets environment for all tests.

These env vars MUST be set before api.main is imported, so this file runs
first (pytest auto-loads conftest.py before any test module).
"""
import os

# Skip DNS resolution in webhook URL validation (avoids flaky tests)
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"

# Enable the in-process test API keys (sg_test_key_001, sg_test_key_002).
# Production deployments MUST NOT set this — it would allow anyone who
# knows the test keys to authenticate against the API.
os.environ["SGRAAL_TEST_MODE"] = "1"
