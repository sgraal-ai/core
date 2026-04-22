"""Federation vaccination endpoints."""
import hashlib
import time as _time

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.main import verify_api_key, _federation_registry, _evict_if_full

router = APIRouter(tags=["federation"])


class FederationContributeRequest(BaseModel):
    vaccine_signature: str
    attack_type: str = "unknown"
    domain: str = "general"


class FederationCheckRequest(BaseModel):
    memory_state: list = []


@router.post("/v1/federation/contribute")
def federation_contribute(req: FederationContributeRequest, key_record: dict = Depends(verify_api_key)):
    """Contribute anonymized vaccine to shared federation."""
    _sig = hashlib.sha256(req.vaccine_signature.encode()).hexdigest()[:16]
    entry = {"signature": _sig, "attack_type": req.attack_type,
             "domain": req.domain, "contributed_by": "anonymous", "contributed_at": _time.time()}
    _evict_if_full(_federation_registry, "_federation_registry")
    _federation_registry[_sig] = entry
    return {"contributed": True, "federation_size": len(_federation_registry)}


@router.get("/v1/federation/vaccines")
def federation_list(key_record: dict = Depends(verify_api_key)):
    """List all federated vaccine signatures."""
    return {"vaccines": list(_federation_registry.values())[-100:], "total": len(_federation_registry)}


@router.post("/v1/federation/check")
def federation_check(req: FederationCheckRequest, key_record: dict = Depends(verify_api_key)):
    """Check memory against federated vaccine registry."""
    matched = 0
    matched_types = set()
    for e in req.memory_state:
        content = e.get("content", "") if isinstance(e, dict) else str(e)
        _hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        vax = _federation_registry.get(_hash)
        if vax:
            matched += 1
            matched_types.add(vax["attack_type"])
    return {"federated_matches": matched, "matched_attack_types": list(matched_types),
            "federation_protected": matched > 0}
