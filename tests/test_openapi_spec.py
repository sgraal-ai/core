import os, sys
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_openapi_spec_accessible():
    r = client.get("/docs/openapi.json")
    assert r.status_code == 200
    d = r.json()
    assert "openapi" in d
    assert "paths" in d
