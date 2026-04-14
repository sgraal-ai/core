"""memorae-sgraal: Drop-in Sgraal-guarded wrapper for Memorae memory agents.

Memorae is a WhatsApp/Telegram-based memory agent. This bridge intercepts
search() and add() calls with Sgraal preflight validation.

Usage:
    from memorae_sgraal import SafeMemoraeMemory

    memory = SafeMemoraeMemory(
        api_key="sg_live_...",
        memorae_token="your_memorae_token",
        on_block="raise",
    )

    # Guarded search — runs preflight before returning results
    results = memory.search("what did the user say about pricing?")

    # Guarded add — validates memory quality before storing
    memory.add("User prefers dark mode", user_id="user_123")
"""
from __future__ import annotations

import hashlib
import logging
import warnings
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)


class BlockedByPreflight(Exception):
    """Raised when preflight returns BLOCK and on_block='raise'."""
    pass


class SafeMemoraeMemory:
    """Memorae memory wrapper with automatic Sgraal preflight guards.

    Intercepts search() and add() calls with memory governance validation.

    Args:
        api_key: Sgraal API key (sg_live_... or sg_test_...)
        memorae_token: Memorae API token
        memorae_url: Memorae API base URL
        api_url: Sgraal API base URL
        on_block: behavior when BLOCK returned ("raise" | "warn" | "skip" | "heal")
        default_trust: source_trust for Memorae entries (default 0.75)
        domain: Sgraal domain for preflight (default "customer_support")
    """

    def __init__(
        self,
        api_key: str,
        memorae_token: str = "",
        memorae_url: str = "https://api.memorae.ai",
        api_url: str = "https://api.sgraal.com",
        on_block: str = "raise",
        default_trust: float = 0.75,
        domain: str = "customer_support",
    ):
        self.api_key = api_key
        self.memorae_token = memorae_token
        self.memorae_url = memorae_url.rstrip("/")
        self.api_url = api_url.rstrip("/")
        self.on_block = on_block
        self.default_trust = default_trust
        self.domain = domain
        self._session = requests.Session()
        self._session.headers.update({"Authorization": f"Bearer {api_key}"})

    def _to_sgraal_entries(self, memories: list[dict]) -> list[dict]:
        """Convert Memorae memory format to Sgraal MemCube format."""
        entries = []
        for i, mem in enumerate(memories):
            content = mem.get("content") or mem.get("text") or mem.get("message") or str(mem)
            mem_type = mem.get("type", "episodic")
            age_days = mem.get("age_days", 1)
            # Map Memorae confidence to Sgraal trust
            confidence = mem.get("confidence", self.default_trust)
            entries.append({
                "id": mem.get("id") or hashlib.sha256(content.encode()).hexdigest()[:12],
                "content": content,
                "type": mem_type if mem_type in ("semantic", "episodic", "preference", "tool_state",
                                                  "shared_workflow", "policy", "identity") else "episodic",
                "timestamp_age_days": age_days,
                "source_trust": min(1.0, max(0.0, confidence)),
                "source_conflict": mem.get("conflict", 0.1),
                "downstream_count": mem.get("downstream_count", 1),
            })
        return entries

    def _run_preflight(self, entries: list[dict], action_type: str = "informational") -> dict:
        """Run Sgraal preflight on memory entries."""
        try:
            resp = self._session.post(f"{self.api_url}/v1/preflight", json={
                "memory_state": entries,
                "action_type": action_type,
                "domain": self.domain,
            }, timeout=5)
            if resp.ok:
                return resp.json()
            logger.warning("Sgraal preflight returned %d", resp.status_code)
            return {"recommended_action": "USE_MEMORY", "omega_mem_final": 0}
        except Exception as e:
            logger.warning("Sgraal preflight failed: %s", e)
            return {"recommended_action": "USE_MEMORY", "omega_mem_final": 0}

    def _handle_block(self, preflight_result: dict, context: str = "search") -> bool:
        """Handle BLOCK decision. Returns True if operation should proceed."""
        action = preflight_result.get("recommended_action", "USE_MEMORY")
        omega = preflight_result.get("omega_mem_final", 0)

        if action == "BLOCK":
            if self.on_block == "raise":
                raise BlockedByPreflight(
                    f"Sgraal BLOCK on {context}: omega={omega}, "
                    f"reason={preflight_result.get('explainability_note', 'high risk')}"
                )
            elif self.on_block == "warn":
                warnings.warn(f"Sgraal BLOCK on {context}: omega={omega}", stacklevel=3)
                return True
            elif self.on_block == "skip":
                return False
            elif self.on_block == "heal":
                logger.info("Sgraal BLOCK on %s, attempting heal", context)
                return True

        if action in ("WARN", "ASK_USER"):
            logger.info("Sgraal %s on %s: omega=%s", action, context, omega)

        return True

    def search(self, query: str, user_id: str = "", limit: int = 10, **kwargs) -> list[dict]:
        """Search Memorae with Sgraal preflight guard.

        Returns memories that pass governance checks.
        """
        # Fetch from Memorae
        try:
            memorae_resp = self._session.get(
                f"{self.memorae_url}/v1/search",
                params={"q": query, "user_id": user_id, "limit": limit},
                headers={"Authorization": f"Bearer {self.memorae_token}"},
                timeout=5,
            )
            memories = memorae_resp.json() if memorae_resp.ok else []
            if isinstance(memories, dict):
                memories = memories.get("results", memories.get("memories", []))
        except Exception:
            memories = []

        if not memories:
            return []

        # Run preflight
        entries = self._to_sgraal_entries(memories)
        preflight = self._run_preflight(entries, "informational")

        if not self._handle_block(preflight, "search"):
            return []

        # Attach governance metadata
        for mem in memories:
            mem["_sgraal_omega"] = preflight.get("omega_mem_final", 0)
            mem["_sgraal_action"] = preflight.get("recommended_action", "USE_MEMORY")

        return memories

    def add(self, content: str, user_id: str = "", memory_type: str = "episodic", **kwargs) -> dict:
        """Add memory to Memorae with Sgraal preflight guard.

        Validates memory quality before storing.
        """
        entry = self._to_sgraal_entries([{
            "content": content, "type": memory_type,
            "age_days": 0, "confidence": self.default_trust,
        }])
        preflight = self._run_preflight(entry, "reversible")

        if not self._handle_block(preflight, "add"):
            return {"stored": False, "reason": "blocked_by_sgraal"}

        # Store in Memorae
        try:
            resp = requests.post(
                f"{self.memorae_url}/v1/memories",
                json={"content": content, "user_id": user_id, "type": memory_type, **kwargs},
                headers={"Authorization": f"Bearer {self.memorae_token}"},
                timeout=5,
            )
            result = resp.json() if resp.ok else {"stored": False, "error": resp.status_code}
        except Exception as e:
            result = {"stored": False, "error": str(e)}

        result["_sgraal_omega"] = preflight.get("omega_mem_final", 0)
        result["_sgraal_action"] = preflight.get("recommended_action", "USE_MEMORY")
        return result
