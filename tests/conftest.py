"""Shared test configuration — sets environment for all tests."""
import os

# Skip DNS resolution in webhook URL validation (avoids flaky tests)
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
