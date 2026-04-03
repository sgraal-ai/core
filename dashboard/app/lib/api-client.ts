import type { Agent } from "./mock-data";
import type { DemoAgent } from "./demo-fleet";

const DEFAULT_API_URL = process.env.NEXT_PUBLIC_SGRAAL_API_URL ?? "https://api.sgraal.com";

export async function fetchPreflight(
  agent: DemoAgent,
  apiKey: string,
  apiUrl: string = DEFAULT_API_URL,
): Promise<Agent> {
  const res = await fetch(`${apiUrl}/v1/preflight`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      agent_id: agent.id,
      memory_state: agent.memory_state,
      action_type: agent.action_type,
      domain: agent.domain,
      response_profile: "standard",
    }),
  });

  if (!res.ok) {
    throw new Error(`Preflight failed for ${agent.id}: ${res.status}`);
  }

  const data = await res.json();

  return {
    id: agent.id,
    name: agent.name,
    omega_mem_final: data.omega_mem_final,
    recommended_action: data.recommended_action,
    assurance_score: data.assurance_score,
    domain: agent.domain,
    last_preflight: new Date().toISOString(),
    healing_counter: data.healing_counter ?? 0,
    gsv: data.gsv ?? 0,
    component_breakdown: data.component_breakdown,
    repair_plan: data.repair_plan ?? [],
    at_risk_warnings: data.at_risk_warnings ?? [],
    compliance_result: data.compliance_result ?? {
      compliant: true,
      violations: [],
      audit_required: false,
      profile_applied: "GENERAL",
    },
    calibration: data.calibration,
    hawkes_intensity: data.hawkes_intensity,
    copula_analysis: data.copula_analysis,
    mewma: data.mewma,
  };
}

export async function fetchFleet(
  fleet: DemoAgent[],
  apiKey: string,
  apiUrl?: string,
): Promise<{ agents: Agent[]; errors: string[] }> {
  const agents: Agent[] = [];
  const errors: string[] = [];

  await Promise.all(
    fleet.map(async (demo) => {
      try {
        const agent = await fetchPreflight(demo, apiKey, apiUrl);
        agents.push(agent);
      } catch (err) {
        errors.push(err instanceof Error ? err.message : String(err));
      }
    }),
  );

  // Sort by omega_mem_final descending (highest risk first)
  agents.sort((a, b) => b.omega_mem_final - a.omega_mem_final);
  return { agents, errors };
}
