"""Guard endpoints — OpenAI function_call and Claude tool_use preflight validation.

Extracted from api/main.py as the first step of the router split refactor.
Behavior-preserving: the endpoint handlers are byte-identical to the originals.

Import order: api/main.py must define `verify_api_key`, `_check_rate_limit`,
`API_KEYS`, and `app` BEFORE it imports this module. The router is wired up
via `app.include_router(guard.router)` at the end of main.py.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

# These imports work because main.py only imports this file AFTER the
# required names are already defined in the api.main namespace.
from api.main import verify_api_key, _check_rate_limit, API_KEYS, app


router = APIRouter()


class OpenAIFunctionGuardRequest(BaseModel):
    name: str
    arguments: dict = {}
    memory_state: list[dict]
    agent_id: str = ""
    domain: str = "general"


class ClaudeToolGuardRequest(BaseModel):
    type: str = "tool_use"
    name: str = ""
    input: dict = {}
    memory_state: list[dict]
    agent_id: str = ""
    domain: str = "general"


@router.post("/v1/guard/openai-function")
def guard_openai_function(req: OpenAIFunctionGuardRequest, key_record: dict = Depends(verify_api_key)):
    """Guard an OpenAI function_call with Sgraal preflight validation."""
    _check_rate_limit(key_record)
    # Determine action_type from function name heuristics
    _destructive = {"delete", "remove", "drop", "kill", "terminate", "destroy"}
    _irreversible = {"transfer", "send", "execute", "deploy", "submit", "approve", "sign"}
    name_lower = req.name.lower()
    if any(w in name_lower for w in _destructive):
        action_type = "destructive"
    elif any(w in name_lower for w in _irreversible):
        action_type = "irreversible"
    else:
        action_type = "reversible"

    from fastapi.testclient import TestClient as _GClient
    _gc = _GClient(app)
    _gk = None
    for _ak in API_KEYS:
        if API_KEYS[_ak] == key_record.get("customer_id"):
            _gk = _ak
            break
    if not _gk:
        _gk = "sg_test_key_001"

    _pf = _gc.post("/v1/preflight", headers={"Authorization": f"Bearer {_gk}"}, json={
        "memory_state": req.memory_state[:20],
        "action_type": action_type,
        "domain": req.domain,
        "agent_id": req.agent_id,
        "dry_run": True,
    })
    if _pf.status_code != 200:
        return {"safe_to_call": False, "block_explanation": f"Preflight error: {_pf.status_code}"}

    _r = _pf.json()
    _safe = _r.get("recommended_action") == "USE_MEMORY"
    return {
        "safe_to_call": _safe,
        "recommended_action": _r.get("recommended_action"),
        "omega_mem_final": _r.get("omega_mem_final"),
        "block_explanation": _r.get("block_explanation"),
        "function_name": req.name,
        "action_type_inferred": action_type,
    }


@router.post("/v1/guard/claude-tool")
def guard_claude_tool(req: ClaudeToolGuardRequest, key_record: dict = Depends(verify_api_key)):
    """Guard a Claude tool_use block with Sgraal preflight validation."""
    _check_rate_limit(key_record)
    _destructive = {"delete", "remove", "drop", "kill", "terminate", "destroy"}
    _irreversible = {"transfer", "send", "execute", "deploy", "submit", "approve", "sign"}
    name_lower = req.name.lower()
    if any(w in name_lower for w in _destructive):
        action_type = "destructive"
    elif any(w in name_lower for w in _irreversible):
        action_type = "irreversible"
    else:
        action_type = "reversible"

    from fastapi.testclient import TestClient as _GClient
    _gc = _GClient(app)
    _gk = None
    for _ak in API_KEYS:
        if API_KEYS[_ak] == key_record.get("customer_id"):
            _gk = _ak
            break
    if not _gk:
        _gk = "sg_test_key_001"

    _pf = _gc.post("/v1/preflight", headers={"Authorization": f"Bearer {_gk}"}, json={
        "memory_state": req.memory_state[:20],
        "action_type": action_type,
        "domain": req.domain,
        "agent_id": req.agent_id,
        "dry_run": True,
    })
    if _pf.status_code != 200:
        return {"safe_to_call": False, "block_explanation": f"Preflight error: {_pf.status_code}"}

    _r = _pf.json()
    _safe = _r.get("recommended_action") == "USE_MEMORY"
    return {
        "safe_to_call": _safe,
        "recommended_action": _r.get("recommended_action"),
        "omega_mem_final": _r.get("omega_mem_final"),
        "block_explanation": _r.get("block_explanation"),
        "tool_name": req.name,
        "action_type_inferred": action_type,
    }
