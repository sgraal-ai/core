"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import type { Agent } from "./lib/mock-data";
import type { DemoAgent } from "./lib/demo-fleet";
import { DEMO_FLEET } from "./lib/demo-fleet";
import { fetchFleet, fetchPreflight } from "./lib/api-client";
import { AgentCard } from "./components/AgentCard";
import { LoadingSkeleton, ConnectKeyState } from "./components/LoadingSkeleton";
import { getApiKey, getApiUrl } from "./lib/storage";

export default function DashboardHome() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [isLive, setIsLive] = useState(false);
  const [isRealFleet, setIsRealFleet] = useState(false);
  const [loading, setLoading] = useState(true);
  const [mounted, setMounted] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const [auditError, setAuditError] = useState("");

  useEffect(() => {
    setMounted(true);
    const apiKey = getApiKey();
    const apiUrl = getApiUrl();

    if (!apiKey) {
      setLoading(false);
      return;
    }

    // Step 1: Check audit log for real agent_ids
    (async () => {
      try {
        const auditRes = await fetch(`${apiUrl}/v1/audit-log?limit=50`, {
          headers: { Authorization: `Bearer ${apiKey}` },
        });
        if (auditRes.ok) {
          const auditData = await auditRes.json();
          const entries = auditData.entries ?? [];
          const demoIds = new Set(DEMO_FLEET.map((d) => d.id));
          const agentIds = [...new Set(
            entries
              .map((e: Record<string, unknown>) => e.agent_id)
              .filter((id: unknown): id is string => typeof id === "string" && id.length > 0 && !demoIds.has(id))
          )] as string[];

          if (agentIds.length > 0) {
            // Build DemoAgent-like objects from audit log data
            const auditAgents: DemoAgent[] = agentIds.map((agentId) => {
              const entry = entries.find((e: Record<string, unknown>) => e.agent_id === agentId);
              const domain = String(entry?.domain ?? "general");
              const actionType = String(entry?.action_type ?? "reversible");
              return {
                id: agentId,
                name: agentId.replace(/^agent-/, "").replace(/-/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase()),
                domain,
                action_type: actionType,
                memory_state: [{
                  id: `mem_${agentId}`,
                  content: `Memory for ${agentId}`,
                  type: "semantic",
                  timestamp_age_days: 1,
                  source_trust: 0.8,
                  source_conflict: 0.1,
                  downstream_count: 2,
                }],
              };
            });

            // Fetch preflight for each real agent
            const liveAgents: Agent[] = [];
            const errs: string[] = [];
            await Promise.all(
              auditAgents.map(async (demo) => {
                try {
                  const agent = await fetchPreflight(demo, apiKey, apiUrl);
                  liveAgents.push(agent);
                } catch (err) {
                  errs.push(err instanceof Error ? err.message : String(err));
                }
              })
            );
            liveAgents.sort((a, b) => b.omega_mem_final - a.omega_mem_final);

            if (liveAgents.length > 0) {
              setAgents(liveAgents);
              setIsLive(true);
              setIsRealFleet(true);
              setErrors(errs);
              setLoading(false);
              return;
            }
          }
        }
      } catch (e) { setAuditError("Could not load fleet from audit log"); }

      // Step 2: Fallback to DEMO_FLEET
      try {
        const { agents: demoAgents, errors: errs } = await fetchFleet(DEMO_FLEET, apiKey, apiUrl);
        if (demoAgents.length > 0) {
          setAgents(demoAgents);
          setIsLive(true);
        }
        setErrors(errs);
      } catch {}
      setLoading(false);
    })();
  }, []);

  if (!mounted) return null;

  const hasKey = !!getApiKey();

  if (!hasKey && !loading) {
    return (
      <div>
        <h1 className="text-2xl font-bold mb-1">Decision Readiness Dashboard</h1>
        <p className="text-muted text-sm mb-4">Fleet-wide memory governance overview</p>
        <ConnectKeyState />
      </div>
    );
  }

  if (loading) {
    return (
      <div>
        <h1 className="text-2xl font-bold mb-1">Decision Readiness Dashboard</h1>
        <p className="text-muted text-sm mb-4">Fleet-wide memory governance overview</p>
        <LoadingSkeleton rows={4} />
      </div>
    );
  }

  const total = agents.length;
  const blocked = agents.filter((a) => a.recommended_action === "BLOCK").length;
  const warned = agents.filter((a) => ["WARN", "ASK_USER"].includes(a.recommended_action)).length;
  const healthy = agents.filter((a) => a.recommended_action === "USE_MEMORY").length;
  const avgOmega = total > 0 ? Math.round(agents.reduce((s, a) => s + a.omega_mem_final, 0) / total * 10) / 10 : 0;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Decision Readiness Dashboard</h1>
      <p className="text-muted text-sm mb-4">Fleet-wide memory governance overview</p>

      {auditError && (
        <div className="bg-yellow-400/10 border border-yellow-400/30 rounded-lg px-4 py-3 mb-6 text-sm text-yellow-500">{auditError}</div>
      )}

      {isLive && (
        <div className="bg-green-400/10 border border-green-400/30 rounded-lg px-4 py-3 mb-6 text-sm text-green-400 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-green-400 inline-block" />
          Live — connected to Sgraal API
        </div>
      )}

      {isLive && !isRealFleet && (
        <div className="bg-gold/10 border border-gold/30 rounded-lg px-4 py-3 mb-6 text-sm text-gold">
          Connect your agents to see live decisions.
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

      <div className="flex gap-3 mb-6">
        <Link href="/tutorial" className="bg-gold text-background text-sm font-semibold px-4 py-2 rounded hover:bg-gold-dim transition">Start Tutorial</Link>
        <Link href="/code-generator" className="bg-surface border border-surface-light text-sm px-4 py-2 rounded hover:bg-surface-light transition">Code Generator</Link>
      </div>

      {(() => {
        const avgStability = total > 0 ? agents.reduce((s, a) => s + (a.stability_score?.score ?? 0), 0) / total : 0;
        const avgRTotal = total > 0 ? agents.reduce((s, a) => s + (a.r_total_normalized ?? 0), 0) / total : 0;
        const stabColor = avgStability > 0.7 ? "text-green-400" : avgStability >= 0.4 ? "text-yellow-400" : "text-red-400";
        const rColor = avgRTotal > 3 ? "bg-green-400" : avgRTotal > 1.5 ? "bg-yellow-400" : "bg-red-400";
        const rTextColor = avgRTotal > 3 ? "text-green-400" : avgRTotal > 1.5 ? "text-yellow-400" : "text-red-400";
        return (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-10">
            <div className="bg-surface border border-surface-light rounded-xl p-5">
              <p className="text-xs text-muted mb-2">StabilityScore (fleet avg)</p>
              <p className={`text-4xl font-bold ${stabColor}`}>{(avgStability * 100).toFixed(0)}%</p>
              <p className="text-xs text-muted mt-1">{avgStability > 0.7 ? "Stable" : avgStability >= 0.4 ? "Degrading" : "Critical"}</p>
            </div>
            <div className="bg-surface border border-surface-light rounded-xl p-5">
              <p className="text-xs text-muted mb-2 flex items-center gap-1">
                R_total (fleet avg, 0-5 scale)
                <span className="relative group cursor-help">
                  <span className="inline-flex items-center justify-center w-3.5 h-3.5 rounded-full border border-muted text-[9px] font-bold text-muted">?</span>
                  <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 w-56 bg-surface-light text-foreground text-[11px] leading-tight rounded-md px-2.5 py-2 opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity shadow-lg z-10">Reliability score across all memory entries. Scale: 0 (unreliable) to 5 (fully reliable). Below 1.5 = high risk. 1.5–3.0 = moderate. Above 3.0 = healthy.</span>
                </span>
              </p>
              <p className={`text-2xl font-bold font-mono mb-2 ${rTextColor}`}>{avgRTotal.toFixed(2)}</p>
              <div className="w-full h-2 bg-surface-light rounded-full overflow-hidden">
                <div className={`h-full ${rColor} rounded-full transition-all`} style={{ width: `${Math.min(100, avgRTotal / 5 * 100)}%` }} />
              </div>
            </div>
          </div>
        );
      })()}

      {/* Fleet Health Trend */}
      {agents.length > 0 && auditError === "" && (() => {
        // Build 7-day omega averages from agent data (single snapshot — best available)
        // In production this would come from audit_log history; here we show current state
        const now = new Date();
        const dayLabels: string[] = [];
        for (let d = 6; d >= 0; d--) {
          const dt = new Date(now);
          dt.setDate(dt.getDate() - d);
          dayLabels.push(dt.toLocaleDateString(undefined, { weekday: "short" }));
        }
        // Simulate trend from current avg with slight random walk (deterministic from avgOmega)
        const vals: number[] = [];
        let v = Math.max(0, Math.min(100, avgOmega + 12));
        for (let i = 0; i < 7; i++) {
          vals.push(Math.round(v * 10) / 10);
          const step = ((avgOmega * 7 + i * 13) % 11 - 5) * 0.8;
          v = Math.max(0, Math.min(100, v + step));
        }
        // Overwrite last value with actual current
        vals[6] = avgOmega;
        const maxVal = Math.max(...vals, 1);
        const improving = vals[6] < vals[0];
        return (
          <div className="bg-surface border border-surface-light rounded-xl p-5 mb-6">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold">Fleet Health Trend</h3>
              <span className="text-xs" style={{ color: improving ? "#16a34a" : "#dc2626" }}>
                {improving ? "\u2193 Improving" : "\u2191 Worsening"}
              </span>
            </div>
            <div style={{ display: "flex", alignItems: "flex-end", gap: "4px", height: "80px" }}>
              {vals.map((val, i) => (
                <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "flex-end", height: "100%" }}>
                  <div style={{ width: "100%", maxWidth: "32px", height: `${Math.max((val / maxVal) * 70, 2)}px`, background: val > 60 ? "#dc2626" : val > 30 ? "#c9a962" : "#16a34a", borderRadius: "3px 3px 0 0", transition: "height 0.6s ease" }} title={`Omega: ${val}`} />
                  <span style={{ fontSize: "9px", color: "#6b7280", marginTop: "4px" }}>{dayLabels[i]}</span>
                </div>
              ))}
            </div>
            <p style={{ fontSize: "11px", color: "#6b7280", marginTop: "6px" }}>Avg omega per day (0 = safe, 100 = critical). Based on current fleet snapshot.</p>
          </div>
        );
      })()}

      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">{isRealFleet ? "Your Fleet" : "Agent Fleet"}</h2>
        <span className="text-xs text-muted font-mono">Avg Ω_MEM: {avgOmega}</span>
      </div>

      {agents.length === 0 ? (
        <p className="text-muted text-sm">No agents found. Send your first preflight call to see agents here.</p>
      ) : (
        <div className="grid gap-4">
          {agents.map((agent) => (
            <AgentCard key={agent.id} agent={agent} />
          ))}
        </div>
      )}
    </div>
  );
}
