"use client";

import { useState, useEffect } from "react";
import type { Agent } from "./lib/mock-data";
import { MOCK_AGENTS } from "./lib/mock-data";
import { DEMO_FLEET } from "./lib/demo-fleet";
import { fetchFleet } from "./lib/api-client";
import { AgentCard } from "./components/AgentCard";
import { SettingsPanel } from "./components/SettingsPanel";

export default function DashboardHome() {
  const [agents, setAgents] = useState<Agent[]>(MOCK_AGENTS);
  const [isLive, setIsLive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);

  useEffect(() => {
    const apiKey = localStorage.getItem("sgraal_api_key") ?? "";
    const apiUrl = localStorage.getItem("sgraal_api_url") ?? "https://api.sgraal.com";

    if (!apiKey) {
      setAgents(MOCK_AGENTS);
      setIsLive(false);
      return;
    }

    setLoading(true);
    fetchFleet(DEMO_FLEET, apiKey, apiUrl)
      .then(({ agents: liveAgents, errors: errs }) => {
        if (liveAgents.length > 0) {
          setAgents(liveAgents);
          setIsLive(true);
        }
        setErrors(errs);
      })
      .catch(() => {
        setAgents(MOCK_AGENTS);
        setIsLive(false);
      })
      .finally(() => setLoading(false));
  }, []);

  const total = agents.length;
  const blocked = agents.filter((a) => a.recommended_action === "BLOCK").length;
  const warned = agents.filter((a) => ["WARN", "ASK_USER"].includes(a.recommended_action)).length;
  const healthy = agents.filter((a) => a.recommended_action === "USE_MEMORY").length;
  const avgOmega = total > 0 ? Math.round(agents.reduce((s, a) => s + a.omega_mem_final, 0) / total * 10) / 10 : 0;

  return (
    <div>
      <div className="flex items-start justify-between mb-1">
        <div>
          <h1 className="text-2xl font-bold">Decision Readiness Dashboard</h1>
          <p className="text-muted text-sm mb-4">Fleet-wide memory governance overview</p>
        </div>
        <SettingsPanel onSave={() => window.location.reload()} />
      </div>

      {!isLive && !loading && (
        <div className="bg-gold/10 border border-gold/30 rounded-lg px-4 py-3 mb-6 text-sm text-gold">
          Showing mock data. Enter your API key in Settings (gear icon) to see live data.
        </div>
      )}

      {isLive && (
        <div className="bg-green-400/10 border border-green-400/30 rounded-lg px-4 py-3 mb-6 text-sm text-green-400 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-green-400 inline-block" />
          Live — connected to Sgraal API
        </div>
      )}

      {loading && (
        <div className="bg-surface border border-surface-light rounded-lg px-4 py-3 mb-6 text-sm text-muted">
          Loading live fleet data...
        </div>
      )}

      {errors.length > 0 && (
        <div className="bg-red-400/10 border border-red-400/30 rounded-lg px-4 py-3 mb-6 text-sm text-red-400">
          {errors.map((e, i) => <p key={i}>{e}</p>)}
        </div>
      )}

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

      {/* Quick Actions */}
      <div className="flex gap-3 mb-6">
        <a href="/tutorial" className="bg-gold text-background text-sm font-semibold px-4 py-2 rounded hover:bg-gold-dim transition">Start Tutorial</a>
        <a href="/code-generator" className="bg-surface border border-surface-light text-sm px-4 py-2 rounded hover:bg-surface-light transition">Code Generator</a>
      </div>

      {/* Stability Overview */}
      {(() => {
        const avgStability = total > 0 ? agents.reduce((s, a) => s + (a.stability_score?.score ?? 0), 0) / total : 0;
        const avgRTotal = total > 0 ? agents.reduce((s, a) => s + (a.r_total_normalized ?? 0), 0) / total : 0;
        const stabColor = avgStability > 0.7 ? "text-green-400" : avgStability >= 0.4 ? "text-yellow-400" : "text-red-400";
        const rColor = avgRTotal > 3 ? "bg-red-400" : avgRTotal > 1.5 ? "bg-yellow-400" : "bg-green-400";
        return (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-10">
            <div className="bg-surface border border-surface-light rounded-xl p-5">
              <p className="text-xs text-muted mb-2">StabilityScore (fleet avg)</p>
              <p className={`text-4xl font-bold ${stabColor}`}>{(avgStability * 100).toFixed(0)}%</p>
              <p className="text-xs text-muted mt-1">{avgStability > 0.7 ? "Stable" : avgStability >= 0.4 ? (isLive ? "Degrading" : "Demo mode") : "Critical"}</p>
            </div>
            <div className="bg-surface border border-surface-light rounded-xl p-5">
              <p className="text-xs text-muted mb-2 flex items-center gap-1">
                R_total (fleet avg, 0-5 scale)
                <span className="relative group cursor-help">
                  <span className="inline-flex items-center justify-center w-3.5 h-3.5 rounded-full border border-muted text-[9px] font-bold text-muted">?</span>
                  <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 w-52 bg-surface-light text-foreground text-[11px] leading-tight rounded-md px-2.5 py-2 opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity shadow-lg z-10">Reliability score across all memory entries. Scale: 0 (unreliable) to 5 (fully reliable).</span>
                </span>
              </p>
              <p className="text-2xl font-bold font-mono mb-2">{avgRTotal.toFixed(2)}</p>
              <div className="w-full h-2 bg-surface-light rounded-full overflow-hidden">
                <div className={`h-full ${rColor} rounded-full transition-all`} style={{ width: `${Math.min(100, avgRTotal / 5 * 100)}%` }} />
              </div>
            </div>
          </div>
        );
      })()}

      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Agent Fleet</h2>
        <span className="text-xs text-muted font-mono">Avg Ω_MEM: {avgOmega}</span>
      </div>

      <div className="grid gap-4">
        {agents.map((agent) => (
          <AgentCard key={agent.id} agent={agent} />
        ))}
      </div>
    </div>
  );
}
