"""cloudflare-sgraal: Sgraal preflight guard for Cloudflare Agent Memory.

Cloudflare Agent Memory stores and recalls memories for AI agents.
This bridge validates recalled memories through Sgraal preflight
before the agent acts on them.

    Cloudflare stores it. Sgraal validates it.

Usage:
    from cloudflare_sgraal import CloudflareSgraalBridge

    bridge = CloudflareSgraalBridge(
        cloudflare_account_id="your-account-id",
        cloudflare_api_token="your-cf-token",
        sgraal_api_key="sg_live_...",
    )

    result = bridge.recall_and_validate(
        profile_id="my-project",
        query="What package manager does the user prefer?",
        action_type="reversible",
        domain="coding",
    )

    if result["sgraal_decision"] == "USE_MEMORY":
        answer = result["synthesized_answer"]
        # safe to act on
"""
from __future__ import annotations

import hashlib
import logging
import warnings
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)


class BlockedByPreflight(Exception):
    """Raised when Sgraal preflight returns BLOCK and on_block='raise'."""
    pass


# Cloudflare Agent Memory REST API base URL pattern.
# The API is in private beta; endpoints follow standard Cloudflare v4 conventions.
_CF_API_BASE = "https://api.cloudflare.com/client/v4/accounts/{account_id}/agent-memory"


