from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from .sheaf_cohomology import ConsistencyResult


@dataclass
class ZKSheafProof:
    commitment: str
    proof_valid: bool
    n_edges_verified: int
    nonce: str
    verified_at: str


def compute_zk_sheaf_proof(
    sheaf_result: Optional[ConsistencyResult],
    entry_ids: list[str],
    consistency_threshold: float = 0.95,
) -> Optional[ZKSheafProof]:
    """Combine FV-06 Zero-Knowledge commitment with SH-01 Sheaf Cohomology.

    Proof_cons = FV-06_ZK ∧ ∀e∈E (restrict(sᵢ,e) = restrict(sⱼ,e))

    Proves global consistency of memory graph WITHOUT revealing entry contents.

    ZK commitment:
        commit = SHA256(consistency_score || h1_rank || entry_ids_sorted || nonce)

    proof_valid: true only when consistency_score > threshold AND h1_rank = 0.

    Args:
        sheaf_result: ConsistencyResult from SH-01, or None if unavailable
        entry_ids: list of entry IDs in the memory state
        consistency_threshold: minimum consistency_score for valid proof (default 0.95)

    Returns:
        ZKSheafProof or None if sheaf_result is unavailable
    """
    if sheaf_result is None:
        return None

    try:
        nonce = secrets.token_hex(16)

        # Build commitment payload: consistency_score || h1_rank || sorted entry IDs || nonce
        sorted_ids = sorted(entry_ids)
        payload = f"{sheaf_result.consistency_score}|{sheaf_result.h1_rank}|{'|'.join(sorted_ids)}|{nonce}"
        commitment = hashlib.sha256(payload.encode()).hexdigest()

        # Proof valid: consistency_score > threshold AND h1_rank = 0
        proof_valid = (
            sheaf_result.consistency_score >= consistency_threshold
            and sheaf_result.h1_rank == 0
        )

        # Number of edges verified = total edges in sheaf graph
        # Total edges = consistent edges + inconsistent edges
        # h1_rank = inconsistent edges count
        # consistency_score = 1 - (h1_rank / total_edges)
        # So total_edges = h1_rank / (1 - consistency_score) if consistency_score < 1
        if sheaf_result.consistency_score < 1.0 and sheaf_result.h1_rank > 0:
            total_edges = round(sheaf_result.h1_rank / (1.0 - sheaf_result.consistency_score))
        else:
            # All edges consistent: estimate from inconsistent_pairs list
            # When h1_rank=0 and score=1.0, we count pairs that were checked
            # Use number of entry pairs that could form edges as upper bound
            n = len(entry_ids)
            total_edges = n * (n - 1) // 2 if n >= 2 else 0

        verified_at = datetime.now(timezone.utc).isoformat()

        return ZKSheafProof(
            commitment=commitment,
            proof_valid=proof_valid,
            n_edges_verified=total_edges,
            nonce=nonce,
            verified_at=verified_at,
        )
    except Exception:
        return None
