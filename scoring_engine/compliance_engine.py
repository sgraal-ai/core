from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ComplianceProfile(str, Enum):
    GENERAL = "GENERAL"
    EU_AI_ACT = "EU_AI_ACT"
    FDA_510K = "FDA_510K"
    HIPAA = "HIPAA"


@dataclass
class ComplianceViolation:
    article: str
    description: str
    severity: str  # "critical", "high", "medium"


@dataclass
class ComplianceResult:
    compliant: bool
    violations: list[ComplianceViolation] = field(default_factory=list)
    audit_required: bool = False
    profile_applied: str = "GENERAL"


class ComplianceEngine:
    """Evaluates preflight results against regulatory compliance profiles."""

    def evaluate(
        self,
        omega_mem_final: float,
        assurance_score: float,
        domain: str,
        action_type: str,
        profile: ComplianceProfile = ComplianceProfile.GENERAL,
    ) -> ComplianceResult:
        if profile == ComplianceProfile.EU_AI_ACT:
            return self._evaluate_eu_ai_act(omega_mem_final, assurance_score, domain, action_type)
        if profile == ComplianceProfile.FDA_510K:
            return self._evaluate_fda_510k(omega_mem_final, assurance_score, domain, action_type)
        if profile == ComplianceProfile.HIPAA:
            return self._evaluate_hipaa(omega_mem_final, assurance_score, domain, action_type)
        return ComplianceResult(compliant=True, profile_applied="GENERAL")

    def _evaluate_eu_ai_act(
        self, omega: float, assurance: float, domain: str, action_type: str,
    ) -> ComplianceResult:
        violations: list[ComplianceViolation] = []
        audit_required = False

        # Article 12: Logging & irreversible actions
        if omega > 60 and action_type == "irreversible":
            violations.append(ComplianceViolation(
                article="Article 12",
                description="High-risk memory state used in irreversible action. Audit trail required.",
                severity="critical",
            ))
            audit_required = True

        # Article 9: Risk management — medical domain
        if domain == "medical" and omega > 40:
            violations.append(ComplianceViolation(
                article="Article 9",
                description="Medical domain with elevated risk. Human oversight required before proceeding.",
                severity="high",
            ))
            audit_required = True

        # Article 13: Transparency — always enforced (no violation, just a note)
        # Explainability is always included in the response by design.

        return ComplianceResult(
            compliant=len(violations) == 0,
            violations=violations,
            audit_required=audit_required,
            profile_applied="EU_AI_ACT",
        )

    def _evaluate_fda_510k(
        self, omega: float, assurance: float, domain: str, action_type: str,
    ) -> ComplianceResult:
        violations: list[ComplianceViolation] = []
        audit_required = False

        if domain == "medical" and omega > 30:
            violations.append(ComplianceViolation(
                article="510(k) Predicate",
                description="Medical device memory state exceeds safety threshold. Requires predicate device comparison.",
                severity="critical",
            ))
            audit_required = True

        if action_type in ("irreversible", "destructive") and omega > 50:
            violations.append(ComplianceViolation(
                article="510(k) Risk Classification",
                description="High-risk action with elevated memory risk. Class III review required.",
                severity="high",
            ))
            audit_required = True

        return ComplianceResult(
            compliant=len(violations) == 0,
            violations=violations,
            audit_required=audit_required,
            profile_applied="FDA_510K",
        )

    def _evaluate_hipaa(
        self, omega: float, assurance: float, domain: str, action_type: str,
    ) -> ComplianceResult:
        violations: list[ComplianceViolation] = []
        audit_required = False

        if domain == "medical" and assurance < 70:
            violations.append(ComplianceViolation(
                article="HIPAA §164.312",
                description="Low assurance score for medical data. PHI integrity cannot be guaranteed.",
                severity="critical",
            ))
            audit_required = True

        return ComplianceResult(
            compliant=len(violations) == 0,
            violations=violations,
            audit_required=audit_required,
            profile_applied="HIPAA",
        )