class CloudflareSgraalBridge:
    """Bridge between Cloudflare Agent Memory and Sgraal preflight.

    Recalls memories from Cloudflare, converts them to MemCube format,
    runs Sgraal preflight validation, and returns the combined result.

    Args:
        cloudflare_account_id: Cloudflare account ID.
        cloudflare_api_token: Cloudflare API token with Agent Memory permissions.
        sgraal_api_key: Sgraal API key (sg_live_... or sg_test_...).
        sgraal_api_url: Sgraal API base URL (default: https://api.sgraal.com).
        on_block: Behavior when BLOCK returned ("raise" | "warn" | "pass").
            - "raise": raise BlockedByPreflight exception (default, safest).
            - "warn": emit warning but return memories anyway.
            - "pass": silently return memories (caller handles decision).
        default_trust: Default source_trust for Cloudflare memories (0.0-1.0).
        timeout: HTTP timeout in seconds for both APIs.
    """

    # Map Cloudflare memory types to MemCube types.
    _TYPE_MAP = {
        "fact": "semantic",
        "facts": "semantic",
        "event": "episodic",
        "events": "episodic",
        "instruction": "policy",
        "instructions": "policy",
        "task": "tool_state",
        "tasks": "tool_state",
    }

    def __init__(
        self,
        cloudflare_account_id: str,
        cloudflare_api_token: str,
        sgraal_api_key: str,
        sgraal_api_url: str = "https://api.sgraal.com",
        on_block: str = "raise",
        default_trust: float = 0.85,
        timeout: int = 10,
    ):
        self.cf_account_id = cloudflare_account_id
        self.cf_token = cloudflare_api_token
        self.sgraal_key = sgraal_api_key
        self.sgraal_url = sgraal_api_url.rstrip("/")
        self.on_block = on_block
        self.default_trust = default_trust
        self.timeout = timeout
        self._cf_base = _CF_API_BASE.format(account_id=cloudflare_account_id)
        self._cf_headers = {
            "Authorization": f"Bearer {cloudflare_api_token}",
            "Content-Type": "application/json",
        }
        self._sgraal_headers = {
            "Authorization": f"Bearer {sgraal_api_key}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Cloudflare Agent Memory operations
    # ------------------------------------------------------------------

    def recall(self, profile_id: str, query: str) -> dict:
        """Recall memories from Cloudflare Agent Memory.

        Returns the raw Cloudflare response including synthesized answer
        and matching memory entries.
        """
        resp = requests.post(
            f"{self._cf_base}/profiles/{profile_id}/recall",
            json={"query": query},
            headers=self._cf_headers,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def remember(self, profile_id: str, content: str, session_id: Optional[str] = None) -> dict:
        """Store a single memory in Cloudflare Agent Memory."""
        body: dict[str, Any] = {"content": content}
        if session_id:
            body["sessionId"] = session_id
        resp = requests.post(
            f"{self._cf_base}/profiles/{profile_id}/remember",
            json=body,
            headers=self._cf_headers,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def ingest(self, profile_id: str, messages: list[dict], session_id: Optional[str] = None) -> dict:
        """Ingest a conversation into Cloudflare Agent Memory.

        Args:
            profile_id: Cloudflare memory profile ID.
            messages: List of {"role": "user"|"assistant", "content": "..."}.
            session_id: Optional session identifier.
        """
        body: dict[str, Any] = {"messages": messages}
        if session_id:
            body["sessionId"] = session_id
        resp = requests.post(
            f"{self._cf_base}/profiles/{profile_id}/ingest",
            json=body,
            headers=self._cf_headers,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def list_memories(self, profile_id: str) -> dict:
        """List all stored memories for a profile."""
        resp = requests.get(
            f"{self._cf_base}/profiles/{profile_id}/memories",
            headers=self._cf_headers,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def forget(self, profile_id: str, memory_id: str) -> dict:
        """Mark a memory as no longer relevant."""
        resp = requests.delete(
            f"{self._cf_base}/profiles/{profile_id}/memories/{memory_id}",
            headers=self._cf_headers,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Conversion: Cloudflare → MemCube
    # ------------------------------------------------------------------

    def _to_memory_state(self, cf_memories: list[dict]) -> list[dict]:
        """Convert Cloudflare Agent Memory entries to Sgraal MemCube format.

        Cloudflare memories have: id, content, type (fact/event/instruction/task),
        topic_key, session_id, created_at. We map these to MemCube's required fields.
        """
        entries = []
        for i, mem in enumerate(cf_memories):
            content = mem.get("content", mem.get("text", ""))
            cf_type = mem.get("type", "fact").lower()
            memcube_type = self._TYPE_MAP.get(cf_type, "semantic")

            # Estimate age from created_at if available
            age_days = 0.0
            created_at = mem.get("created_at") or mem.get("createdAt")
            if created_at:
                try:
                    from datetime import datetime, timezone
                    if isinstance(created_at, str):
                        ts = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    else:
                        ts = datetime.fromtimestamp(created_at, tz=timezone.utc)
                    age_days = max(0, (datetime.now(timezone.utc) - ts).total_seconds() / 86400)
                except Exception:
                    pass

            # Deterministic ID: use Cloudflare's ID or hash content
            entry_id = mem.get("id") or hashlib.sha256(content.encode()).hexdigest()[:16]

            entries.append({
                "id": str(entry_id),
                "content": content[:2000],
                "type": memcube_type,
                "timestamp_age_days": round(age_days, 2),
                "source_trust": self.default_trust,
                "source_conflict": 0.05,
                "downstream_count": 1,
                "source": "cloudflare_agent_memory",
            })
        return entries

    # ------------------------------------------------------------------
    # Sgraal preflight
    # ------------------------------------------------------------------

    def _run_preflight(
        self,
        memory_state: list[dict],
        action_type: str = "reversible",
        domain: str = "general",
        agent_id: str = "cloudflare-agent",
    ) -> dict:
        """Run Sgraal preflight on converted memory entries."""
        resp = requests.post(
            f"{self.sgraal_url}/v1/preflight",
            json={
                "memory_state": memory_state,
                "action_type": action_type,
                "domain": domain,
                "agent_id": agent_id,
            },
            headers=self._sgraal_headers,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def _handle_decision(self, decision: str, sgraal_result: dict) -> None:
        """Handle Sgraal decision based on on_block policy."""
        if decision in ("USE_MEMORY", "WARN"):
            if decision == "WARN":
                warnings.warn(
                    f"Sgraal WARN: omega={sgraal_result.get('omega_mem_final')} "
                    f"— proceed with caution",
                    UserWarning,
                    stacklevel=4,
                )
            return

        # ASK_USER or BLOCK
        omega = sgraal_result.get("omega_mem_final", 0)
        repair = sgraal_result.get("repair_plan", [])

        if self.on_block == "raise":
            raise BlockedByPreflight(
                f"Sgraal {decision}: omega={omega}. "
                f"Memory is not safe to act on. "
                f"Repair: {[r.get('action') for r in repair[:3]]}"
            )
        elif self.on_block == "warn":
            warnings.warn(
                f"Sgraal {decision}: omega={omega} — memory unreliable. "
                f"Repair: {[r.get('action') for r in repair[:3]]}",
                UserWarning,
                stacklevel=4,
            )
        # "pass" — silently continue, caller checks sgraal_decision

    # ------------------------------------------------------------------
    # Main API: recall + validate
    # ------------------------------------------------------------------

    def recall_and_validate(
        self,
        profile_id: str,
        query: str,
        action_type: str = "reversible",
        domain: str = "general",
        agent_id: str = "cloudflare-agent",
    ) -> dict:
        """Recall memories from Cloudflare and validate through Sgraal preflight.

        This is the primary method. It:
        1. Recalls memories from Cloudflare Agent Memory
        2. Converts to MemCube format
        3. Runs Sgraal preflight validation
        4. Returns combined result with decision

        Args:
            profile_id: Cloudflare memory profile ID.
            query: Natural language query for memory recall.
            action_type: Sgraal action type (informational/reversible/irreversible/destructive).
            domain: Sgraal domain (general/customer_support/coding/legal/fintech/medical).
            agent_id: Agent identifier for audit trail.

        Returns:
            {
                "cloudflare_memories": [...],      # Raw recalled memories
                "synthesized_answer": "...",        # Cloudflare's synthesized answer
                "memory_state": [...],              # MemCube-converted entries
                "sgraal_decision": "USE_MEMORY",    # Sgraal decision
                "sgraal_omega": 12.3,               # Risk score (0-100)
                "sgraal_result": {...},              # Full Sgraal preflight response
                "safe_to_act": True,                # Convenience boolean
            }

        Raises:
            BlockedByPreflight: If decision is BLOCK/ASK_USER and on_block="raise".
            requests.HTTPError: If either API call fails.
        """
        # 1. Recall from Cloudflare
        cf_response = self.recall(profile_id, query)

        # Extract memories and synthesized answer from Cloudflare response.
        # Cloudflare returns {result: "synthesized answer", memories: [...]}
        # but the exact shape may vary in beta.
        cf_result = cf_response.get("result", cf_response)
        if isinstance(cf_result, str):
            synthesized = cf_result
            cf_memories = cf_response.get("memories", [])
        elif isinstance(cf_result, dict):
            synthesized = cf_result.get("result", cf_result.get("answer", ""))
            cf_memories = cf_result.get("memories", cf_result.get("matches", []))
        else:
            synthesized = str(cf_result)
            cf_memories = []

        if not cf_memories:
            return {
                "cloudflare_memories": [],
                "synthesized_answer": synthesized,
                "memory_state": [],
                "sgraal_decision": "USE_MEMORY",
                "sgraal_omega": 0.0,
                "sgraal_result": {},
                "safe_to_act": True,
            }

        # 2. Convert to MemCube format
        memory_state = self._to_memory_state(cf_memories)

        # 3. Run Sgraal preflight
        try:
            sgraal_result = self._run_preflight(memory_state, action_type, domain, agent_id)
            decision = sgraal_result.get("recommended_action", "USE_MEMORY")
            omega = float(sgraal_result.get("omega_mem_final", 0))
        except Exception as e:
            logger.warning("Sgraal preflight failed, allowing recall: %s", e)
            return {
                "cloudflare_memories": cf_memories,
                "synthesized_answer": synthesized,
                "memory_state": memory_state,
                "sgraal_decision": "USE_MEMORY",
                "sgraal_omega": 0.0,
                "sgraal_result": {"error": str(e)[:200]},
                "safe_to_act": True,
                "sgraal_unavailable": True,
            }

        # 4. Handle decision (may raise BlockedByPreflight)
        self._handle_decision(decision, sgraal_result)

        return {
            "cloudflare_memories": cf_memories,
            "synthesized_answer": synthesized,
            "memory_state": memory_state,
            "sgraal_decision": decision,
            "sgraal_omega": omega,
            "sgraal_result": sgraal_result,
            "safe_to_act": decision in ("USE_MEMORY", "WARN"),
        }

    def validate_memories(
        self,
        memories: list[dict],
        action_type: str = "reversible",
        domain: str = "general",
        agent_id: str = "cloudflare-agent",
    ) -> dict:
        """Validate pre-fetched Cloudflare memories through Sgraal.

        Use this when you already have memories from Cloudflare's Worker
        binding (env.MEMORY.getProfile().recall()) and want to validate
        them without recalling again via REST.

        Args:
            memories: List of Cloudflare memory objects.
            action_type: Sgraal action type.
            domain: Sgraal domain.
            agent_id: Agent identifier.

        Returns:
            Same shape as recall_and_validate().
        """
        memory_state = self._to_memory_state(memories)

        try:
            sgraal_result = self._run_preflight(memory_state, action_type, domain, agent_id)
            decision = sgraal_result.get("recommended_action", "USE_MEMORY")
            omega = float(sgraal_result.get("omega_mem_final", 0))
        except Exception as e:
            logger.warning("Sgraal preflight failed: %s", e)
            return {
                "cloudflare_memories": memories,
                "memory_state": memory_state,
                "sgraal_decision": "USE_MEMORY",
                "sgraal_omega": 0.0,
                "sgraal_result": {"error": str(e)[:200]},
                "safe_to_act": True,
                "sgraal_unavailable": True,
            }

        self._handle_decision(decision, sgraal_result)

        return {
            "cloudflare_memories": memories,
            "memory_state": memory_state,
            "sgraal_decision": decision,
            "sgraal_omega": omega,
            "sgraal_result": sgraal_result,
            "safe_to_act": decision in ("USE_MEMORY", "WARN"),
        }
