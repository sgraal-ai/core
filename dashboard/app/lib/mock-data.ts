export interface Agent {
  id: string;
  name: string;
  omega_mem_final: number;
  recommended_action: "USE_MEMORY" | "WARN" | "ASK_USER" | "BLOCK";
  assurance_score: number;
  domain: string;
  last_preflight: string;
  healing_counter: number;
  gsv: number;
  component_breakdown: Record<string, number>;
  repair_plan: RepairAction[];
  at_risk_warnings: AtRiskWarning[];
  compliance_result: ComplianceResult;
}

export interface RepairAction {
  action: string;
  entry_id: string;
  reason: string;
  projected_improvement: number;
  priority: number;
}

export interface AtRiskWarning {
  entry_id: string;
  importance_score: number;
  warning: string;
}

export interface ComplianceResult {
  compliant: boolean;
  violations: { article: string; description: string; severity: string }[];
  audit_required: boolean;
  profile_applied: string;
}

export const MOCK_AGENTS: Agent[] = [
  {
    id: "agent-onboarding-eu",
    name: "EU Onboarding Agent",
    omega_mem_final: 12.4,
    recommended_action: "USE_MEMORY",
    assurance_score: 91,
    domain: "customer_support",
    last_preflight: "2026-03-23T14:22:00Z",
    healing_counter: 0,
    gsv: 1847,
    component_breakdown: {
      s_freshness: 8.2, s_drift: 5.1, s_provenance: 3.0, s_propagation: 12.0,
      r_recall: 6.1, r_encode: 1.5, s_interference: 4.0, s_recovery: 96.1,
      r_belief: 15.0, s_relevance: 0.0,
    },
    repair_plan: [],
    at_risk_warnings: [],
    compliance_result: { compliant: true, violations: [], audit_required: false, profile_applied: "EU_AI_ACT" },
  },
  {
    id: "agent-fintech-trade",
    name: "Fintech Trade Executor",
    omega_mem_final: 38.7,
    recommended_action: "WARN",
    assurance_score: 73,
    domain: "fintech",
    last_preflight: "2026-03-23T14:19:30Z",
    healing_counter: 3,
    gsv: 1845,
    component_breakdown: {
      s_freshness: 42.0, s_drift: 31.2, s_provenance: 15.0, s_propagation: 24.0,
      r_recall: 31.2, r_encode: 7.5, s_interference: 22.0, s_recovery: 79.0,
      r_belief: 30.0, s_relevance: 10.0,
    },
    repair_plan: [
      { action: "REFETCH", entry_id: "mem_exchange_rate", reason: "Memory is stale (freshness=42/100, type=tool_state)", projected_improvement: 6.3, priority: 2 },
      { action: "VERIFY_WITH_SOURCE", entry_id: "mem_compliance_rule", reason: "High source conflict (K=0.55)", projected_improvement: 3.1, priority: 2 },
    ],
    at_risk_warnings: [],
    compliance_result: { compliant: true, violations: [], audit_required: false, profile_applied: "EU_AI_ACT" },
  },
  {
    id: "agent-medical-triage",
    name: "Medical Triage Assistant",
    omega_mem_final: 54.2,
    recommended_action: "ASK_USER",
    assurance_score: 62,
    domain: "medical",
    last_preflight: "2026-03-23T14:15:00Z",
    healing_counter: 7,
    gsv: 1842,
    component_breakdown: {
      s_freshness: 65.0, s_drift: 48.0, s_provenance: 25.0, s_propagation: 40.0,
      r_recall: 49.0, r_encode: 12.5, s_interference: 35.0, s_recovery: 67.5,
      r_belief: 45.0, s_relevance: 20.0,
    },
    repair_plan: [
      { action: "REFETCH", entry_id: "mem_patient_allergy", reason: "Memory is stale (freshness=65/100, type=tool_state)", projected_improvement: 9.8, priority: 1 },
      { action: "VERIFY_WITH_SOURCE", entry_id: "mem_drug_interaction", reason: "High source conflict (K=0.72)", projected_improvement: 5.2, priority: 1 },
      { action: "REBUILD_WORKING_SET", entry_id: "mem_treatment_plan", reason: "Low model belief (r_belief=0.22)", projected_improvement: 3.5, priority: 2 },
    ],
    at_risk_warnings: [
      { entry_id: "mem_patient_allergy", importance_score: 8.2, warning: "\u26a0\ufe0f Memory at risk: 'Patient allergic to penicillin — confirmed 2025-06' (290 days old, only known from a single source). Consider refreshing before proceeding." },
    ],
    compliance_result: {
      compliant: false,
      violations: [
        { article: "Article 9", description: "Medical domain with elevated risk. Human oversight required before proceeding.", severity: "high" },
      ],
      audit_required: true,
      profile_applied: "EU_AI_ACT",
    },
  },
  {
    id: "agent-legal-review",
    name: "Legal Contract Reviewer",
    omega_mem_final: 82.1,
    recommended_action: "BLOCK",
    assurance_score: 42,
    domain: "legal",
    last_preflight: "2026-03-23T14:10:00Z",
    healing_counter: 12,
    gsv: 1839,
    component_breakdown: {
      s_freshness: 88.0, s_drift: 72.0, s_provenance: 40.0, s_propagation: 56.0,
      r_recall: 68.8, r_encode: 20.0, s_interference: 55.0, s_recovery: 56.0,
      r_belief: 70.0, s_relevance: 20.0,
    },
    repair_plan: [
      { action: "REFETCH", entry_id: "mem_contract_clause_7", reason: "Memory is stale (freshness=88/100, type=tool_state)", projected_improvement: 13.2, priority: 1 },
      { action: "VERIFY_WITH_SOURCE", entry_id: "mem_precedent_case", reason: "High source conflict (K=0.82)", projected_improvement: 8.1, priority: 1 },
      { action: "REBUILD_WORKING_SET", entry_id: "mem_client_intent", reason: "Low model belief (r_belief=0.15)", projected_improvement: 5.8, priority: 1 },
    ],
    at_risk_warnings: [
      { entry_id: "mem_contract_clause_7", importance_score: 9.1, warning: "\u26a0\ufe0f Memory at risk: 'Liability clause §7.2 — capped at €500K per incident' (180 days old, used in irreversible actions). Consider refreshing before proceeding." },
      { entry_id: "mem_precedent_case", importance_score: 7.5, warning: "\u26a0\ufe0f Memory at risk: 'Kovács v. TechCorp (2024) — established duty of care' (210 days old, only known from a single source). Consider refreshing before proceeding." },
    ],
    compliance_result: {
      compliant: false,
      violations: [
        { article: "Article 12", description: "High-risk memory state used in irreversible action. Audit trail required.", severity: "critical" },
      ],
      audit_required: true,
      profile_applied: "EU_AI_ACT",
    },
  },
  {
    id: "agent-code-assistant",
    name: "Coding Assistant",
    omega_mem_final: 5.1,
    recommended_action: "USE_MEMORY",
    assurance_score: 96,
    domain: "coding",
    last_preflight: "2026-03-23T14:25:00Z",
    healing_counter: 1,
    gsv: 1849,
    component_breakdown: {
      s_freshness: 2.0, s_drift: 1.8, s_provenance: 5.0, s_propagation: 8.0,
      r_recall: 3.2, r_encode: 2.5, s_interference: 2.0, s_recovery: 99.0,
      r_belief: 10.0, s_relevance: 0.0,
    },
    repair_plan: [],
    at_risk_warnings: [],
    compliance_result: { compliant: true, violations: [], audit_required: false, profile_applied: "GENERAL" },
  },
];

export function getAgent(id: string): Agent | undefined {
  return MOCK_AGENTS.find((a) => a.id === id);
}
