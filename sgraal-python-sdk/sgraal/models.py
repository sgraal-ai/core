"""Data models for the Sgraal SDK."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Decision(str, Enum):
    USE_MEMORY = "USE_MEMORY"
    WARN = "WARN"
    ASK_USER = "ASK_USER"
    BLOCK = "BLOCK"


@dataclass
class MemoryEntry:
    """MemCube v2 memory entry schema."""
    id: str
    content: str
    type: str = "semantic"
    timestamp_age_days: float = 0
    source_trust: float = 0.9
    source_conflict: float = 0.1
    downstream_count: int = 1

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "type": self.type,
            "timestamp_age_days": self.timestamp_age_days,
            "source_trust": self.source_trust,
            "source_conflict": self.source_conflict,
            "downstream_count": self.downstream_count,
        }


@dataclass
class PreflightResult:
    """Result from a preflight call."""
    omega_mem_final: float
    recommended_action: str
    assurance_score: float = 0
    component_breakdown: dict = field(default_factory=dict)
    repair_plan: list = field(default_factory=list)
    request_id: str = ""
    input_hash: str = ""
    deterministic: bool = True
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "PreflightResult":
        return cls(
            omega_mem_final=data.get("omega_mem_final", 0),
            recommended_action=data.get("recommended_action", "USE_MEMORY"),
            assurance_score=data.get("assurance_score", 0),
            component_breakdown=data.get("component_breakdown", {}),
            repair_plan=data.get("repair_plan", []),
            request_id=data.get("request_id", ""),
            input_hash=data.get("input_hash", ""),
            deterministic=data.get("deterministic", True),
            raw=data,
        )
