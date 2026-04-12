"""Tests for embedding-based consensus detection and memory_location URI analysis."""
import pytest
import math


def _e(id="m1", content="Standard data.", type="semantic", age=1, trust=0.9,
       conflict=0.05, downstream=3, prompt_embedding=None, memory_location=None):
    d = {"id": id, "content": content, "type": type, "timestamp_age_days": age,
         "source_trust": trust, "source_conflict": conflict, "downstream_count": downstream}
    if prompt_embedding is not None:
        d["prompt_embedding"] = prompt_embedding
    if memory_location is not None:
        d["memory_location"] = memory_location
    return d


def _client():
    from fastapi.testclient import TestClient
    from api.main import app
    return TestClient(app)


AUTH = {"Authorization": "Bearer sg_demo_playground"}


def _make_embedding(seed, dim=8):
    """Generate a simple deterministic embedding vector."""
    import hashlib
    h = hashlib.sha256(str(seed).encode()).digest()
    vec = [float(b) / 255.0 for b in h[:dim]]
    norm = math.sqrt(sum(x * x for x in vec))
    return [x / norm for x in vec]  # unit normalized


class TestEmbeddingConsensus:
    def test_embedding_consensus_detection(self):
        """Entries with similar embeddings detected via cosine similarity."""
        # Same embedding = identical content semantically
        emb = _make_embedding("same_content")
        entries = [
            _e(id="m1", content="Revenue grew by twelve percent.", trust=0.90,
               conflict=0.02, downstream=8, prompt_embedding=emb),
            _e(id="m2", content="Top line increased 12 pct.", trust=0.90,
               conflict=0.02, downstream=8, prompt_embedding=emb),
            _e(id="m3", content="Sales up twelve percent year over year.", trust=0.90,
               conflict=0.02, downstream=18, prompt_embedding=emb),
        ]
        from api.main import _check_consensus_collapse
        result = _check_consensus_collapse(entries)
        assert result["consensus_detection_method"] == "embedding"
        # Same embedding → collapse detected
        assert result["consensus_collapse"] in ("SUSPICIOUS", "MANIPULATED")

    def test_embedding_fallback_to_jaccard(self):
        """Entries without embeddings fall back to Jaccard."""
        entries = [
            _e(id="m1", content="Settlement netting approved.", trust=0.90, conflict=0.02, downstream=8),
            _e(id="m2", content="Settlement netting confirmed.", trust=0.90, conflict=0.02, downstream=8),
            _e(id="m3", content="Settlement approved and confirmed.", trust=0.90, conflict=0.02, downstream=18),
        ]
        from api.main import _check_consensus_collapse
        result = _check_consensus_collapse(entries)
        assert result["consensus_detection_method"] == "jaccard"

    def test_embedding_mixed_falls_back(self):
        """If only some entries have embeddings, fall back to Jaccard."""
        emb = _make_embedding("partial")
        entries = [
            _e(id="m1", content="Data point A.", prompt_embedding=emb),
            _e(id="m2", content="Data point B."),  # no embedding
            _e(id="m3", content="Data point C.", prompt_embedding=emb),
        ]
        from api.main import _check_consensus_collapse
        result = _check_consensus_collapse(entries)
        assert result["consensus_detection_method"] == "jaccard"


class TestMemoryLocationAnalysis:
    def test_memory_location_analysis_populated(self):
        """memory_location_analysis populated when locations present."""
        c = _client()
        entries = [
            _e(id="m1", content="Data from Redis.", memory_location="redis://agent-001/session-42"),
            _e(id="m2", content="Data from vector DB.", memory_location="vector_db://collection-fintech"),
        ]
        resp = c.post("/v1/preflight", json={
            "memory_state": entries, "domain": "general", "action_type": "informational",
        }, headers=AUTH)
        data = resp.json()
        assert data["memory_locations_present"] is True
        assert "memory_location_analysis" in data
        analysis = data["memory_location_analysis"]
        assert "redis" in analysis["sources_detected"]
        assert analysis["source_diversity"] > 0

    def test_memory_location_cross_source_risk(self):
        """Same content from different schemes → cross_source_risk > 0."""
        c = _client()
        entries = [
            _e(id="m1", content="Settlement netting approved for processing transaction.",
               memory_location="redis://agent-001/cache"),
            _e(id="m2", content="Settlement netting approved for processing transaction.",
               memory_location="external://bloomberg-feed"),
            _e(id="m3", content="Settlement netting approved for processing transaction.",
               memory_location="vector_db://fintech-collection"),
        ]
        resp = c.post("/v1/preflight", json={
            "memory_state": entries, "domain": "fintech", "action_type": "informational",
        }, headers=AUTH)
        data = resp.json()
        analysis = data.get("memory_location_analysis", {})
        assert analysis.get("cross_source_risk", 0) > 0
        assert "external" in analysis.get("sources_detected", [])
        assert "bloomberg-feed" in analysis.get("external_sources", [])
