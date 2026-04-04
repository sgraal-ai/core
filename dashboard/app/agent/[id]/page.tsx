"use client";

import { useState, useEffect, use } from "react";
import Link from "next/link";
import type { Agent } from "../../lib/mock-data";
import { DEMO_FLEET } from "../../lib/demo-fleet";
import { fetchPreflight } from "../../lib/api-client";
import { OmegaMeter } from "../../components/OmegaMeter";
import { ComponentBreakdown } from "../../components/ComponentBreakdown";
import { RepairPlanList } from "../../components/RepairPlanList";
import { AtRiskWarnings } from "../../components/AtRiskWarnings";
import { AdvancedAnalytics } from "../../components/AdvancedAnalytics";
import { DeepAnalytics } from "../../components/DeepAnalytics";
import { LoadingSkeleton, ConnectKeyState } from "../../components/LoadingSkeleton";
import { getApiKey, getApiUrl } from "../../lib/storage";

const ACTION_STYLES: Record<string, { bg: string; text: string }> = {
  USE_MEMORY: { bg: "bg-green-400/10", text: "text-green-400" },
  WARN:       { bg: "bg-yellow-400/10", text: "text-yellow-400" },
  ASK_USER:   { bg: "bg-orange-400/10", text: "text-orange-400" },
  BLOCK:      { bg: "bg-red-400/10", text: "text-red-400" },
};

