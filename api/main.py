from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Literal, Optional
import sys, os
import stripe

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scoring_engine import compute, MemoryEntry

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

supabase_client = None
if SUPABASE_URL and SUPABASE_KEY:
    from supabase import create_client
    supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)

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
    agent_id: Optional[str] = "anonymous"
    task_id: Optional[str] = None
    stripe_customer_id: str
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

    entries = [MemoryEntry(
        id=e.id, content=e.content, type=e.type,
        timestamp_age_days=e.timestamp_age_days,
        source_trust=e.source_trust,
        source_conflict=e.source_conflict,
        downstream_count=e.downstream_count)
        for e in req.memory_state]

    result = compute(entries, req.action_type, req.domain)

    if stripe.api_key:
        try:
            stripe.billing.MeterEvent.create(
                event_name="omega_mem_preflight",
                payload={
                    "value": "1",
                    "stripe_customer_id": req.stripe_customer_id,
                },
            )
        except Exception:
            pass

    if supabase_client:
        try:
            supabase_client.table("memory_ledger").insert({
                "agent_id": req.agent_id,
                "task_id": req.task_id,
                "omega_mem_final": result.omega_mem_final,
                "recommended_action": result.recommended_action,
                "assurance_score": result.assurance_score,
                "domain": req.domain,
                "action_type": req.action_type,
                "explainability_note": result.explainability_note,
                "component_breakdown": result.component_breakdown,
            }).execute()
        except Exception as e:
            pass

    return {
        "omega_mem_final": result.omega_mem_final,
        "recommended_action": result.recommended_action,
        "assurance_score": result.assurance_score,
        "explainability_note": result.explainability_note,
        "component_breakdown": result.component_breakdown,
    }
