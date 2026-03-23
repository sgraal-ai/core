from __future__ import annotations

from dataclasses import dataclass

from .compliance_engine import ComplianceProfile


@dataclass
class PolicyMatrixEntry:
    tier: int                # 1=auto-heal, 2=suggest, 3=log-only
    requires_approval: bool


# Default policy: tier=1, no approval
_DEFAULT = PolicyMatrixEntry(tier=1, requires_approval=False)

# Matrix: (memory_type, domain, profile) → PolicyMatrixEntry
# Only overrides are listed; everything else falls back to default.
_MATRIX: dict[tuple[str, str, ComplianceProfile], PolicyMatrixEntry] = {
    # FDA_510K — medical requires strict controls
    ("tool_state", "medical", ComplianceProfile.FDA_510K):     PolicyMatrixEntry(tier=3, requires_approval=True),
    ("semantic", "medical", ComplianceProfile.FDA_510K):       PolicyMatrixEntry(tier=3, requires_approval=True),
    ("episodic", "medical", ComplianceProfile.FDA_510K):       PolicyMatrixEntry(tier=2, requires_approval=True),
    ("preference", "medical", ComplianceProfile.FDA_510K):     PolicyMatrixEntry(tier=2, requires_approval=False),

    # EU_AI_ACT — fintech and legal need approval for auto-heal
    ("tool_state", "fintech", ComplianceProfile.EU_AI_ACT):    PolicyMatrixEntry(tier=2, requires_approval=True),
    ("tool_state", "legal", ComplianceProfile.EU_AI_ACT):      PolicyMatrixEntry(tier=2, requires_approval=True),
    ("semantic", "fintech", ComplianceProfile.EU_AI_ACT):      PolicyMatrixEntry(tier=2, requires_approval=False),
    ("semantic", "legal", ComplianceProfile.EU_AI_ACT):        PolicyMatrixEntry(tier=2, requires_approval=False),
    ("tool_state", "medical", ComplianceProfile.EU_AI_ACT):    PolicyMatrixEntry(tier=3, requires_approval=True),
    ("semantic", "medical", ComplianceProfile.EU_AI_ACT):      PolicyMatrixEntry(tier=2, requires_approval=True),

    # HIPAA — medical data requires approval
    ("tool_state", "medical", ComplianceProfile.HIPAA):        PolicyMatrixEntry(tier=3, requires_approval=True),
    ("semantic", "medical", ComplianceProfile.HIPAA):          PolicyMatrixEntry(tier=2, requires_approval=True),
    ("episodic", "medical", ComplianceProfile.HIPAA):          PolicyMatrixEntry(tier=2, requires_approval=True),

    # GENERAL — relaxed defaults
    ("tool_state", "general", ComplianceProfile.GENERAL):      PolicyMatrixEntry(tier=1, requires_approval=False),
    ("semantic", "general", ComplianceProfile.GENERAL):        PolicyMatrixEntry(tier=1, requires_approval=False),
}


class HealingPolicyMatrix:
    """Lookup healing tier and approval requirements based on memory_type × domain × compliance_profile."""

    def lookup(
        self,
        memory_type: str,
        domain: str,
        profile: ComplianceProfile = ComplianceProfile.GENERAL,
    ) -> PolicyMatrixEntry:
        return _MATRIX.get((memory_type, domain, profile), _DEFAULT)
