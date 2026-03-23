from __future__ import annotations

import hashlib
import hmac
import json
import re
from typing import Optional


class ObfuscatedId:
    """Layer 1: Entry ID obfuscation via HMAC-SHA256."""

    @staticmethod
    def obfuscate(entry_id: str, session_key: str) -> str:
        return hmac.new(
            session_key.encode(),
            entry_id.encode(),
            hashlib.sha256,
        ).hexdigest()[:16]

    @staticmethod
    def deobfuscate(
        obfuscated_id: str,
        session_key: str,
        original_ids: list[str],
    ) -> Optional[str]:
        for eid in original_ids:
            if ObfuscatedId.obfuscate(eid, session_key) == obfuscated_id:
                return eid
        return None


# Reason patterns → abstract categories
_REASON_PATTERNS = [
    (re.compile(r"stale|freshness", re.IGNORECASE), "STALE"),
    (re.compile(r"conflict|interfere", re.IGNORECASE), "CONFLICT"),
    (re.compile(r"trust|provenance", re.IGNORECASE), "LOW_TRUST"),
    (re.compile(r"propagation|downstream|blast", re.IGNORECASE), "PROPAGATION_RISK"),
    (re.compile(r"drift|relevance|goal|belief", re.IGNORECASE), "INTENT_DRIFT"),
]


class ReasonAbstractor:
    """Layer 2: Maps detailed repair reasons to abstract categories.

    No content, age, or specific values leak in the abstracted reason.
    """

    @staticmethod
    def abstract(reason: str) -> str:
        for pattern, category in _REASON_PATTERNS:
            if pattern.search(reason):
                return category
        return "GENERAL_RISK"


class ZKAssurance:
    """Layer 3: Zero-knowledge assurance (stub — full ZK proof in Phase 2).

    Provides a commitment hash that binds the omega_mem_final score to the
    entry IDs without revealing the entries themselves.
    """

    @staticmethod
    def commit(omega_mem_final: float, entry_ids: list[str]) -> str:
        payload = json.dumps(
            {"omega": omega_mem_final, "entries": sorted(entry_ids)},
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    @staticmethod
    def verify(commitment_hash: str, omega_mem_final: float, entry_ids: list[str]) -> bool:
        return ZKAssurance.commit(omega_mem_final, entry_ids) == commitment_hash
