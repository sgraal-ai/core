from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Literal
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scoring_engine import compute, MemoryEntry

app = FastAPI(title="Sgraal API", version="0.1.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class MemoryEntryRequest(BaseModel):
    id: str
    content: str
    type: str
    timestamp_age_days: float
    source_trust: float = 0.9
    source_conflict: float = 0.1
    downstream_count: int = 1

class PreflightRequest(BaseModel):
    memory_state: list[MemoryEntryRequest]
    action_type: Literal["informational","reversible","irreversible","destructive"] = "reversible"
    domain: Literal["general","customer_support","coding","legal","fintech","medical"] = "general"

@app.get("/")
def root():
    return {"name": "Sgraal", "version": "0.1.0"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/v1/preflight")
def preflight(req: PreflightRequest):
    if not req.memory_state:
        raise HTTPException(status_code=400, detail="memory_state cannot be empty")
    entries = [MemoryEntry(id=e.id, content=e.content, type=e.type,
        timestamp_age_days=e.timestamp_age_days, source_trust=e.source_trust,
        source_conflict=e.source_conflict, downstream_count=e.downstream_count)
        for e in req.memory_state]
    result = compute(entries, req.action_type, req.domain)
    return {"omega_mem_final": result.omega_mem_final,
            "recommended_action": result.recommended_action,
            "assurance_score": result.assurance_score,
            "explainability_note": result.explainability_note,
            "component_breakdown": result.component_breakdown}
