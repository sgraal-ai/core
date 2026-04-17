import os, sys, random
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}

# Generate 20 deterministic random memory states
rng = random.Random(42)
RANDOM_INPUTS = []
for i in range(20):
    n_entries = rng.randint(1, 5)
    entries = []
    for j in range(n_entries):
        entries.append({
            "id": f"rnd_{i}_{j}",
            "content": f"random content {rng.random():.4f}",
            "type": rng.choice(["tool_state", "episodic", "semantic", "identity", "preference", "policy", "shared_workflow"]),
            "timestamp_age_days": rng.uniform(0, 200),
            "source_trust": rng.uniform(0.05, 1.0),
            "source_conflict": rng.uniform(0.0, 0.95),
            "downstream_count": rng.randint(1, 20),
        })
    domain = rng.choice(["general", "fintech", "medical", "legal", "coding", "customer_support"])
    action_type = rng.choice(["informational", "reversible", "irreversible", "destructive"])
    RANDOM_INPUTS.append((entries, domain, action_type))


class TestPropertyBased:
    @pytest.mark.parametrize("idx", range(20))
    def test_omega_in_range(self, idx):
        entries, domain, action_type = RANDOM_INPUTS[idx]
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": entries, "domain": domain, "action_type": action_type,
        })
        assert r.status_code == 200
        omega = r.json()["omega_mem_final"]
        assert 0.0 <= omega <= 100.0, f"omega={omega} out of [0,100]"

    @pytest.mark.parametrize("idx", range(20))
    def test_decision_is_valid(self, idx):
        entries, domain, action_type = RANDOM_INPUTS[idx]
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": entries, "domain": domain, "action_type": action_type,
        })
        assert r.json()["recommended_action"] in ("USE_MEMORY", "WARN", "ASK_USER", "BLOCK")

    @pytest.mark.parametrize("idx", range(5))
    def test_determinism_a2_axiom(self, idx):
        entries, domain, action_type = RANDOM_INPUTS[idx]
        payload = {"memory_state": entries, "domain": domain, "action_type": action_type}
        r1 = client.post("/v1/preflight", headers=AUTH, json=payload)
        r2 = client.post("/v1/preflight", headers=AUTH, json=payload)
        assert r1.json()["omega_mem_final"] == r2.json()["omega_mem_final"]
        assert r1.json()["recommended_action"] == r2.json()["recommended_action"]
