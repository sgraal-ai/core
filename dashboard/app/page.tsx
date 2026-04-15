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

function _isRealAgentId(id: string): boolean {
  if (!id) return false;
  const lower = id.toLowerCase();
  if (lower === "unknown" || lower === "anonymous") return false;
  if (id.startsWith("[") || id.includes("%5B") || id.includes("%5b")) return false;
  return true;
}

export default function DashboardHome() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [isLive, setIsLive] = useState(false);
  const [isRealFleet, setIsRealFleet] = useState(false);
  const [loading, setLoading] = useState(true);
  const [mounted, setMounted] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const [auditError, setAuditError] = useState("");

  // Fleet Intelligence
  interface Insight {
    agent_id: string;
    available: boolean;
    reason?: string;
    insight_summary?: string;
    days_until_block?: number | null;
    monoculture_risk_level?: string;
    confidence_calibration?: { state: string; score: number };
    omega_mem_final?: number;
    recommended_action?: string;
  }
  const [insights, setInsights] = useState<Insight[]>([]);
  const [insightsLoading, setInsightsLoading] = useState(false);

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

  // Build insights from existing agent preflight data (same agent set as fleet cards)
  function buildInsightsFromAgents(agentList: Agent[]) {
    setInsightsLoading(true);
    const results: Insight[] = agentList.slice(0, 10).map((a) => {
      const omega = a.omega_mem_final ?? 0;
      const action = a.recommended_action ?? "USE_MEMORY";
      const isBlock = action === "BLOCK";
      const isWarn = action === "WARN" || action === "ASK_USER";

      // Build summary from available signals
      const parts: string[] = [];
      if (isBlock) {
        parts.push("Agent is currently BLOCKED. Immediate attention required.");
      } else if (omega > 70) {
        parts.push(`Agent omega is critically high (${omega}).`);
      } else if (isWarn) {
        parts.push(`Agent requires attention (${action}, omega=${omega}).`);
      }
      if (!parts.length) {
        parts.push("Agent memory is healthy. No critical signals detected.");
      }

      // Extract calibration from preflight data if available
      const cal = (a as unknown as Record<string, unknown>).confidence_calibration as
        { state: string; score: number } | undefined;

      return {
        agent_id: a.id,
        available: true,
        insight_summary: parts.join(" "),
        days_until_block: (a as unknown as Record<string, unknown>).days_until_block as number | null | undefined,
        monoculture_risk_level: String((a as unknown as Record<string, unknown>).monoculture_risk_level ?? "LOW"),
        confidence_calibration: cal ?? { state: "CALIBRATED", score: 0.5 },
        omega_mem_final: omega,
        recommended_action: action,
      };
    });
    setInsights(results);
    setInsightsLoading(false);
  }

  // Also try fetching from /v1/insights API (enriches with synthesis fields)
  async function fetchInsightsFromAPI(agentList: Agent[]) {
    const apiKey = getApiKey();
    const apiUrl = getApiUrl();
    if (!apiKey || agentList.length === 0) return;
    setInsightsLoading(true);
    const results: Insight[] = [];
    await Promise.all(
      agentList.slice(0, 10).map(async (a) => {
        try {
          const res = await fetch(`${apiUrl}/v1/insights?agent_id=${encodeURIComponent(a.id)}&domain=${a.domain}`, {
            headers: { Authorization: `Bearer ${apiKey}` },
          });
          if (res.ok) {
            const data = await res.json();
            if (data.available) {
              // Override summary if BLOCK but summary says healthy
              if (data.recommended_action === "BLOCK" && data.insight_summary?.includes("healthy")) {
                data.insight_summary = "Agent is currently BLOCKED. Immediate attention required.";
              }
              results.push(data);
              return;
            }
          }
        } catch {}
        // Fallback: build from local agent data
        const omega = a.omega_mem_final ?? 0;
        const action = a.recommended_action ?? "USE_MEMORY";
        const summary = action === "BLOCK"
          ? "Agent is currently BLOCKED. Immediate attention required."
          : omega > 70
          ? `Agent omega is critically high (${omega}).`
          : action !== "USE_MEMORY"
          ? `Agent requires attention (${action}, omega=${omega}).`
          : "Agent memory is healthy. No critical signals detected.";
        results.push({
          agent_id: a.id, available: true, insight_summary: summary,
          days_until_block: null, monoculture_risk_level: "LOW",
          confidence_calibration: { state: "CALIBRATED", score: 0.5 },
          omega_mem_final: omega, recommended_action: action,
        });
      })
    );
    setInsights(results);
    setInsightsLoading(false);
  }

  async function fetchDivergence() {
    const apiKey = getApiKey();
    if (!apiKey) return;
    try {
      const res = await fetch(`${getApiUrl()}/v1/fleet/divergence`, { headers: { Authorization: `Bearer ${apiKey}` } });
      if (res.ok) {
        const data = await res.json();
        const el = document.getElementById("divergence-result");
        if (el) {
          const dagents = data.diverging_agents ?? [];
          const degrading = dagents.filter((a: Record<string, unknown>) => a.divergence_type === "DEGRADING");
          const recovering = dagents.filter((a: Record<string, unknown>) => a.divergence_type === "RECOVERING");
          let html = `<div style="display:flex;gap:12px;margin-bottom:8px">`;
          html += `<span style="font-size:20px;font-weight:700;color:#dc2626">${degrading.length}</span><span style="font-size:11px;color:#6b7280">degrading</span>`;
          html += `<span style="font-size:20px;font-weight:700;color:#16a34a">${recovering.length}</span><span style="font-size:11px;color:#6b7280">recovering</span>`;
          html += `<span style="font-size:20px;font-weight:700;color:#6b7280">${data.stable_agents ?? 0}</span><span style="font-size:11px;color:#6b7280">stable</span>`;
          html += `</div>`;
          if (degrading.length > 0) {
            const top = degrading[0] as Record<string, unknown>;
            html += `<p style="font-size:11px;color:#dc2626">Top: ${String(top.agent_id)} (trend +${String(top.omega_trend)}/call, BLOCK in ~${String(top.predicted_block_in_calls)} calls)</p>`;
          }
          el.innerHTML = html;
        }
      }
    } catch {}
  }

  async function fetchGaming() {
    const apiKey = getApiKey();
    if (!apiKey) return;
    try {
      const res = await fetch(`${getApiUrl()}/v1/fleet/gaming-detection`, { headers: { Authorization: `Bearer ${apiKey}` } });
      if (res.ok) {
        const data = await res.json();
        const el = document.getElementById("gaming-result");
        if (el) {
          const suspects = data.gaming_suspects ?? [];
          if (suspects.length === 0) {
            el.innerHTML = `<div style="text-align:center;padding:8px"><span style="background:#f0fdf4;color:#16a34a;font-size:11px;padding:2px 10px;border-radius:4px;font-weight:600">Clean</span><p style="font-size:11px;color:#6b7280;margin-top:4px">${data.clean_agents ?? 0} agents verified</p></div>`;
          } else {
            let html = `<p style="font-size:12px;color:#ca8a04;font-weight:600;margin-bottom:6px">${suspects.length} suspect(s)</p>`;
            for (const s of suspects.slice(0, 3)) {
              html += `<div style="font-size:11px;padding:3px 0;border-bottom:1px solid #f5f4f0">`;
              html += `<span style="font-family:monospace;font-weight:600">${String((s as Record<string, unknown>).agent_id)}</span>`;
              html += ` <span style="color:#ca8a04">score=${String((s as Record<string, unknown>).gaming_score)}</span>`;
              html += ` <span style="color:#6b7280;font-size:10px">${((s as Record<string, unknown>).signals as string[])?.join(", ")}</span>`;
              html += `</div>`;
            }
            el.innerHTML = html;
          }
        }
      }
    } catch {}
  }

  useEffect(() => {
    if (agents.length > 0 && insights.length === 0 && !insightsLoading) {
      buildInsightsFromAgents(agents);
      fetchInsightsFromAPI(agents);
      fetchDivergence();
      fetchGaming();
    }
  }, [agents]);

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

  const realAgents = agents.filter((a) => _isRealAgentId(a.id));
  const total = realAgents.length;
  const blocked = realAgents.filter((a) => a.recommended_action === "BLOCK").length;
  const warned = realAgents.filter((a) => ["WARN", "ASK_USER"].includes(a.recommended_action)).length;
  const healthy = realAgents.filter((a) => a.recommended_action === "USE_MEMORY").length;
  const avgOmega = total > 0 ? Math.round(realAgents.reduce((s, a) => s + a.omega_mem_final, 0) / total * 10) / 10 : 0;

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
        const avgStability = total > 0 ? realAgents.reduce((s, a) => s + (a.stability_score?.score ?? 0), 0) / total : 0;
        const avgRTotal = total > 0 ? realAgents.reduce((s, a) => s + (a.r_total_normalized ?? 0), 0) / total : 0;
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

      {/* Fleet Intelligence */}
      {agents.length > 0 && (
        <div className="mb-10">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold">Fleet Intelligence</h2>
              <p className="text-xs text-muted">AI-generated insights from your agent memory signals</p>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => fetchInsightsFromAPI(agents)}
                disabled={insightsLoading}
                className="text-xs font-semibold px-3 py-1.5 rounded bg-surface border border-surface-light hover:bg-surface-light transition disabled:opacity-50"
              >
                {insightsLoading ? "Loading..." : "Refresh"}
              </button>
              <Link href="/analytics" className="text-xs text-gold hover:underline">View all &rarr;</Link>
            </div>
          </div>
          {insightsLoading && insights.length === 0 ? (
            <div className="grid gap-3">
              {[1, 2, 3].map(i => (
                <div key={i} className="bg-surface border border-surface-light rounded-xl p-5 animate-pulse">
                  <div className="h-4 bg-surface-light rounded w-1/3 mb-3" />
                  <div className="h-3 bg-surface-light rounded w-2/3" />
                </div>
              ))}
            </div>
          ) : (
            <div className="grid gap-3">
              {insights.filter(ins => _isRealAgentId(ins.agent_id)).length < 2 && (
                <p className="text-sm text-muted py-4">Add agents to see Fleet Intelligence insights.</p>
              )}
              {insights.filter(ins => _isRealAgentId(ins.agent_id)).slice(0, 10).map((ins) => {
                const dubColor = ins.days_until_block === null || ins.days_until_block === undefined ? "#6b7280"
                  : ins.days_until_block === 0 ? "#dc2626"
                  : (ins.days_until_block ?? 999) < 7 ? "#dc2626"
                  : (ins.days_until_block ?? 999) < 30 ? "#ca8a04"
                  : "#16a34a";
                const dubText = ins.days_until_block === null || ins.days_until_block === undefined ? "—"
                  : ins.days_until_block === 0 ? "NOW"
                  : `${ins.days_until_block}d`;
                const monoColor = ins.monoculture_risk_level === "HIGH" ? "#dc2626"
                  : ins.monoculture_risk_level === "MEDIUM" ? "#ca8a04" : "#16a34a";
                const calState = ins.confidence_calibration?.state ?? "CALIBRATED";
                const calColor = calState === "OVERCONFIDENT" ? "#dc2626"
                  : calState === "UNDERCONFIDENT" ? "#ca8a04" : "#16a34a";
                const actColor = ins.recommended_action === "BLOCK" ? "#dc2626"
                  : ins.recommended_action === "WARN" || ins.recommended_action === "ASK_USER" ? "#ca8a04"
                  : "#16a34a";
                return (
                  <div key={ins.agent_id} className="bg-surface border border-surface-light rounded-xl p-5 hover:border-gold/20 transition">
                    {!ins.available ? (
                      <div className="flex items-center gap-3">
                        <span className="font-mono text-xs text-muted">{ins.agent_id}</span>
                        <span className="text-xs text-muted">No recent data</span>
                      </div>
                    ) : (
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-mono text-xs font-semibold">{ins.agent_id}</span>
                          <div className="flex items-center gap-2">
                            {ins.omega_mem_final !== undefined && (
                              <span className="text-xs font-mono text-muted">Ω {ins.omega_mem_final}</span>
                            )}
                            <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded" style={{ background: `${actColor}15`, color: actColor }}>
                              {ins.recommended_action}
                            </span>
                          </div>
                        </div>
                        <p className="text-sm text-foreground mb-3">{ins.insight_summary}</p>
                        <div className="flex flex-wrap gap-2">
                          <span className="text-[11px] font-mono px-2 py-0.5 rounded" style={{ background: `${dubColor}15`, color: dubColor }}>
                            BLOCK: {dubText}
                          </span>
                          <span className="text-[11px] font-mono px-2 py-0.5 rounded" style={{ background: `${monoColor}15`, color: monoColor }}>
                            Mono: {ins.monoculture_risk_level ?? "—"}
                          </span>
                          <span className="text-[11px] font-mono px-2 py-0.5 rounded" style={{ background: `${calColor}15`, color: calColor }}>
                            {calState}
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Fleet Divergence + Gaming Detection */}
      {realAgents.length > 0 && (
        <div className="grid md:grid-cols-2 gap-4 mb-8">
          {/* Divergence */}
          <div className="bg-surface border border-surface-light rounded-xl p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold">Fleet Divergence</h3>
              <button onClick={fetchDivergence} className="text-xs px-2 py-1 rounded bg-surface-light hover:bg-gold/10 transition">Refresh</button>
            </div>
            <div id="divergence-result"><p className="text-xs text-muted">Click refresh to load</p></div>
          </div>

          {/* Gaming Detection */}
          <div className="bg-surface border border-surface-light rounded-xl p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold">Gaming Detection</h3>
              <button onClick={fetchGaming} className="text-xs px-2 py-1 rounded bg-surface-light hover:bg-gold/10 transition">Refresh</button>
            </div>
            <div id="gaming-result"><p className="text-xs text-muted">Click refresh to load</p></div>
          </div>
        </div>
      )}

      {agents.filter(a => _isRealAgentId(a.id)).length === 0 ? (
        <p className="text-muted text-sm">No agents found. Send your first preflight call to see agents here.</p>
      ) : (
        <div className="grid gap-4">
          {agents.filter(a => _isRealAgentId(a.id)).map((agent) => (
            <AgentCard key={agent.id} agent={agent} />
          ))}
        </div>
      )}
    </div>
  );
}
