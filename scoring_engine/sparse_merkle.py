from __future__ import annotations
import hashlib
from dataclasses import dataclass
from typing import Optional

@dataclass
class SparseMerkleResult:
    root_hash: str
    proof_depth: int
    integrity_verified: bool
    tamper_detected: bool

def compute_sparse_merkle(entry_ids: list[str], stored_root: Optional[str] = None) -> Optional[SparseMerkleResult]:
    if not entry_ids: return None
    try:
        leaves = sorted(hashlib.sha256(eid.encode()).hexdigest() for eid in entry_ids)
        level = leaves[:]
        depth = 0
        while len(level) > 1:
            next_level = []
            for i in range(0, len(level), 2):
                if i + 1 < len(level):
                    combined = level[i] + level[i+1]
                else:
                    combined = level[i] + level[i]
                next_level.append(hashlib.sha256(combined.encode()).hexdigest())
            level = next_level; depth += 1
        root = level[0]
        tamper = stored_root is not None and stored_root != root
        verified = stored_root is None or stored_root == root
        return SparseMerkleResult(root_hash=root, proof_depth=depth, integrity_verified=verified, tamper_detected=tamper)
    except Exception: return None