export default function AgentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [agent, setAgent] = useState<Agent | null>(null);
  const [mounted, setMounted] = useState(false);
  const [loading, setLoading] = useState(true);

  // Explain
  const [explainText, setExplainText] = useState<Record<string, string> | null>(null);
  const [explainLoading, setExplainLoading] = useState(false);
  const [explainError, setExplainError] = useState("");

  // Decision Twin
  const [twinResult, setTwinResult] = useState<Record<string, unknown> | null>(null);
  const [twinLoading, setTwinLoading] = useState(false);
  const [twinError, setTwinError] = useState("");
  const [twinOpen, setTwinOpen] = useState(false);

  // Time Machine
  const [snapshots, setSnapshots] = useState<Array<Record<string, unknown>>>([]);
  const [snapshotLoading, setSnapshotLoading] = useState(false);
  const [snapshotError, setSnapshotError] = useState("");
  const [snapshotMsg, setSnapshotMsg] = useState("");

  // Forensics
  const [forensicsData, setForensicsData] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    setMounted(true);
    const apiKey = getApiKey();
    const apiUrl = getApiUrl();

    if (!apiKey) {
      setLoading(false);
      return;
    }

    const demo = DEMO_FLEET.find((d) => d.id === id);
    if (!demo) {
      setLoading(false);
      return;
    }

    fetchPreflight(demo, apiKey, apiUrl)
      .then(async (liveAgent) => {
        setAgent(liveAgent);
        // Auto-load explanation
        try {
          const explainRes = await fetch(`${apiUrl}/v1/explain`, {
            method: "POST",
            headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
            body: JSON.stringify({ preflight_result: liveAgent, audience: "developer", language: "en" }),
          });
          if (explainRes.ok) setExplainText(await explainRes.json());
        } catch {}
        // Auto-load forensics for BLOCK decisions
        if (liveAgent.recommended_action === "BLOCK") {
          try {
            const forensicsRes = await fetch(`${apiUrl}/v1/forensics/analyze`, {
              method: "POST",
              headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
              body: JSON.stringify({
                agent_id: liveAgent.id,
                incident_type: "block",
                context: { omega: liveAgent.omega_mem_final, decision: "BLOCK", domain: liveAgent.domain },
              }),
            });
            if (forensicsRes.ok) setForensicsData(await forensicsRes.json());
          } catch {}
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [id]);

  if (!mounted) return null;

  const hasKey = !!getApiKey();

  if (!hasKey) {
    return (
      <div>
        <Link href="/" className="text-sm text-muted hover:text-foreground transition mb-6 inline-block">&larr; Back to fleet</Link>
        <ConnectKeyState />
      </div>
    );
  }

  if (loading) {
    return (
      <div>
        <Link href="/" className="text-sm text-muted hover:text-foreground transition mb-6 inline-block">&larr; Back to fleet</Link>
        <LoadingSkeleton rows={5} />
      </div>
    );
  }

  if (!agent) {
    return (
      <div>
        <Link href="/" className="text-sm text-muted hover:text-foreground transition mb-6 inline-block">&larr; Back to fleet</Link>
        <p className="text-muted">Agent not found.</p>
      </div>
    );
  }

  const style = ACTION_STYLES[agent.recommended_action] ?? ACTION_STYLES.WARN;

  return (
    <div>
      <Link href="/" className="text-sm text-muted hover:text-foreground transition mb-6 inline-block">
        &larr; Back to fleet
      </Link>

      <div className="flex flex-col sm:flex-row gap-8 mb-10">
        <OmegaMeter value={agent.omega_mem_final} size={140} />
        <div>
          <h1 className="text-2xl font-bold mb-1">{agent.name}</h1>
          <p className="text-xs text-muted font-mono mb-3">{agent.id}</p>
          <div className="flex flex-wrap gap-3 mb-4">
            <span className={`text-sm font-mono px-3 py-1 rounded ${style.bg} ${style.text}`}>
              {agent.recommended_action}
            </span>
            <span className="text-sm font-mono px-3 py-1 rounded bg-surface-light text-muted">
              {agent.domain}
            </span>
            <span className="text-sm font-mono px-3 py-1 rounded bg-surface-light text-muted">
              GSV: {agent.gsv}
            </span>
            <span className="text-sm font-mono px-3 py-1 rounded bg-surface-light text-muted">
              Healed: {agent.healing_counter}x
            </span>
          </div>
          <div className="flex gap-6 text-sm text-muted">
            <span>Assurance: <strong className="text-foreground">{agent.assurance_score}%</strong></span>
            <span>Profile: <strong className="text-foreground">{agent.compliance_result?.profile_applied ?? "N/A"}</strong></span>
            {agent.compliance_result?.audit_required && (
              <span className="text-red-400 font-mono">AUDIT REQUIRED</span>
            )}
          </div>
        </div>
      </div>

      {(agent.compliance_result?.violations?.length ?? 0) > 0 && (
        <div className="border border-red-400/20 bg-red-400/5 rounded-xl p-5 mb-8">
          <h2 className="text-sm font-semibold text-red-400 mb-3">Compliance Violations</h2>
          {(agent.compliance_result?.violations ?? []).map((v, i) => (
            <div key={i} className="mb-2">
              <span className="text-xs font-mono text-red-400 mr-2">[{v.severity.toUpperCase()}]</span>
              <span className="text-xs font-mono text-gold mr-2">{v.article}</span>
              <span className="text-sm text-foreground/80">{v.description}</span>
            </div>
          ))}
        </div>
      )}

      {agent.recommended_action === "BLOCK" && (
        <div className="border border-red-400/30 bg-red-400/5 rounded-xl p-5 mb-8">
          <h2 className="text-sm font-semibold text-red-400 mb-3 flex items-center gap-2">
            <span>&#x1F6A8;</span> ACTION REQUIRED
          </h2>
          <p className="text-sm text-foreground mb-3">
            Apply <strong>{(agent.repair_plan?.[0] as unknown as Record<string, string>)?.action ?? "EMERGENCY_HEAL"}</strong> → re-run preflight
          </p>
          <p className="text-xs text-muted font-mono">
            Expected result: Omega ~23.6 → USE_MEMORY
          </p>
        </div>
      )}

      {/* Forensics */}
      {agent.recommended_action === "BLOCK" && forensicsData && (
        <div className="bg-surface border border-surface-light rounded-xl p-5 mb-8">
          <h2 className="text-lg font-semibold mb-4">Forensics</h2>
          {String(forensicsData.root_cause ?? "") === "insufficient_data" ? (
            <p className="text-sm text-muted">Forensics requires more preflight history to generate a full incident trace.</p>
          ) : (
            <div className="space-y-3">
              {!!forensicsData.forensics_id && (
                <p className="text-xs text-muted font-mono">{String(forensicsData.forensics_id)}</p>
              )}
              {!!forensicsData.root_cause && (
                <div>
                  <p className="text-xs text-muted uppercase mb-1">Root Cause</p>
                  <p className="text-sm">{String(forensicsData.root_cause)}</p>
                </div>
              )}
              {!!forensicsData.recommendation && (
                <div>
                  <p className="text-xs text-muted uppercase mb-1">Recommendation</p>
                  <p className="text-sm">{String(forensicsData.recommendation)}</p>
                </div>
              )}
              <div className="flex gap-6 text-xs text-muted">
                {Array.isArray(forensicsData.timeline) && (
                  <span>Timeline: <strong className="text-foreground">{String((forensicsData.timeline as unknown[]).length)} events</strong></span>
                )}
                {Array.isArray(forensicsData.contamination_chain) && (
                  <span>Contamination chain: <strong className="text-foreground">{String((forensicsData.contamination_chain as unknown[]).length)} entries</strong></span>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Explain Decision */}
      <div className="mb-8">
        <div className="flex items-center gap-4 mb-4">
          <h2 className="text-lg font-semibold">Explain Decision</h2>
          <button
            onClick={async () => {
              setExplainLoading(true);
              setExplainError("");
              try {
                const res = await fetch(`${getApiUrl()}/v1/explain`, {
                  method: "POST",
                  headers: { Authorization: `Bearer ${getApiKey()}`, "Content-Type": "application/json" },
                  body: JSON.stringify({ preflight_result: agent, audience: "developer", language: "en" }),
                });
                if (res.ok) setExplainText(await res.json());
                else setExplainError(`Error: ${res.status}`);
              } catch (e) { setExplainError(e instanceof Error ? e.message : "Request failed"); }
              setExplainLoading(false);
            }}
            disabled={explainLoading}
            className="text-sm font-semibold px-4 py-1.5 rounded bg-gold text-background hover:bg-gold-dim transition disabled:opacity-50"
          >
            {explainLoading ? "Explaining..." : explainText ? "Refresh explanation" : "Explain this decision"}
          </button>
        </div>
        {explainError && <p className="text-sm text-red-400 mb-2">{explainError}</p>}
        {explainText && (
          <div className="bg-surface border border-surface-light rounded-xl p-5 space-y-3">
            {explainText.summary && (
              <div>
                <p className="text-xs text-muted uppercase mb-1">Summary</p>
                <p className="text-sm">{explainText.summary}</p>
              </div>
            )}
            {explainText.root_cause && (
              <div>
                <p className="text-xs text-muted uppercase mb-1">Root Cause</p>
                <p className="text-sm font-mono">{explainText.root_cause}</p>
              </div>
            )}
            {explainText.recommended_action_human && (
              <div>
                <p className="text-xs text-muted uppercase mb-1">Recommended Action</p>
                <p className="text-sm">{explainText.recommended_action_human}</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Decision Twin */}
      <div className="mb-8">
        <div className="flex items-center gap-4 mb-4">
          <h2 className="text-lg font-semibold">Decision Twin</h2>
          <button
            onClick={async () => {
              setTwinLoading(true);
              setTwinError("");
              setTwinResult(null);
              const headers = { Authorization: `Bearer ${getApiKey()}`, "Content-Type": "application/json" };
              const base = getApiUrl();
              try {
                // Step 1: Start twin simulation
                const demo = DEMO_FLEET.find((d) => d.id === id);
                const memoryState = demo?.memory_state ?? [{
                  id: `mem_${agent.id}`,
                  content: `Memory for ${agent.name}`,
                  type: "fact",
                  domain: agent.domain,
                  timestamp_age_days: 30,
                }];
                console.log("Twin memory_state:", JSON.stringify(memoryState));
                const startRes = await fetch(`${base}/v1/simulate/twin`, {
                  method: "POST", headers,
                  body: JSON.stringify({
                    agent_id: agent.id,
                    memory_state: memoryState,
                    action_type: (agent as unknown as Record<string, unknown>).action_type ?? "irreversible",
                  }),
                });
                if (!startRes.ok) { setTwinError(`Error: ${startRes.status}`); setTwinLoading(false); return; }
                const startData = await startRes.json();
                const jobId = startData.job_id ?? startData.id ?? startData.twin_id;
                if (!jobId) { setTwinResult(startData); setTwinOpen(true); setTwinLoading(false); return; }

                // Step 2: Poll for completion
                for (let i = 0; i < 10; i++) {
                  await new Promise((r) => setTimeout(r, 1000));
                  const pollRes = await fetch(`${base}/v1/simulate/twin/${jobId}`, { headers });
                  if (!pollRes.ok) continue;
                  const pollData = await pollRes.json();
                  const status = pollData.status ?? pollData.state;
                  if (status === "complete" || status === "completed") {
                    setTwinResult(pollData); setTwinOpen(true); setTwinLoading(false); return;
                  }
                  if (status === "failed") {
                    setTwinError("Simulation failed — try with a different memory state.");
                    setTwinLoading(false); return;
                  }
                }
                setTwinError("Simulation timed out after 10 seconds.");
              } catch (e) { setTwinError(e instanceof Error ? e.message : "Request failed"); }
              setTwinLoading(false);
            }}
            disabled={twinLoading}
            className="text-sm font-semibold px-4 py-1.5 rounded bg-gold text-background hover:bg-gold-dim transition disabled:opacity-50"
          >
            {twinLoading ? "Simulating..." : "Run Decision Twin"}
          </button>
        </div>
        {twinError && <p className="text-sm text-red-400 mb-2">{twinError}</p>}
        {twinResult && (
          <div className="bg-surface border border-surface-light rounded-xl overflow-hidden">
            <button onClick={() => setTwinOpen(!twinOpen)} className="w-full text-left px-5 py-3 flex justify-between items-center text-sm font-semibold hover:bg-surface-light transition">
              <span>Twin Result: {String((twinResult as Record<string, unknown>).recommended_action ?? (twinResult as Record<string, unknown>).decision ?? "—")}</span>
              <span className="text-muted">{twinOpen ? "▲" : "▼"}</span>
            </button>
            {twinOpen && (() => {
              const tr = twinResult as Record<string, unknown>;
              const rawScenarios = (tr.result as Record<string, unknown>)?.scenarios ?? tr.scenarios;
              const scenarios = Array.isArray(rawScenarios) ? rawScenarios as Array<Record<string, unknown>> : null;
              const omegaColor = (v: number) => v < 25 ? "#16a34a" : v < 50 ? "#eab308" : v < 75 ? "#f97316" : "#dc2626";
              const actionBadge: Record<string, { bg: string; color: string }> = {
                USE_MEMORY: { bg: "#dcfce7", color: "#16a34a" },
                WARN: { bg: "#fef9c3", color: "#a16207" },
                ASK_USER: { bg: "#ffedd5", color: "#c2410c" },
                BLOCK: { bg: "#fee2e2", color: "#dc2626" },
              };
              const nested = (tr.result as Record<string, unknown>) ?? {};
              const recommended = String(nested.recommended_path ?? tr.recommended_path ?? nested.recommended ?? tr.recommended ?? "");
              return (
                <div className="px-5 pb-5">
                  {scenarios ? (
                    <>
                      <table className="w-full text-sm" style={{ borderCollapse: "collapse" }}>
                        <thead>
                          <tr>
                            {["Scenario", "Omega", "Action", "Risk Delta", "Summary"].map((h) => (
                              <th key={h} className="text-xs text-muted uppercase text-left pb-2 pr-4" style={{ borderBottom: "1px solid #e5e7eb" }}>{h}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {scenarios.map((s, i) => {
                            const omega = Number(s.omega ?? s.omega_mem_final ?? 0);
                            const action = String(s.action ?? s.recommended_action ?? "—");
                            const badge = actionBadge[action];
                            const delta = Number(s.risk_delta ?? s.delta ?? 0);
                            return (
                              <tr key={i}>
                                <td className="py-3 pr-4 text-sm font-semibold" style={{ borderBottom: "1px solid #f5f4f0" }}>
                                  {String(s.name ?? s.scenario ?? `Scenario ${i + 1}`)}
                                  {String(s.name ?? s.scenario ?? "") === String(nested.recommended_path ?? tr.recommended_path ?? "") && String(s.name ?? s.scenario ?? "") !== "" && (
                                    <span className="ml-2 text-xs bg-green-400/10 text-green-400 px-2 py-0.5 rounded font-mono">Recommended</span>
                                  )}
                                </td>
                                <td className="py-3 pr-4 font-mono text-sm font-semibold" style={{ borderBottom: "1px solid #f5f4f0", color: omegaColor(omega) }}>{omega}</td>
                                <td className="py-3 pr-4" style={{ borderBottom: "1px solid #f5f4f0" }}>
                                  {badge ? (
                                    <span style={{ background: badge.bg, color: badge.color, borderRadius: "20px", padding: "2px 10px", fontSize: "12px", fontWeight: 600 }}>{action}</span>
                                  ) : (
                                    <span className="font-mono text-xs">{action}</span>
                                  )}
                                </td>
                                <td className="py-3 pr-4 font-mono text-sm" style={{ borderBottom: "1px solid #f5f4f0", color: delta < 0 ? "#16a34a" : delta > 0 ? "#dc2626" : "#6b7280" }}>{delta > 0 ? `+${delta}` : String(delta)}</td>
                                <td className="py-3 text-xs text-muted" style={{ borderBottom: "1px solid #f5f4f0" }}>{String(s.summary ?? s.description ?? "")}</td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                      {recommended && (
                        <p className="mt-4 text-sm font-semibold" style={{ color: "#c9a962" }}>Recommended path: {recommended}</p>
                      )}
                    </>
                  ) : (
                    <>
                      <pre className="text-xs font-mono text-muted overflow-x-auto max-h-64 overflow-y-auto">
                        {JSON.stringify(twinResult, null, 2)}
                      </pre>
                      {recommended && (
                        <p className="mt-4 text-sm font-semibold" style={{ color: "#c9a962" }}>Recommended path: {recommended}</p>
                      )}
                    </>
                  )}
                </div>
              );
            })()}
          </div>
        )}
      </div>

      {/* Time Machine */}
      <div className="mb-10">
        <div className="flex items-center gap-4 mb-4">
          <h2 className="text-lg font-semibold">Time Machine</h2>
          <button
            onClick={async () => {
              setSnapshotMsg("");
              setSnapshotError("");
              try {
                const res = await fetch(`${getApiUrl()}/v1/memory/snapshot`, {
                  method: "POST",
                  headers: { Authorization: `Bearer ${getApiKey()}`, "Content-Type": "application/json" },
                  body: JSON.stringify({ agent_id: agent.id, label: "manual" }),
                });
                if (res.ok) setSnapshotMsg("Snapshot created");
                else setSnapshotError(`Error: ${res.status}`);
              } catch (e) { setSnapshotError(e instanceof Error ? e.message : "Request failed"); }
            }}
            className="text-sm font-semibold px-4 py-1.5 rounded bg-gold text-background hover:bg-gold-dim transition"
          >
            Take Snapshot
          </button>
          <button
            onClick={async () => {
              setSnapshotLoading(true);
              setSnapshotError("");
              try {
                const res = await fetch(`${getApiUrl()}/v1/memory/snapshots?agent_id=${agent.id}`, {
                  headers: { Authorization: `Bearer ${getApiKey()}` },
                });
                if (res.ok) { const d = await res.json(); setSnapshots(Array.isArray(d) ? d : d.snapshots ?? []); }
                else setSnapshotError(`Error: ${res.status}`);
              } catch (e) { setSnapshotError(e instanceof Error ? e.message : "Request failed"); }
              setSnapshotLoading(false);
            }}
            disabled={snapshotLoading}
            className="text-sm px-4 py-1.5 rounded border border-surface-light text-muted hover:text-foreground transition disabled:opacity-50"
          >
            {snapshotLoading ? "Loading..." : "View Snapshots"}
          </button>
        </div>
        {snapshotMsg && <p className="text-sm text-green-400 mb-2">{snapshotMsg}</p>}
        {snapshotError && <p className="text-sm text-red-400 mb-2">{snapshotError}</p>}
        {snapshots.length > 0 && (
          <div className="bg-surface border border-surface-light rounded-xl p-5">
            <div className="space-y-2">
              {snapshots.map((s, i) => (
                <div key={i} className="flex justify-between items-center py-2 border-b border-surface-light last:border-0 text-sm">
                  <span className="font-mono text-muted">{String(s.created_at ?? s.timestamp ?? "—")}</span>
                  <span className="text-foreground">{String(s.label ?? s.name ?? `Snapshot ${i + 1}`)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="grid md:grid-cols-2 gap-8 mb-10">
        <div>
          <h2 className="text-lg font-semibold mb-2">Component Breakdown</h2>
          {explainText?.root_cause && (() => {
            const rc = explainText.root_cause.toLowerCase();
            const human = rc.includes("freshness") ? "The main risk is memory age — this data may be outdated."
              : rc.includes("drift") ? "The main risk is semantic drift — this memory has changed meaning."
              : rc.includes("provenance") ? "The main risk is source trust — this memory comes from an unreliable source."
              : rc.includes("interference") ? "The main risk is conflicting sources — two memories contradict each other."
              : rc.includes("recovery") ? "The main risk is recoverability — this memory is difficult to repair."
              : explainText.root_cause;
            return <p className="text-sm text-muted mb-4">{human}</p>;
          })()}
          {!explainText?.root_cause && agent.component_breakdown && (() => {
            const entries = Object.entries(agent.component_breakdown ?? {}).filter(([, v]) => typeof v === "number");
            if (entries.length === 0) return null;
            const [topKey, topVal] = entries.sort(([, a], [, b]) => (b as number) - (a as number))[0];
            return <p className="text-sm text-muted mb-4">Highest component: <strong className="text-foreground">{topKey}</strong> at <strong className="text-foreground">{Math.round(topVal as number)}/100</strong></p>;
          })()}
          <div className="bg-surface border border-surface-light rounded-xl p-5">
            <ComponentBreakdown breakdown={agent.component_breakdown} />
          </div>
        </div>
        <div>
          <h2 className="text-lg font-semibold mb-2">
            Repair Plan
            {(agent.repair_plan?.length ?? 0) > 0 && (
              <span className="text-sm text-gold ml-2">({agent.repair_plan.length})</span>
            )}
          </h2>
          {(agent.repair_plan?.length ?? 0) > 0 && (() => {
            const first = agent.repair_plan[0] as unknown as Record<string, unknown>;
            const action = first?.action ?? first;
            const improvement = Number(first?.projected_improvement ?? 0);
            return improvement ? (
              <p className="text-sm text-muted mb-4">Applying <strong className="text-foreground">{String(action)}</strong> is expected to reduce omega by <strong className="text-green-400">{Math.abs(improvement)}</strong> points.</p>
            ) : (
              <p className="text-sm text-muted mb-4">Recommended: apply <strong className="text-foreground">{String(action)}</strong> then re-run preflight.</p>
            );
          })()}
          <RepairPlanList plan={agent.repair_plan ?? []} />
        </div>
      </div>

      <div className="mb-10">
        <h2 className="text-lg font-semibold mb-4">
          At-Risk Warnings
          {(agent.at_risk_warnings?.length ?? 0) > 0 && (
            <span className="text-sm text-red-400 ml-2">({agent.at_risk_warnings.length})</span>
          )}
        </h2>
        <AtRiskWarnings warnings={agent.at_risk_warnings ?? []} />
      </div>

      <div className="mb-10">
        <h2 className="text-lg font-semibold mb-2">Advanced Analytics</h2>
        {(agent.calibration || agent.hawkes_intensity || agent.copula_analysis || agent.mewma) && (
          <p className="text-sm text-muted mb-4">Multiple risk signals detected simultaneously — review recommended.</p>
        )}
        <AdvancedAnalytics
          calibration={agent.calibration}
          hawkes={agent.hawkes_intensity}
          copula={agent.copula_analysis}
          mewma={agent.mewma}
        />
      </div>

      <div className="mb-10">
        <h2 className="text-lg font-semibold mb-4">Deep Analysis <span className="text-xs text-muted font-normal">(click to expand)</span></h2>
        <DeepAnalytics data={agent as unknown as Record<string, unknown>} />
      </div>
    </div>
  );
}
