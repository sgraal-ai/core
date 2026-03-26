"""mem0-sgraal: Drop-in Sgraal-guarded wrapper for Mem0 Memory."""
from __future__ import annotations

import logging
import warnings
from typing import Any, Optional

try:
    from mem0 import Memory
except ImportError:
    raise ImportError(
        "mem0-sgraal requires mem0ai package: pip install mem0ai"
    )

logger = logging.getLogger(__name__)


class BlockedByPreflight(Exception):
    """Raised when preflight returns BLOCK and on_block='raise'."""
    pass


class SafeMemory:
    """Mem0 Memory wrapper with automatic Sgraal preflight guards.

    Performs preflight scoring before every search() call.

    Args:
        api_key: Sgraal API key (sg_live_... or sg_test_...)
        api_url: Sgraal API base URL
        on_block: behavior when BLOCK returned ("raise" | "warn" | "skip" | "heal")
        default_trust: source_trust estimate for Mem0 entries (default 0.8)
        mem0_config: config dict passed to Mem0 Memory()
    """

    def __init__(
        self,
        api_key: str,
        api_url: str = "https://api.sgraal.com",
        on_block: str = "raise",
        default_trust: float = 0.8,
        mem0_config: Optional[dict] = None,
    ):
        self.api_key = api_key
        self.api_url = api_url.rstrip("/")
        self.on_block = on_block
        self.default_trust = default_trust
        self._mem0 = Memory(**(mem0_config or {}))

    def _to_memory_state(self, results: list[dict]) -> list[dict]:
        """Convert Mem0 search results to Sgraal memory_state format."""
        entries = []
        for i, r in enumerate(results):
            meta = r.get("metadata", {}) or {}
            entries.append({
                "id": r.get("id", f"mem0_{i}"),
                "content": r.get("memory", r.get("text", "")),
                "type": meta.get("type", "episodic"),
                "timestamp_age_days": meta.get("age_days", 0),
                "source_trust": meta.get("confidence", self.default_trust),
                "source_conflict": meta.get("conflict", 0.1),
                "downstream_count": meta.get("downstream", 1),
            })
        return entries

    def _run_preflight(self, memory_state: list[dict]) -> dict:
        """Call Sgraal preflight API."""
        import requests as _req
        resp = _req.post(
            f"{self.api_url}/v1/preflight",
            json={"memory_state": memory_state},
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def _handle_decision(self, decision: str, preflight: dict) -> Optional[str]:
        """Handle preflight decision. Returns None to proceed, or action taken."""
        if decision in ("USE_MEMORY", "WARN"):
            if decision == "WARN":
                warnings.warn(
                    f"Sgraal WARN: omega={preflight.get('omega_mem_final')} — proceed with caution",
                    UserWarning,
                    stacklevel=3,
                )
            return None

        # BLOCK or ASK_USER
        if self.on_block == "raise":
            raise BlockedByPreflight(
                f"Sgraal {decision}: omega={preflight.get('omega_mem_final')}. "
                f"Repair plan: {preflight.get('repair_plan', [])}"
            )
        elif self.on_block == "warn":
            warnings.warn(
                f"Sgraal {decision}: omega={preflight.get('omega_mem_final')} — memory unreliable",
                UserWarning,
                stacklevel=3,
            )
            return None
        elif self.on_block == "skip":
            logger.warning("Sgraal %s — skipping search results", decision)
            return "skipped"
        elif self.on_block == "heal":
            repair = preflight.get("repair_plan", [])
            for action in repair[:3]:
                try:
                    import requests as _req
                    _req.post(
                        f"{self.api_url}/v1/heal",
                        json={"entry_id": action.get("entry_id", "*"), "action": action.get("action", "REFETCH")},
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        timeout=5,
                    )
                except Exception:
                    pass
            return None
        return None

    def search(self, query: str, **kwargs: Any) -> list[dict]:
        """Search Mem0 with automatic Sgraal preflight guard."""
        results = self._mem0.search(query, **kwargs)

        if not results:
            return results

        memory_state = self._to_memory_state(results)
        try:
            preflight = self._run_preflight(memory_state)
            decision = preflight.get("recommended_action", "USE_MEMORY")
            action = self._handle_decision(decision, preflight)
            if action == "skipped":
                return []
        except BlockedByPreflight:
            raise
        except Exception as e:
            logger.warning("Sgraal preflight failed, allowing search: %s", e)

        return results

    def add(self, *args: Any, **kwargs: Any) -> Any:
        """Passthrough to Mem0 Memory.add()."""
        return self._mem0.add(*args, **kwargs)

    def get_all(self, *args: Any, **kwargs: Any) -> Any:
        """Passthrough to Mem0 Memory.get_all()."""
        return self._mem0.get_all(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> Any:
        """Passthrough to Mem0 Memory.delete()."""
        return self._mem0.delete(*args, **kwargs)
