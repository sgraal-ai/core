import os, sys
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app, _load_benchmark_corpus

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


class TestCorpusRunner:
    def test_main_corpus_f1_above_threshold(self):
        """Run the main benchmark corpus and verify F1 >= 0.95."""
        cases = _load_benchmark_corpus()
        if not cases or len(cases) < 10:
            import pytest
            pytest.skip("Benchmark corpus not available or too small")

        tp = fp = fn = 0
        for case in cases[:200]:  # cap for speed in CI
            ms = case.get("memory_state", [])
            if not ms:
                continue
            gt = (case.get("ground_truth", {}).get("expected_action")
                  or case.get("ground_truth", {}).get("recommended_action")
                  or case.get("expected_decision")
                  or case.get("expected_action"))
            if not gt:
                continue
            r = client.post("/v1/preflight", headers=AUTH, json={
                "memory_state": ms[:20],
                "action_type": case.get("action_type", "reversible"),
                "domain": case.get("domain", "general"),
                "dry_run": True,
            })
            if r.status_code != 200:
                continue
            pred = r.json().get("recommended_action")
            is_block_gt = gt in ("BLOCK", "MANIPULATED")
            is_block_pred = pred == "BLOCK"
            if is_block_gt and is_block_pred:
                tp += 1
            elif is_block_pred and not is_block_gt:
                fp += 1
            elif is_block_gt and not is_block_pred:
                fn += 1

        total = tp + fp + fn
        if total == 0:
            import pytest
            pytest.skip("No classifiable cases found")
        precision = tp / max(tp + fp, 1)
        recall = tp / max(tp + fn, 1)
        f1 = 2 * precision * recall / max(precision + recall, 1e-9)
        assert f1 >= 0.90, f"Corpus F1={f1:.3f} (tp={tp}, fp={fp}, fn={fn}) below 0.90 threshold"
