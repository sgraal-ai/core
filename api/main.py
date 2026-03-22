from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Literal, Optional
import sys, os
import secrets
import hashlib
from datetime import datetime, timezone
import stripe

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scoring_engine import compute, MemoryEntry

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase_client = None
if SUPABASE_URL and SUPABASE_KEY:
    from supabase import create_client
    supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)

supabase_service_client = None
if SUPABASE_URL and SUPABASE_SERVICE_KEY:
    from supabase import create_client as _create_client
    supabase_service_client = _create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

app = FastAPI(title="Sgraal API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# In-memory API key store: api_key -> stripe_customer_id
API_KEYS: dict[str, str] = {
    "sg_test_key_001": "cus_test_001",
}

bearer_scheme = HTTPBearer()


def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """Validate Bearer token and return the key record with tier/usage info."""
    api_key = credentials.credentials

    # Check in-memory store first (test keys skip rate limiting)
    if api_key in API_KEYS:
        return {"customer_id": API_KEYS[api_key], "tier": "free", "calls_this_month": 0, "key_hash": None}

    # Fall back to Supabase hash lookup
    if supabase_service_client:
        key_hash = _hash_key(api_key)
        result = (
            supabase_service_client.table("api_keys")
            .select("key_hash, customer_id, tier, calls_this_month")
            .eq("key_hash", key_hash)
            .execute()
        )
        if result.data:
            return result.data[0]

    raise HTTPException(status_code=401, detail="Invalid API key")

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
    memory_state: list[MemoryEntryRequest]
    action_type: Literal["informational","reversible","irreversible","destructive"] = "reversible"
    domain: Literal["general","customer_support","coding","legal","fintech","medical"] = "general"

class SignupRequest(BaseModel):
    email: str


TIER_LIMITS = {
    "free": 10_000,
    "starter": 100_000,
    "growth": 1_000_000,
}


def _generate_api_key() -> str:
    return "sg_live_" + secrets.token_urlsafe(32)


def _hash_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()


@app.get("/")
def root():
    return {"name": "Sgraal", "version": "0.1.0"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/v1/signup")
def signup(req: SignupRequest):
    if not stripe.api_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    if not supabase_service_client:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    # 1. Create Stripe customer
    customer = stripe.Customer.create(email=req.email)

    # 2. Create free tier subscription
    stripe.Subscription.create(
        customer=customer.id,
        items=[{"price": "price_1TDnSaHIIn2LzB5quygTrclw"}],
    )

    # 3. Generate API key
    api_key = _generate_api_key()
    key_hash = _hash_key(api_key)

    # 4. Store hashed key in Supabase (service role bypasses RLS)
    supabase_service_client.table("api_keys").insert({
        "key_hash": key_hash,
        "customer_id": customer.id,
        "email": req.email,
        "tier": "free",
    }).execute()

    # 5. Return plaintext key (only time it's shown)
    return {
        "api_key": api_key,
        "customer_id": customer.id,
        "tier": "free",
    }


@app.post("/v1/preflight")
def preflight(req: PreflightRequest, key_record: dict = Depends(verify_api_key)):
    if not req.memory_state:
        raise HTTPException(status_code=400, detail="memory_state cannot be empty")

    # Rate limit check
    tier = key_record.get("tier", "free")
    calls = key_record.get("calls_this_month", 0)
    limit = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
    if calls >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Monthly limit of {limit:,} calls exceeded for {tier} tier. "
                   f"Upgrade your plan or wait until the next billing cycle.",
        )

    entries = [MemoryEntry(
        id=e.id, content=e.content, type=e.type,
        timestamp_age_days=e.timestamp_age_days,
        source_trust=e.source_trust,
        source_conflict=e.source_conflict,
        downstream_count=e.downstream_count)
        for e in req.memory_state]

    result = compute(entries, req.action_type, req.domain)

    # Increment calls_this_month and update last_used_at
    key_hash = key_record.get("key_hash")
    if supabase_service_client and key_hash:
        try:
            supabase_service_client.table("api_keys").update({
                "calls_this_month": calls + 1,
                "last_used_at": datetime.now(timezone.utc).isoformat(),
            }).eq("key_hash", key_hash).execute()
        except Exception:
            pass

    if stripe.api_key:
        try:
            stripe.billing.MeterEvent.create(
                event_name="omega_mem_preflight",
                payload={
                    "value": "1",
                    "stripe_customer_id": key_record["customer_id"],
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
