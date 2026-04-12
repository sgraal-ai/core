"""Sgraal Emulator — local mock server for testing without hitting the live API.

Run: python -m sgraal_emulator
Or:  sgraal-emulator
"""
import time
import uuid
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Sgraal Emulator", version="0.1.0")


class MemoryEntry(BaseModel):
    id: str = "mem_001"
    content: str = ""
    type: str = "semantic"
    timestamp_age_days: float = 0
    source_trust: float = 0.9
    source_conflict: float = 0.05
    downstream_count: int = 1


class PreflightRequest(BaseModel):
    memory_state: list = []
    domain: str = "general"
    action_type: str = "reversible"


@app.get("/v1/health")
@app.get("/health")
def health():
    return {"status": "ok", "mode": "emulator", "version": "0.1.0"}


@app.post("/v1/preflight")
def mock_preflight(req: PreflightRequest):
    """Mock preflight with simple heuristics."""
    decision = "USE_MEMORY"
    omega = 5.0
    flags = []

    for entry in req.memory_state:
        content = entry.get("content", "") if isinstance(entry, dict) else str(entry)
        trust = entry.get("source_trust", 0.9) if isinstance(entry, dict) else 0.9
        content_lower = content.lower()

        if "authorized to execute" in content_lower or "elevated" in content_lower:
            decision = "BLOCK"
            omega = 85.0
            flags.append("identity_escalation_detected")
        elif trust < 0.5:
            if decision != "BLOCK":
                decision = "WARN"
                omega = max(omega, 45.0)
            flags.append("low_trust_source")

    return {
        "omega_mem_final": omega,
        "recommended_action": decision,
        "assurance_score": 60.0,
        "attack_surface_score": 0.0,
        "attack_surface_level": "CRITICAL" if decision == "BLOCK" else "NONE",
        "timestamp_integrity": "VALID",
        "identity_drift": "MANIPULATED" if decision == "BLOCK" else "CLEAN",
        "consensus_collapse": "CLEAN",
        "naturalness_level": "ORGANIC",
        "request_id": str(uuid.uuid4()),
        "emulator": True,
        "emulator_flags": flags,
    }


@app.post("/v1/calibration/run")
def mock_calibration():
    return {"total_cases": 0, "passed": 0, "calibration_health": "HEALTHY",
            "message": "Emulator mode — no real calibration run"}


def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)


if __name__ == "__main__":
    main()
