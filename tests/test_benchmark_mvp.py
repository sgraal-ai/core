"""Tests for Multi-Model Benchmark MVP (#204)."""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app, _load_benchmark_corpus

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


class TestBenchmarkRun:
    def test_run_returns_200(self):
        r = client.post("/v1/benchmark/run", headers=AUTH, json={
            "rounds": [9], "sample_size": 5, "store_results": False,
        })
        assert r.status_code == 200
        j = r.json()
        assert "overall_f1" in j
        assert "total_cases" in j
        assert j["total_cases"] == 5

    def test_run_full_round9(self):
        r = client.post("/v1/benchmark/run", headers=AUTH, json={
            "rounds": [9], "store_results": False,
        })
        j = r.json()
        assert j["total_cases"] == 120
        # Scoring engine alone catches ~85%+; full preflight with detection layers catches 100%
        assert j["overall_f1"] >= 0.8

    def test_run_has_rounds_breakdown(self):
        r = client.post("/v1/benchmark/run", headers=AUTH, json={
            "rounds": [9], "sample_size": 10, "store_results": False,
        })
        j = r.json()
        assert "rounds" in j
        assert "9" in j["rounds"]
        assert "f1" in j["rounds"]["9"]
        assert "precision" in j["rounds"]["9"]
        assert "recall" in j["rounds"]["9"]

    def test_run_has_duration(self):
        r = client.post("/v1/benchmark/run", headers=AUTH, json={
            "rounds": [9], "sample_size": 3, "store_results": False,
        })
        assert r.json()["duration_ms"] >= 0

    def test_requires_auth(self):
        r = client.post("/v1/benchmark/run", json={"rounds": [9], "sample_size": 1})
        assert r.status_code in (401, 403)


class TestBenchmarkResults:
    def test_returns_200(self):
        r = client.get("/v1/benchmark/results", headers=AUTH)
        assert r.status_code == 200
        j = r.json()
        assert "latest" in j
        assert "history" in j
        assert "trend" in j

    def test_requires_auth(self):
        r = client.get("/v1/benchmark/results")
        assert r.status_code in (401, 403)


class TestBenchmarkStatus:
    def test_returns_200(self):
        r = client.get("/v1/benchmark/status", headers=AUTH)
        assert r.status_code == 200
        j = r.json()
        assert "corpus_loaded" in j
        assert "total_corpus_cases" in j
        assert "rounds_available" in j
        assert j["corpus_loaded"] is True
        assert j["total_corpus_cases"] > 0

    def test_rounds_include_9(self):
        r = client.get("/v1/benchmark/status", headers=AUTH)
        assert 9 in r.json()["rounds_available"]

    def test_requires_auth(self):
        r = client.get("/v1/benchmark/status")
        assert r.status_code in (401, 403)


class TestCorpusLoader:
    def test_loads_all_rounds(self):
        cases = _load_benchmark_corpus()
        assert len(cases) > 100  # At minimum Round 9 = 120

    def test_loads_specific_round(self):
        cases = _load_benchmark_corpus(rounds=[9])
        assert len(cases) == 120
        assert all(c["round"] == 9 for c in cases)

    def test_cases_have_required_fields(self):
        cases = _load_benchmark_corpus(rounds=[9])
        for c in cases[:5]:
            assert "memory_state" in c
            assert "expected_decision" in c
            assert "round" in c
