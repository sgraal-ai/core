"""Sgraal Emulator — drop-in replacement for Mem0/Zep/Letta APIs with built-in governance.

Usage:
    sgraal emulate --provider mem0 --port 8080 --api-key sg_live_...
    sgraal emulate --provider zep --port 8080   # returns 501
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import uuid
from typing import Optional

logger = logging.getLogger("sgraal.emulator")

SUPPORTED_PROVIDERS = {"mem0"}
PLANNED_PROVIDERS = {"zep", "letta"}

# In-memory store for emulated memories
_memories: dict[str, dict] = {}


def _sgraal_preflight(memory_state: list[dict], api_key: str, api_url: str) -> dict:
    """Call Sgraal preflight API."""
    import requests
    resp = requests.post(
        f"{api_url}/v1/preflight",
        json={"memory_state": memory_state},
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def _to_sgraal_entry(mem: dict) -> dict:
    """Convert emulator memory to Sgraal format."""
    meta = mem.get("metadata", {}) or {}
    return {
        "id": mem.get("id", str(uuid.uuid4())),
        "content": mem.get("memory", mem.get("text", "")),
        "type": meta.get("type", "episodic"),
        "timestamp_age_days": meta.get("age_days", 0),
        "source_trust": meta.get("confidence", 0.8),
        "source_conflict": meta.get("conflict", 0.1),
        "downstream_count": meta.get("downstream", 1),
    }


def create_mem0_app(api_key: str, api_url: str = "https://api.sgraal.com", dry_run: bool = False):
    """Create a FastAPI app emulating Mem0 API with Sgraal governance."""
    from fastapi import FastAPI, HTTPException

    app = FastAPI(title="Sgraal Mem0 Emulator")

    @app.post("/v1/memories")
    def add_memory(req: dict):
        # req is parsed from JSON body by FastAPI
        mem_id = str(uuid.uuid4())
        content = req.get("memory", req.get("text", ""))
        mem = {"id": mem_id, "memory": content, "user_id": req.get("user_id", "default"), "metadata": req.get("metadata", {})}

        # Run preflight
        entry = _to_sgraal_entry(mem)
        if dry_run:
            logger.info("[DRY RUN] Would preflight: %s", entry["id"])
            preflight = {"recommended_action": "USE_MEMORY", "omega_mem_final": 0}
        else:
            try:
                preflight = _sgraal_preflight([entry], api_key, api_url)
            except Exception as e:
                logger.warning("Preflight failed, storing anyway: %s", e)
                preflight = {"recommended_action": "USE_MEMORY", "omega_mem_final": 0}

        if preflight.get("recommended_action") == "BLOCK":
            raise HTTPException(status_code=409, detail=f"Memory blocked by Sgraal (omega={preflight.get('omega_mem_final')})")

        mem["sgraal_preflight"] = {"action": preflight.get("recommended_action"), "omega": preflight.get("omega_mem_final")}
        _memories[mem_id] = mem
        return {"id": mem_id, "memory": content, "sgraal": mem["sgraal_preflight"]}

    @app.post("/v1/memories/search")
    def search_memories(req: dict):
        query_lower = req.get("query", "").lower()
        user_id = req.get("user_id", "default")
        limit = req.get("limit", 10)
        matches = []
        for mem in _memories.values():
            if mem.get("user_id") == user_id and query_lower in mem.get("memory", "").lower():
                matches.append(mem)

        # Filter by Sgraal risk score
        entries = [_to_sgraal_entry(m) for m in matches[:limit]]
        if entries and not dry_run:
            try:
                preflight = _sgraal_preflight(entries, api_key, api_url)
                omega = preflight.get("omega_mem_final", 0)
                if omega > 80:
                    return {"results": [], "sgraal_filtered": True, "omega": omega}
            except Exception:
                pass

        return {"results": [{"id": m["id"], "memory": m["memory"], "metadata": m.get("metadata", {})} for m in matches[:limit]]}

    @app.delete("/v1/memories/{memory_id}")
    def delete_memory(memory_id: str):
        if memory_id not in _memories:
            raise HTTPException(status_code=404, detail="Memory not found")
        del _memories[memory_id]
        return {"id": memory_id, "deleted": True}

    return app


def main():
    parser = argparse.ArgumentParser(description="Sgraal Memory Emulator")
    parser.add_argument("--provider", required=True, choices=list(SUPPORTED_PROVIDERS | PLANNED_PROVIDERS))
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--api-url", default="https://api.sgraal.com")
    parser.add_argument("--dry-run", action="store_true", help="Show decisions without calling Sgraal")
    parser.add_argument("--log-level", default="info", choices=["debug", "info", "warning", "error"])
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level.upper()))

    if args.provider in PLANNED_PROVIDERS:
        print(json.dumps({"error": f"{args.provider.capitalize()} emulation coming soon. Currently supported: mem0"}))
        sys.exit(501 % 256)  # Non-zero exit

    if args.provider == "mem0":
        app = create_mem0_app(args.api_key, args.api_url, args.dry_run)
        import uvicorn
        print(f"Sgraal Mem0 Emulator running on http://0.0.0.0:{args.port}")
        uvicorn.run(app, host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
