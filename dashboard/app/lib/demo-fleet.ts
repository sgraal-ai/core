export interface DemoAgent {
  id: string;
  name: string;
  domain: string;
  action_type: string;
  memory_state: Record<string, unknown>[];
}

export const DEMO_FLEET: DemoAgent[] = [
  {
    id: "agent-onboarding-eu",
    name: "EU Onboarding Agent",
    domain: "customer_support",
    action_type: "reversible",
    memory_state: [
      {
        id: "mem_welcome_flow",
        content: "Welcome email sent to new EU customers on signup",
        type: "shared_workflow",
        timestamp_age_days: 2,
        source_trust: 0.95,
        source_conflict: 0.05,
        downstream_count: 3,
        r_belief: 0.85,
      },
      {
        id: "mem_gdpr_consent",
        content: "GDPR consent collected at registration step 2",
        type: "policy",
        timestamp_age_days: 5,
        source_trust: 0.98,
        source_conflict: 0.02,
        downstream_count: 6,
        r_belief: 0.92,
      },
    ],
  },
  {
    id: "agent-fintech-trade",
    name: "Fintech Trade Executor",
    domain: "fintech",
    action_type: "irreversible",
    memory_state: [
      {
        id: "mem_exchange_rate",
        content: "EUR/USD exchange rate: 1.0842 (last fetched 2026-03-08)",
        type: "tool_state",
        timestamp_age_days: 15,
        source_trust: 0.88,
        source_conflict: 0.22,
        downstream_count: 8,
        r_belief: 0.6,
        source: "api_response",
        has_backup_source: true,
      },
      {
        id: "mem_trade_limit",
        content: "Daily trade limit for standard accounts: €50,000",
        type: "policy",
        timestamp_age_days: 30,
        source_trust: 0.95,
        source_conflict: 0.1,
        downstream_count: 5,
        r_belief: 0.75,
      },
    ],
  },
  {
    id: "agent-medical-triage",
    name: "Medical Triage Assistant",
    domain: "medical",
    action_type: "irreversible",
    memory_state: [
      {
        id: "mem_patient_allergy",
        content: "Patient allergic to penicillin — confirmed June 2025",
        type: "tool_state",
        timestamp_age_days: 290,
        source_trust: 0.9,
        source_conflict: 0.1,
        downstream_count: 4,
        r_belief: 0.5,
        source: "user_stated",
        has_backup_source: false,
        action_context: "irreversible",
        reference_count: 6,
      },
      {
        id: "mem_drug_interaction",
        content: "Amoxicillin + Warfarin: increased bleeding risk",
        type: "semantic",
        timestamp_age_days: 45,
        source_trust: 0.7,
        source_conflict: 0.55,
        downstream_count: 3,
        r_belief: 0.4,
      },
    ],
  },
  {
    id: "agent-legal-review",
    name: "Legal Contract Reviewer",
    domain: "legal",
    action_type: "irreversible",
    memory_state: [
      {
        id: "mem_contract_clause_7",
        content: "Liability clause §7.2 — capped at €500K per incident",
        type: "tool_state",
        timestamp_age_days: 180,
        source_trust: 0.6,
        source_conflict: 0.65,
        downstream_count: 10,
        r_belief: 0.2,
        source: "user_stated",
        has_backup_source: false,
        action_context: "irreversible",
        reference_count: 8,
      },
    ],
  },
  {
    id: "agent-code-assistant",
    name: "Coding Assistant",
    domain: "coding",
    action_type: "reversible",
    memory_state: [
      {
        id: "mem_repo_structure",
        content: "Main branch: src/components/, src/lib/, src/app/",
        type: "semantic",
        timestamp_age_days: 1,
        source_trust: 0.99,
        source_conflict: 0.01,
        downstream_count: 2,
        r_belief: 0.95,
      },
    ],
  },
];
