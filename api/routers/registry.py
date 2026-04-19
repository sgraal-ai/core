"""Verified Memory Registry endpoints."""
import time as _time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from api.main import (verify_api_key, _safe_key_hash, _evict_if_full, _check_public_rate_limit,
                      _preflight_internal, _registry, PreflightRequest, MemoryEntryRequest)
from api.redis_state import redis_get, redis_set

router = APIRouter(tags=["registry"])


class RegistryRegisterRequest(BaseModel):
    agent_id: str
    memory_state: list
    domain: str = "general"
    action_type: str = "reversible"


@router.post("/v1/registry/register")
def register_memory(req: RegistryRegisterRequest, key_record: dict = Depends(verify_api_key)):
    """Register agent memory as verified — only USE_MEMORY passes."""
    pf_req = PreflightRequest(
        memory_state=[MemoryEntryRequest(**e) if isinstance(e, dict) else e for e in req.memory_state],
        domain=req.domain, action_type=req.action_type, agent_id=req.agent_id,
    )
    pf_result = _preflight_internal(pf_req, key_record)
    decision = pf_result.get("recommended_action", "BLOCK") if isinstance(pf_result, dict) else "BLOCK"
    if decision != "USE_MEMORY":
        raise HTTPException(status_code=422, detail=f"Memory not clean enough for registry: {decision}. Only USE_MEMORY qualifies.")
    _mem_hash = pf_result.get("input_hash", "") if isinstance(pf_result, dict) else ""
    reg_id = str(uuid.uuid4())
    now = _time.time()
    entry = {
        "registry_id": reg_id, "agent_id": req.agent_id, "memory_hash": _mem_hash,
        "governance_score": None,
        "governance_score_note": "Insufficient history for governance score",
        "registered_at": now, "valid_until": now + 86400, "status": "VERIFIED",
        "api_key_id": _safe_key_hash(key_record)[:16],
    }
    _evict_if_full(_registry, "_registry")
    _registry[req.agent_id] = entry
    redis_set(f"registry:{req.agent_id}", entry, ttl=86400)
    return entry


@router.get("/v1/registry/{agent_id}")
def get_registry_entry(agent_id: str, request: Request):
    """Public: check if an agent has verified memory (no auth). Rate limited: 60/min per IP."""
    _check_public_rate_limit(request, "registry_lookup")
    entry = _registry.get(agent_id) or redis_get(f"registry:{agent_id}")
    if not entry:
        raise HTTPException(status_code=404, detail="Agent not registered or registration expired")
    if entry.get("valid_until", 0) < _time.time():
        raise HTTPException(status_code=404, detail="Registration expired")
    return entry


@router.get("/v1/registry")
def list_registry(key_record: dict = Depends(verify_api_key)):
    """List all registered agents for this API key."""
    _kh = _safe_key_hash(key_record)[:16]
    entries = [v for v in _registry.values() if v.get("api_key_id") == _kh and v.get("valid_until", 0) > _time.time()]
    return {"agents": entries, "count": len(entries)}
