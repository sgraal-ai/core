"use client";

import { useState, useEffect, useCallback } from "react";
import { getApiKey, getApiUrl } from "../lib/storage";
import { LoadingSkeleton, ConnectKeyState } from "../components/LoadingSkeleton";
import { DEMO_FLEET } from "../lib/demo-fleet";

const CARD = "bg-surface border border-surface-light rounded-xl p-5";

interface QTableStatus { domain?: string; qtable_size?: number; episodes?: number; cold_start?: boolean; }
interface HealResult { auto_healed?: boolean; actions_taken?: number; omega_before?: number; omega_after?: number; improvement?: number; agent_id?: string; }
interface HealthPoint { p95?: number; count?: number; points?: unknown[]; agent_id?: string; }
interface Alert { id?: string; message?: string; severity?: string; created_at?: string; }

export default function ScalePage() {
  const [mounted, setMounted] = useState(false);
  const [hasKey, setHasKey] = useState(false);
  const [loading, setLoading] = useState(true);

  const [qtable, setQtable] = useState<QTableStatus | null>(null);
  const [healResults, setHealResults] = useState<HealResult[]>([]);
  const [healLoading, setHealLoading] = useState<string | null>(null);
  const [healthHistory, setHealthHistory] = useState<HealthPoint[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);
  const [weights, setWeights] = useState<Record<string, unknown> | null>(null);
  const [lineageData, setLineageData] = useState<Record<string, { count: number; format: string }>>({});
  const [fleetAgents, setFleetAgents] = useState<Array<{ id: string; name: string }>>([]);
  const [currentWeights, setCurrentWeights] = useState<Record<string, unknown> | null>(null);
  const [weightsDomain, setWeightsDomain] = useState("general");

  useEffect(() => { if (toast) { const t = setTimeout(() => setToast(null), 3000); return () => clearTimeout(t); } }, [toast]);

  function headers() {
    return { Authorization: `Bearer ${getApiKey()}`, "Content-Type": "application/json" };
  }
  function base() { return getApiUrl(); }

  const load = useCallback(async () => {
    setMounted(true);
    const apiKey = getApiKey();
    setHasKey(!!apiKey);
    if (!apiKey) { setLoading(false); return; }
    const h = { Authorization: `Bearer ${apiKey}` };
    const u = getApiUrl();

    // Discover real agents from audit log, fall back to DEMO_FLEET
    const demoIds = new Set(DEMO_FLEET.map(d => d.id));
    let agents: Array<{ id: string; name: string }> = DEMO_FLEET.map(d => ({ id: d.id, name: d.name }));
    try {
      const auditRes = await fetch(`${u}/v1/audit-log?limit=50`, { headers: h });
      if (auditRes.ok) {
        const auditData = await auditRes.json();
        const entries = auditData.entries ?? [];
        const realIds = [...new Set(
          entries.map((e: Record<string, unknown>) => e.agent_id)
            .filter((id: unknown): id is string => typeof id === "string" && id.length > 0 && !demoIds.has(id))
        )] as string[];
        if (realIds.length > 0) {
          agents = realIds.map(id => ({
            id,
            name: id.replace(/^agent-/, "").replace(/-/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase()),
          }));
        }
      }
    } catch {}
    setFleetAgents(agents);

    setHealthHistory([]);
    const healthResults: HealthPoint[] = [];
    await Promise.all([
      fetch(`${u}/v1/learning/qtable-status`, { headers: h }).then(r => r.ok ? r.json() : null).then(d => d && setQtable(d)).catch(() => {}),
      fetch(`${u}/v1/alerts/predictive`, { headers: h }).then(r => r.ok ? r.json() : null).then(d => { if (d) setAlerts(Array.isArray(d) ? d : d.alerts ?? []); }).catch(() => {}),
      fetch(`${u}/v1/weights/export`, { headers: h }).then(r => r.ok ? r.json() : null).then(d => d && setWeights(d)).catch(() => {}),
      fetch(`${u}/v1/weights/current`, { headers: h }).then(r => r.ok ? r.json() : null).then(d => d && setCurrentWeights(d)).catch(() => {}),
      ...agents.map(agent =>
        fetch(`${u}/v1/memory/health-history?agent_id=${agent.id}`, { headers: h })
          .then(r => r.ok ? r.json() : null)
          .then(d => { if (d) healthResults.push({ ...d, agent_id: agent.id }); })
          .catch(() => {})
      ),
    ]);
    setHealthHistory(healthResults);
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  async function runHeal(agentId: string) {
    setHealLoading(agentId);
    try {
      const res = await fetch(`${base()}/v1/heal/autonomous`, {
        method: "POST", headers: headers(),
        body: JSON.stringify({ agent_id: agentId }),
      });
      if (res.ok) {
        const data = await res.json();
        setHealResults(prev => [...prev.filter(r => r.agent_id !== agentId), { ...data, agent_id: agentId }]);
        setToast({ message: `Healed ${agentId}`, type: "success" });
      } else {
        setToast({ message: `Heal failed: ${res.status}`, type: "error" });
      }
    } catch (e) { setToast({ message: e instanceof Error ? e.message : "Heal failed", type: "error" }); }
    setHealLoading(null);
  }

  async function runBatchHeal() {
    setHealLoading("batch");
    try {
      const res = await fetch(`${base()}/v1/heal/batch`, {
        method: "POST", headers: headers(),
        body: JSON.stringify({ entries: fleetAgents.map(a => ({ entry_id: a.id, agent_id: a.id, action: "REFETCH" })) }),
      });
      if (res.ok) {
        const data = await res.json();
        const results = (data.results ?? data.healed ?? []) as HealResult[];
        setHealResults(results);
        setToast({ message: `Batch heal complete — ${results.length} agents`, type: "success" });
      } else {
        setToast({ message: `Batch heal failed: ${res.status}`, type: "error" });
      }
    } catch (e) { setToast({ message: e instanceof Error ? e.message : "Batch heal failed", type: "error" }); }
    setHealLoading(null);
  }

  if (!mounted) return null;

  if (!hasKey) return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Scale</h1>
      <p className="text-muted text-sm mb-6">Learning, autonomous healing, and fleet health.</p>
      <ConnectKeyState />
    </div>
  );

  if (loading) return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Scale</h1>
      <p className="text-muted text-sm mb-6">Learning, autonomous healing, and fleet health.</p>
      <LoadingSkeleton rows={4} />
    </div>
  );

  const episodes = Number(qtable?.episodes ?? 0);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Scale</h1>
      <p className="text-muted text-sm mb-6">Learning, autonomous healing, and fleet health.</p>

      {/* Learning Status */}
      <div className={`${CARD} mb-6`}>
        <h2 className="text-lg font-semibold mb-3">Learning Status</h2>
        {qtable ? (
          <div>
            <div className="flex items-center gap-6 mb-3">
              <div>
                <p className="text-xs text-muted uppercase mb-1">Episodes</p>
                <p className="text-2xl font-bold" style={{ color: episodes > 0 ? "#16a34a" : "#6b7280" }}>{episodes}</p>
              </div>
              {qtable.domain && (
                <div>
                  <p className="text-xs text-muted uppercase mb-1">Domain</p>
                  <p className="text-sm font-semibold">{qtable.domain}</p>
                </div>
              )}
              {qtable.qtable_size !== undefined && (
                <div>
                  <p className="text-xs text-muted uppercase mb-1">Q-table Size</p>
                  <p className="text-sm font-mono">{qtable.qtable_size}</p>
                </div>
              )}
            </div>
            <p className="text-sm text-muted">
              {qtable.cold_start
                ? "Learning not active yet. Sgraal already blocks unsafe decisions without learning. Submit outcomes via agent detail to activate self-improvement."
                : `The system has learned from ${episodes} decision outcomes. Thresholds are calibrating automatically.`}
            </p>
          </div>
        ) : (
          <p className="text-sm text-muted">Learning status unavailable.</p>
        )}
      </div>

      {/* Autonomous Heal */}
      <div className={`${CARD} mb-6`}>
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-semibold">Autonomous Heal</h2>
          <button onClick={runBatchHeal} disabled={healLoading === "batch"}
            className="text-sm font-semibold px-4 py-1.5 rounded bg-gold text-background hover:bg-gold-dim transition disabled:opacity-50">
            {healLoading === "batch" ? "Healing..." : "Run Batch Heal"}
          </button>
        </div>
        <p className="text-sm text-muted mb-4">Autonomous heal detects memory degradation and applies the optimal repair plan — without manual intervention.</p>
        <p className="text-xs text-muted mb-4">Batch heal runs the full repair sequence across all agents simultaneously.</p>
        <div className="space-y-3">
          {fleetAgents.map(agent => {
            const result = healResults.find(r => r.agent_id === agent.id);
            return (
              <div key={agent.id} className="py-2 border-b border-surface-light last:border-0">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-semibold">{agent.name}</p>
                    <p className="text-xs text-muted font-mono">{agent.id}</p>
                  </div>
                  <button onClick={() => runHeal(agent.id)} disabled={healLoading === agent.id}
                    className="text-xs px-3 py-1 rounded border border-surface-light text-muted hover:text-foreground transition disabled:opacity-50">
                    {healLoading === agent.id ? <span aria-label="Healing agent">...</span> : "Heal"}
                  </button>
                </div>
                {result && (
                  <p className="text-xs mt-1" style={{ color: "#16a34a" }}>
                    &#x2713; Healed — &#x3A9; before: {String(result.omega_before ?? "?")} &rarr; after: {String(result.omega_after ?? "?")}
                    {result.improvement !== undefined && <>, improvement: {String(result.improvement)}</>}
                    {result.actions_taken !== undefined && <>, {result.actions_taken} actions</>}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Health History */}
      <div className={`${CARD} mb-6`}>
        <h2 className="text-lg font-semibold mb-2">Health History</h2>
        <p className="text-sm text-muted mb-4">Tracks omega score trends over time. Rising P95 indicates systemic memory degradation across your fleet.</p>
        {healthHistory.length > 0 ? (
          <>
            <table className="w-full text-sm" style={{ borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  {["Agent", "P95", "Count", "Data Points"].map(h => (
                    <th key={h} className="text-xs text-muted uppercase text-left pb-2 pr-4" style={{ borderBottom: "1px solid #e5e7eb" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {healthHistory.map((h, i) => (
                  <tr key={i}>
                    <td className="py-2 pr-4 font-mono text-xs font-semibold" style={{ borderBottom: "1px solid #f5f4f0" }}>{h.agent_id}</td>
                    <td className="py-2 pr-4 text-sm" style={{ borderBottom: "1px solid #f5f4f0" }}>{h.p95 !== undefined ? String(h.p95) : "—"}</td>
                    <td className="py-2 pr-4 text-sm" style={{ borderBottom: "1px solid #f5f4f0" }}>{h.count !== undefined ? String(h.count) : "—"}</td>
                    <td className="py-2 pr-4 text-sm" style={{ borderBottom: "1px solid #f5f4f0" }}>{Array.isArray(h.points) ? String(h.points.length) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {healthHistory.every(h => !h.count && (!Array.isArray(h.points) || h.points.length === 0)) && (
              <p className="text-xs text-muted mt-3">Submit 10 outcomes to unlock health trend tracking.</p>
            )}
          </>
        ) : (
          <>
            <p className="text-sm text-muted">No health history yet — requires preflight activity.</p>
            <p className="text-xs text-muted mt-2">Submit 10 outcomes to unlock health trend tracking.</p>
          </>
        )}
      </div>

      {/* Predictive Alerts */}
      <div className={`${CARD} mb-6`}>
        <h2 className="text-lg font-semibold mb-3">Predictive Alerts</h2>
        {alerts.length > 0 ? (
          <div className="space-y-2">
            {alerts.map((a, i) => (
              <div key={i} className="flex justify-between items-center py-2 border-b border-surface-light last:border-0 text-sm">
                <div>
                  <span className={`text-xs font-mono mr-2 ${a.severity === "critical" ? "text-red-400" : a.severity === "warning" ? "text-yellow-400" : "text-muted"}`}>
                    [{(a.severity ?? "info").toUpperCase()}]
                  </span>
                  <span>{a.message ?? "Alert"}</span>
                </div>
                {a.created_at && <span className="text-xs text-muted">{a.created_at}</span>}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-6">
            <p style={{ fontSize: "36px", color: "#16a34a" }}>&#x2713;</p>
            <p className="text-sm text-muted mt-2">No emerging threats detected.</p>
            <p className="text-xs text-muted mt-2">Predictive alerts fire when health trends suggest a future BLOCK — before it happens.</p>
          </div>
        )}
      </div>

      {/* Outcome History */}
      <div className={`${CARD} mb-6`}>
        <h2 className="text-lg font-semibold mb-3">Outcome Reporting</h2>
        <p className="text-sm text-muted mb-2">Submit outcomes via <code className="text-gold font-mono text-xs">POST /v1/outcome</code> to train the RL model and improve future decisions.</p>
        <p className="text-sm text-muted mb-4">Every reported outcome trains the RL model. The more outcomes you submit, the more accurately Sgraal calibrates thresholds for your specific use case.</p>
        <pre className="bg-surface-light rounded-lg p-4 text-xs font-mono text-foreground overflow-x-auto">{`curl -X POST https://api.sgraal.com/v1/outcome \\
  -H "Authorization: Bearer sg_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "outcome_id": "<from preflight response>",
    "status": "success",
    "failure_components": []
  }'`}</pre>
        <p className="text-xs text-muted mt-3">Each reported outcome updates the Q-table, calibrates thresholds, and improves Shapley attribution weights.</p>
      </div>

      {/* Weight Export/Import */}
      <div className={`${CARD} mb-6`}>
        <h2 className="text-lg font-semibold mb-2">Weight Export / Import</h2>
        <p className="text-sm text-muted mb-4">Weights encode your system{"'"}s learned thresholds. Export to back up or transfer to another environment.</p>
        <div className="flex gap-3 mb-4">
          <button onClick={async () => {
            try {
              const res = await fetch(`${base()}/v1/weights/export`, { headers: headers() });
              if (!res.ok) return;
              const data = await res.json();
              setWeights(data);
              const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a"); a.href = url; a.download = "sgraal-weights.json"; a.click();
              setTimeout(() => URL.revokeObjectURL(url), 1000);
              setToast({ message: "Weights exported", type: "success" });
            } catch { setToast({ message: "Export failed", type: "error" }); }
          }} className="text-sm font-semibold px-4 py-1.5 rounded bg-gold text-background hover:bg-gold-dim transition">Export Weights</button>
          <label className="text-sm px-4 py-1.5 rounded border border-surface-light text-muted hover:text-foreground transition cursor-pointer">
            Import Weights
            <input type="file" accept=".json" className="hidden" onChange={async (e) => {
              const file = e.target.files?.[0];
              if (!file) return;
              try {
                const text = await file.text();
                const data = JSON.parse(text);
                const res = await fetch(`${base()}/v1/weights/import`, { method: "POST", headers: headers(), body: JSON.stringify(data) });
                if (res.ok) { setToast({ message: "Weights imported", type: "success" }); setWeights(data); }
                else setToast({ message: `Import failed: ${res.status}`, type: "error" });
              } catch { setToast({ message: "Invalid JSON file", type: "error" }); }
            }} />
          </label>
        </div>
        {weights && (() => {
          const thresholds = (weights.thresholds ?? weights) as Record<string, unknown>;
          const lr = (weights.learning_rate ?? weights) as Record<string, unknown>;
          return (
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-sm">
              {thresholds.warn !== undefined && <div><p className="text-xs text-muted uppercase">Warn</p><p className="font-semibold font-mono">{String(thresholds.warn)}</p></div>}
              {thresholds.ask_user !== undefined && <div><p className="text-xs text-muted uppercase">Ask User</p><p className="font-semibold font-mono">{String(thresholds.ask_user)}</p></div>}
              {thresholds.block !== undefined && <div><p className="text-xs text-muted uppercase">Block</p><p className="font-semibold font-mono">{String(thresholds.block)}</p></div>}
              {lr.eta !== undefined && <div><p className="text-xs text-muted uppercase">Learning Rate</p><p className="font-semibold font-mono">{String(lr.eta)}</p></div>}
              {lr.ewc_strength !== undefined && <div><p className="text-xs text-muted uppercase">EWC Strength</p><p className="font-semibold font-mono">{String(lr.ewc_strength)}</p></div>}
            </div>
          );
        })()}
      </div>

      {/* Agent Lineage */}
      <div className={`${CARD} mb-6`}>
        <h2 className="text-lg font-semibold mb-2">Agent Lineage</h2>
        <p className="text-sm text-muted mb-4">Lineage tracks how each memory entry was created and modified over time.</p>
        <div className="space-y-2">
          {fleetAgents.map(agent => {
            const data = lineageData[agent.id];
            return (
              <div key={agent.id} className="flex items-center justify-between py-2 border-b border-surface-light last:border-0">
                <div>
                  <p className="text-sm font-semibold">{agent.name}</p>
                  <p className="text-xs text-muted font-mono">{agent.id}</p>
                  {data && <p className="text-xs text-muted mt-1">{data.count} entries · {data.format}</p>}
                </div>
                <button onClick={async () => {
                  try {
                    const res = await fetch(`${base()}/v1/store/lineage/export?agent_id=${agent.id}`, { headers: headers() });
                    if (res.ok) {
                      const d = await res.json();
                      const entries = Array.isArray(d) ? d : d.entries ?? d.data ?? [];
                      setLineageData(prev => ({ ...prev, [agent.id]: { count: entries.length, format: d.format ?? "json" } }));
                    } else {
                      setLineageData(prev => ({ ...prev, [agent.id]: { count: 0, format: "—" } }));
                    }
                  } catch {
                    setLineageData(prev => ({ ...prev, [agent.id]: { count: 0, format: "error" } }));
                  }
                }} className="text-xs px-3 py-1 rounded border border-surface-light text-muted hover:text-foreground transition">
                  View Lineage
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* RL Confidence Trend */}
      <div className={`${CARD} mb-6`}>
        <h2 className="text-lg font-semibold mb-2">RL Confidence Trend</h2>
        <p className="text-sm text-muted mb-4">Confidence improves as more outcomes are submitted. Track accuracy gains over time.</p>
        <table className="w-full text-sm" style={{ borderCollapse: "collapse" }}>
          <thead>
            <tr>
              {["Metric", "Value"].map(h => (
                <th key={h} className="text-xs text-muted uppercase text-left pb-2 pr-4" style={{ borderBottom: "1px solid #e5e7eb" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr><td className="py-2 pr-4" style={{ borderBottom: "1px solid #f5f4f0" }}>Domain</td><td className="py-2 font-mono text-xs" style={{ borderBottom: "1px solid #f5f4f0" }}>{qtable?.domain ?? "—"}</td></tr>
            <tr><td className="py-2 pr-4" style={{ borderBottom: "1px solid #f5f4f0" }}>Episodes</td><td className="py-2 font-mono text-xs" style={{ borderBottom: "1px solid #f5f4f0" }}>{String(qtable?.episodes ?? 0)}</td></tr>
            <tr><td className="py-2 pr-4" style={{ borderBottom: "1px solid #f5f4f0" }}>Q-table Size</td><td className="py-2 font-mono text-xs" style={{ borderBottom: "1px solid #f5f4f0" }}>{String(qtable?.qtable_size ?? 0)}</td></tr>
            <tr><td className="py-2 pr-4" style={{ borderBottom: "1px solid #f5f4f0" }}>Cold Start</td><td className="py-2 font-mono text-xs" style={{ borderBottom: "1px solid #f5f4f0" }}>{qtable?.cold_start ? "Yes" : "No"}</td></tr>
            {weights && (() => {
              const t = (weights.thresholds ?? weights) as Record<string, unknown>;
              return <>
                {t.warn !== undefined && <tr><td className="py-2 pr-4" style={{ borderBottom: "1px solid #f5f4f0" }}>Warn Threshold</td><td className="py-2 font-mono text-xs" style={{ borderBottom: "1px solid #f5f4f0" }}>{String(t.warn)}</td></tr>}
                {t.ask_user !== undefined && <tr><td className="py-2 pr-4" style={{ borderBottom: "1px solid #f5f4f0" }}>Ask User Threshold</td><td className="py-2 font-mono text-xs" style={{ borderBottom: "1px solid #f5f4f0" }}>{String(t.ask_user)}</td></tr>}
                {t.block !== undefined && <tr><td className="py-2 pr-4" style={{ borderBottom: "1px solid #f5f4f0" }}>Block Threshold</td><td className="py-2 font-mono text-xs" style={{ borderBottom: "1px solid #f5f4f0" }}>{String(t.block)}</td></tr>}
              </>;
            })()}
          </tbody>
        </table>
      </div>

      {/* Current Weights */}
      <div className={`${CARD} mb-6`}>
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-semibold">Current Weights</h2>
          <div className="flex items-center gap-3">
            <select value={weightsDomain} onChange={async (e) => {
              const domain = e.target.value;
              setWeightsDomain(domain);
              try {
                const res = await fetch(`${base()}/v1/weights/current?domain=${domain}`, { headers: headers() });
                if (res.ok) setCurrentWeights(await res.json());
              } catch {}
            }} className="border border-surface-light rounded px-2 py-1 text-sm bg-surface text-foreground cursor-pointer">
              {["general", "legal", "fintech", "medical", "coding", "customer_support"].map(d => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
            {currentWeights && (
              <span className="text-xs font-mono px-2 py-1 rounded" style={{
                background: currentWeights.calibrated ? "rgba(22,163,74,0.1)" : "rgba(107,114,128,0.1)",
                color: currentWeights.calibrated ? "#16a34a" : "#6b7280",
              }}>
                {currentWeights.calibrated ? "Calibrated" : "Baseline"}
              </span>
            )}
          </div>
        </div>
        <p className="text-sm text-muted mb-4">Weights adjust automatically as you submit outcomes. Drift shows how much the system has learned.</p>
        {currentWeights && currentWeights.components ? (() => {
          const comps = currentWeights.components as Record<string, { baseline: number; current: number; drift: number }>;
          const totalDrift = Number(currentWeights.total_drift ?? 0);
          const TH_S: React.CSSProperties = { fontSize: "12px", color: "#6b7280", textTransform: "uppercase", padding: "6px 12px", textAlign: "left", borderBottom: "1px solid #e5e7eb", letterSpacing: "0.05em" };
          const TD_S: React.CSSProperties = { fontSize: "13px", padding: "8px 12px", borderBottom: "1px solid #f5f4f0", fontFamily: "monospace" };
          return (
            <div>
              <table className="w-full" style={{ borderCollapse: "collapse" }}>
                <thead>
                  <tr>
                    {["Component", "Baseline", "Current", "Drift"].map(h => <th key={h} style={TH_S}>{h}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(comps).map(([k, v]) => {
                    const absDrift = Math.abs(v.drift);
                    const driftColor = absDrift === 0 ? "#16a34a" : absDrift < 0.01 ? "#c9a962" : "#dc2626";
                    return (
                      <tr key={k}>
                        <td style={{ ...TD_S, fontWeight: 600 }}>{k}</td>
                        <td style={TD_S}>{v.baseline}</td>
                        <td style={TD_S}>{v.current}</td>
                        <td style={{ ...TD_S, color: driftColor, fontWeight: 600 }}>{v.drift > 0 ? "+" : ""}{v.drift}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              <p className="text-xs text-muted mt-3">Total drift: <strong className="font-mono">{totalDrift}</strong> — Domain: <strong>{String(currentWeights.domain ?? "general")}</strong></p>
            </div>
          );
        })() : (
          <p className="text-sm text-muted">Submit outcomes to begin weight calibration.</p>
        )}
      </div>

      {/* Store Export/Import */}
      <div className={`${CARD} mb-6`}>
        <h2 className="text-lg font-semibold mb-2">Store Export / Import</h2>
        <p className="text-sm text-muted mb-4">Export and import your full memory store for backup or migration.</p>
        <div className="flex gap-3">
          <button onClick={async () => {
            try {
              const res = await fetch(`${base()}/v1/store/export`, { headers: headers() });
              if (!res.ok) return;
              const data = await res.json();
              const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a"); a.href = url; a.download = "sgraal-store-export.json"; a.click();
              setTimeout(() => URL.revokeObjectURL(url), 1000);
              setToast({ message: "Store exported", type: "success" });
            } catch { setToast({ message: "Export failed", type: "error" }); }
          }} className="text-sm font-semibold px-4 py-1.5 rounded bg-gold text-background hover:bg-gold-dim transition">Export Store</button>
          <label className="text-sm px-4 py-1.5 rounded border border-surface-light text-muted hover:text-foreground transition cursor-pointer">
            Import Store
            <input type="file" accept=".json" className="hidden" onChange={async (e) => {
              const file = e.target.files?.[0];
              if (!file) return;
              try {
                const text = await file.text();
                const parsed = JSON.parse(text);
                const entries = parsed.data ?? parsed.entries ?? (Array.isArray(parsed) ? parsed : []);
                if (!Array.isArray(entries)) {
                  setToast({ message: "Invalid format — expected array of memory entries", type: "error" });
                  return;
                }
                const res = await fetch(`${base()}/v1/store/import`, { method: "POST", headers: headers(), body: JSON.stringify(entries) });
                if (res.ok) setToast({ message: "Store imported", type: "success" });
                else setToast({ message: `Import failed: ${res.status}`, type: "error" });
              } catch { setToast({ message: "Invalid JSON file", type: "error" }); }
            }} />
          </label>
        </div>
      </div>

      {/* Toast */}
      {toast && (
        <div role="alert" aria-live="polite" style={{
          position: "fixed", bottom: "24px", right: "24px",
          background: toast.type === "success" ? "#16a34a" : "#dc2626",
          color: "white", padding: "12px 24px", borderRadius: "8px",
          fontSize: "14px", fontWeight: 600,
          boxShadow: "0 4px 12px rgba(0,0,0,0.15)", zIndex: 100,
        }}>
          {toast.message}
        </div>
      )}
    </div>
  );
}
