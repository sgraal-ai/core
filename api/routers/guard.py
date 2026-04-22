"""Guard endpoints — OpenAI function_call and Claude tool_use preflight validation.

Extracted from api/main.py as the first step of the router split refactor.

Import order: api/main.py must define `verify_api_key`, `_check_rate_limit`,
and `app` BEFORE it imports this module. The router is wired up
via `app.include_router(guard.router)` at the end of main.py.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.main import (verify_api_key, _check_rate_limit,
                      _preflight_internal, PreflightRequest, MemoryEntryRequest)


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


def _infer_action_type(name: str) -> str:
    _destructive = {"delete", "remove", "drop", "kill", "terminate", "destroy"}
    _irreversible = {"transfer", "send", "execute", "deploy", "submit", "approve", "sign"}
    name_lower = name.lower()
    if any(w in name_lower for w in _destructive):
        return "destructive"
    elif any(w in name_lower for w in _irreversible):
        return "irreversible"
    return "reversible"


def _run_guard(name: str, memory_state: list, domain: str, agent_id: str,
               action_type: str, key_record: dict) -> dict:
    """Shared guard logic — calls _preflight_internal directly."""
    try:
        pf_req = PreflightRequest(
            memory_state=[MemoryEntryRequest(**e) if isinstance(e, dict) else e for e in memory_state[:20]],
            action_type=action_type,
            domain=domain,
            agent_id=agent_id,
            dry_run=True,
        )
        _r = _preflight_internal(pf_req, key_record)
        if not isinstance(_r, dict):
            return {"safe_to_call": False, "block_explanation": "Preflight returned non-dict"}
    except Exception as _e:
        return {"safe_to_call": False, "block_explanation": f"Preflight error: {str(_e)[:200]}"}

    _safe = _r.get("recommended_action") == "USE_MEMORY"
    return {
        "safe_to_call": _safe,
        "recommended_action": _r.get("recommended_action"),
        "omega_mem_final": _r.get("omega_mem_final"),
        "block_explanation": _r.get("block_explanation"),
        "action_type_inferred": action_type,
    }


@router.post("/v1/guard/openai-function")
def guard_openai_function(req: OpenAIFunctionGuardRequest, key_record: dict = Depends(verify_api_key)):
    """Guard an OpenAI function_call with Sgraal preflight validation."""
    _check_rate_limit(key_record)
    action_type = _infer_action_type(req.name)
    result = _run_guard(req.name, req.memory_state, req.domain, req.agent_id, action_type, key_record)
    result["function_name"] = req.name
    return result


@router.post("/v1/guard/claude-tool")
def guard_claude_tool(req: ClaudeToolGuardRequest, key_record: dict = Depends(verify_api_key)):
    """Guard a Claude tool_use block with Sgraal preflight validation."""
    _check_rate_limit(key_record)
    action_type = _infer_action_type(req.name)
    result = _run_guard(req.name, req.memory_state, req.domain, req.agent_id, action_type, key_record)
    result["tool_name"] = req.name
    return result
