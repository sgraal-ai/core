import Link from "next/link";
import type { Agent } from "../lib/mock-data";
import { OmegaMeter } from "./OmegaMeter";

const COMPONENT_LABELS: Record<string, string> = {
  s_freshness: "stale memory", s_drift: "memory drift", s_provenance: "untrusted source",
  r_recall: "recall failure", s_propagation: "high dependency risk", r_encode: "encoding issue",
  s_interference: "data conflict", s_recovery: "slow recovery", r_belief: "low confidence",
  s_relevance: "intent drift",
};
const REPAIR_LABELS: Record<string, string> = {
  REFETCH: "Refresh from source", VERIFY_WITH_SOURCE: "Verify with source",
  REBUILD_WORKING_SET: "Rebuild memory set", WAIT: "Wait for self-recovery",
  SLA_WARNING: "Review SLA", CHAOS_WARNING: "Stabilize drift",
  SOFT_HEAL: "Apply light fix", FULL_HEAL: "Full healing cycle",
  EMERGENCY_HEAL: "Emergency heal",
};

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
      className="border border-surface-light bg-surface rounded-xl p-6 hover:border-gold/30 hover:shadow-md transition flex gap-5 items-center relative"
    >
      {agent.omega_mem_final > 70 && (
        <span style={{ position: "absolute", top: "10px", right: "12px", background: "#fee2e2", color: "#dc2626", border: "1px solid #fecaca", borderRadius: "4px", padding: "1px 8px", fontSize: "11px", fontWeight: 700 }}>CRITICAL</span>
      )}
      {agent.omega_mem_final >= 40 && agent.omega_mem_final <= 70 && (
        <span style={{ position: "absolute", top: "10px", right: "12px", background: "#fef3c7", color: "#92400e", border: "1px solid #fde68a", borderRadius: "4px", padding: "1px 8px", fontSize: "11px", fontWeight: 700 }}>WARNING</span>
      )}
      <OmegaMeter value={agent.omega_mem_final} size={90} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-3 mb-1">
          <h3 className="font-semibold truncate">{agent.name}</h3>
          <span className={`text-xs font-mono px-2 py-0.5 rounded ${style.bg} ${style.text}`}>
            {style.label}
          </span>
        </div>
        <p className="text-xs text-muted font-mono mb-2">{agent.id}</p>
        {agent.recommended_action === "BLOCK" && (() => {
          const cb = agent.component_breakdown ?? {};
          const top = Object.entries(cb).sort(([,a],[,b]) => b - a)[0];
          const reason = top ? (COMPONENT_LABELS[top[0]] ?? top[0].replace(/_/g, " ")) : "high risk";
          const rp = agent.repair_plan ?? [];
          const fix = rp.length > 0 ? (REPAIR_LABELS[rp[0].action] ?? rp[0].action) : "Review manually";
          return (
            <p className="text-xs mb-2" style={{ color: "#6b7280" }}>
              Reason: <span style={{ color: "#dc2626" }}>{reason}</span> → Fix: <span style={{ color: "#c9a962" }}>{fix}</span>
            </p>
          );
        })()}
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
        <p className="text-xs mt-2" style={{ color: "#c9a962" }}>View details &rarr;</p>
      </div>
    </Link>
  );
}
