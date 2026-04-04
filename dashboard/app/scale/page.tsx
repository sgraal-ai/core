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

    await Promise.all([
      fetch(`${u}/v1/learning/qtable-status`, { headers: h }).then(r => r.ok ? r.json() : null).then(d => d && setQtable(d)).catch(() => {}),
      fetch(`${u}/v1/alerts/predictive`, { headers: h }).then(r => r.ok ? r.json() : null).then(d => { if (d) setAlerts(Array.isArray(d) ? d : d.alerts ?? []); }).catch(() => {}),
      ...DEMO_FLEET.map(agent =>
        fetch(`${u}/v1/memory/health-history?agent_id=${agent.id}`, { headers: h })
          .then(r => r.ok ? r.json() : null)
          .then(d => { if (d) setHealthHistory(prev => [...prev, { ...d, agent_id: agent.id }]); })
          .catch(() => {})
      ),
    ]);
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
        body: JSON.stringify({ entries: DEMO_FLEET.map(a => ({ entry_id: a.id, agent_id: a.id, action: "REFETCH" })) }),
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
                ? "Cold start — submit outcomes to begin training."
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
          {DEMO_FLEET.map(agent => {
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
                    {healLoading === agent.id ? "..." : "Heal"}
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
        ) : (
          <p className="text-sm text-muted">No health history yet — requires preflight activity.</p>
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
      <div className={CARD}>
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

      {/* Toast */}
      {toast && (
        <div style={{
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
