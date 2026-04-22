"""Vaccine and compromised agent endpoints."""
from fastapi import APIRouter, Depends, Query

from api.main import verify_api_key, _decrypt_vaccine, UPSTASH_REDIS_URL, UPSTASH_REDIS_TOKEN
from api.redis_state import redis_get, redis_set, redis_delete, _get_session as _get_redis_session

router = APIRouter(tags=["vaccines"])


@router.get("/v1/vaccines")
def list_vaccines(domain: str = Query("general"), key_record: dict = Depends(verify_api_key)):
    """List stored vaccine signatures for a domain."""
    _vax_idx_key = f"vaccine_index:{domain}"
    _vax_ids = redis_get(_vax_idx_key, [])
    vaccines = []
    if isinstance(_vax_ids, list):
        for _vid in _vax_ids[:50]:
            _vax_raw = redis_get(f"vaccine:{_vid}")
            if _vax_raw:
                _vax = _decrypt_vaccine(_vax_raw)
                if _vax and isinstance(_vax, dict):
                    vaccines.append(_vax)
    return {"domain": domain, "count": len(vaccines), "vaccines": vaccines}


@router.delete("/v1/vaccines/{signature_id}")
def delete_vaccine(signature_id: str, domain: str = Query("general"), key_record: dict = Depends(verify_api_key)):
    """Remove a vaccine signature."""
    redis_delete(f"vaccine:{signature_id}")
    # Also remove from vaccine index so list_vaccines stays consistent
    _vax_idx_key = f"vaccine_index:{domain}"
    _vax_ids = redis_get(_vax_idx_key, [])
    if isinstance(_vax_ids, list) and signature_id in _vax_ids:
        _vax_ids.remove(signature_id)
        redis_set(_vax_idx_key, _vax_ids, ttl=604800)
    return {"deleted": signature_id}


@router.get("/v1/compromised-agents")
def list_compromised_agents(key_record: dict = Depends(verify_api_key)):
    """List currently flagged compromised agent_ids."""
    agents = []
    if UPSTASH_REDIS_URL:
        try:
            r = _get_redis_session().get(f"{UPSTASH_REDIS_URL}/LRANGE/compromised_agents/0/499",
                headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"}, timeout=2)
            if r.ok:
                result = r.json().get("result", [])
                if isinstance(result, list):
                    agents = list(set(result))  # deduplicate
        except Exception:
            pass
    if not agents:
        # Fallback to old format (redis_get for backward compat)
        agents = redis_get("compromised_agents", [])
        if not isinstance(agents, list):
            agents = []
    return {"count": len(agents), "agents": agents}


@router.delete("/v1/compromised-agents/{agent_id}")
def remove_compromised_agent(agent_id: str, key_record: dict = Depends(verify_api_key)):
    """Remove an agent from the compromised set."""
    agents = redis_get("compromised_agents", [])
    if isinstance(agents, list) and agent_id in agents:
        agents.remove(agent_id)
        redis_set("compromised_agents", agents, ttl=604800)
    return {"removed": agent_id}
