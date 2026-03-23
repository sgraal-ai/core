import { MOCK_AGENTS } from "./lib/mock-data";
import { AgentCard } from "./components/AgentCard";

export default function DashboardHome() {
  const total = MOCK_AGENTS.length;
  const blocked = MOCK_AGENTS.filter((a) => a.recommended_action === "BLOCK").length;
  const warned = MOCK_AGENTS.filter((a) => ["WARN", "ASK_USER"].includes(a.recommended_action)).length;
  const healthy = MOCK_AGENTS.filter((a) => a.recommended_action === "USE_MEMORY").length;
  const avgOmega = Math.round(MOCK_AGENTS.reduce((s, a) => s + a.omega_mem_final, 0) / total * 10) / 10;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Decision Readiness Dashboard</h1>
      <p className="text-muted text-sm mb-8">Fleet-wide memory governance overview</p>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-10">
        <div className="bg-surface border border-surface-light rounded-xl p-5">
          <p className="text-3xl font-bold">{total}</p>
          <p className="text-xs text-muted mt-1">Total Agents</p>
        </div>
        <div className="bg-surface border border-green-400/20 rounded-xl p-5">
          <p className="text-3xl font-bold text-green-400">{healthy}</p>
          <p className="text-xs text-muted mt-1">Healthy (USE)</p>
        </div>
        <div className="bg-surface border border-yellow-400/20 rounded-xl p-5">
          <p className="text-3xl font-bold text-yellow-400">{warned}</p>
          <p className="text-xs text-muted mt-1">Warning (WARN/ASK)</p>
        </div>
        <div className="bg-surface border border-red-400/20 rounded-xl p-5">
          <p className="text-3xl font-bold text-red-400">{blocked}</p>
          <p className="text-xs text-muted mt-1">Blocked (BLOCK)</p>
        </div>
      </div>

      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Agent Fleet</h2>
        <span className="text-xs text-muted font-mono">Avg Ω_MEM: {avgOmega}</span>
      </div>

      <div className="grid gap-4">
        {MOCK_AGENTS.map((agent) => (
          <AgentCard key={agent.id} agent={agent} />
        ))}
      </div>
    </div>
  );
}
