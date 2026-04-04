import Link from "next/link";
import type { Agent } from "../lib/mock-data";
import { OmegaMeter } from "./OmegaMeter";

const ACTION_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  USE_MEMORY: { bg: "bg-green-400/10", text: "text-green-400", label: "USE" },
  WARN:       { bg: "bg-yellow-400/10", text: "text-yellow-400", label: "WARN" },
  ASK_USER:   { bg: "bg-orange-400/10", text: "text-orange-400", label: "ASK" },
  BLOCK:      { bg: "bg-red-400/10", text: "text-red-400", label: "BLOCK" },
};

export function AgentCard({ agent }: { agent: Agent }) {
  const style = ACTION_STYLES[agent.recommended_action] ?? ACTION_STYLES.WARN;

  return (
    <Link
      href={`/agent/${agent.id}`}
      className="border border-surface-light bg-surface rounded-xl p-6 hover:border-gold/30 transition flex gap-5 items-center"
    >
      <OmegaMeter value={agent.omega_mem_final} size={90} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-3 mb-1">
          <h3 className="font-semibold truncate">{agent.name}</h3>
          <span className={`text-xs font-mono px-2 py-0.5 rounded ${style.bg} ${style.text}`}>
            {style.label}
          </span>
        </div>
        <p className="text-xs text-muted font-mono mb-2">{agent.id}</p>
        <div className="flex gap-4 text-xs text-muted">
          <span>Assurance: {agent.assurance_score}%</span>
          <span>Domain: {agent.domain}</span>
          {agent.repair_plan.length > 0 && (
            <span className="text-gold">{agent.repair_plan.length} repair actions</span>
          )}
          {agent.at_risk_warnings.length > 0 && (
            <span className="text-red-400">{agent.at_risk_warnings.length} at risk</span>
          )}
          {agent.poisoning_suspected && (
            <span className="text-red-400 font-semibold">&#x26A0; POISONING</span>
          )}
          {agent.tamper_detected && (
            <span className="text-red-400 font-semibold">&#x26A0; TAMPER</span>
          )}
          {agent.hallucination_risk === "high" && (
            <span className="text-orange-400 font-semibold">&#x26A0; HALLUCINATION RISK</span>
          )}
        </div>
      </div>
    </Link>
  );
}
