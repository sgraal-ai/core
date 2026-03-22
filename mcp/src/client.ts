export interface MemoryEntry {
  id: string;
  content: string;
  type: string;
  timestamp_age_days: number;
  source_trust?: number;
  source_conflict?: number;
  downstream_count?: number;
}

export interface PreflightResult {
  omega_mem_final: number;
  recommended_action: "USE_MEMORY" | "WARN" | "ASK_USER" | "BLOCK";
  assurance_score: number;
  explainability_note: string;
  component_breakdown: Record<string, number>;
}

export type ActionType =
  | "informational"
  | "reversible"
  | "irreversible"
  | "destructive";

export type Domain =
  | "general"
  | "customer_support"
  | "coding"
  | "legal"
  | "fintech"
  | "medical";

export interface PreflightRequest {
  memory_state: MemoryEntry[];
  action_type?: ActionType;
  domain?: Domain;
  agent_id?: string;
  task_id?: string;
}

export class SgraalClient {
  private readonly apiKey: string;
  private readonly baseUrl: string;

  constructor(apiKey?: string, baseUrl?: string) {
    this.apiKey = apiKey ?? process.env.SGRAAL_API_KEY ?? "";
    this.baseUrl = baseUrl ?? process.env.SGRAAL_API_URL ?? "https://api.sgraal.com";

    if (!this.apiKey) {
      throw new Error(
        "Sgraal API key required. Set SGRAAL_API_KEY environment variable or pass it to the constructor."
      );
    }
  }

  async preflight(request: PreflightRequest): Promise<PreflightResult> {
    const res = await fetch(`${this.baseUrl}/v1/preflight`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${this.apiKey}`,
      },
      body: JSON.stringify({
        memory_state: request.memory_state,
        action_type: request.action_type ?? "reversible",
        domain: request.domain ?? "general",
        agent_id: request.agent_id,
        task_id: request.task_id,
      }),
    });

    if (!res.ok) {
      const body = await res.text();
      throw new Error(`Sgraal preflight failed (${res.status}): ${body}`);
    }

    return res.json() as Promise<PreflightResult>;
  }
}
