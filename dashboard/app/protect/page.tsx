"use client";

import { useState, useEffect, useCallback } from "react";
import { getApiKey, getApiUrl } from "../lib/storage";
import { LoadingSkeleton, ConnectKeyState } from "../components/LoadingSkeleton";

interface CircuitBreaker { state: string; last_check?: string; failures?: number; }
interface Violation { id?: string; entry_id?: string; reason?: string; timestamp?: string; omega?: number; }
interface RedTeamResult { attack_type: string; blocked: number; total: number; resilience: number; }
interface Alert { id?: string; message?: string; severity?: string; created_at?: string; }

const CARD = "bg-surface border border-surface-light rounded-xl p-5";
const ATTACK_TYPES = ["injection", "poisoning", "replay", "drift", "tamper", "sleeper"];

export default function ProtectPage() {
  const [mounted, setMounted] = useState(false);
  const [hasKey, setHasKey] = useState(false);
  const [loading, setLoading] = useState(true);

  const [cb, setCb] = useState<CircuitBreaker | null>(null);
  const [violations, setViolations] = useState<Violation[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);

  const [redTeamResults, setRedTeamResults] = useState<RedTeamResult[] | null>(null);
  const [redTeamLoading, setRedTeamLoading] = useState(false);
  const [redTeamError, setRedTeamError] = useState("");
  const [redTeamGrade, setRedTeamGrade] = useState("");

  const headers = useCallback(() => ({ Authorization: `Bearer ${getApiKey()}`, "Content-Type": "application/json" }), []);
  const base = useCallback(() => getApiUrl(), []);

  const load = useCallback(async () => {
    setMounted(true);
    const apiKey = getApiKey();
    setHasKey(!!apiKey);
    if (!apiKey) { setLoading(false); return; }
    const h = { Authorization: `Bearer ${apiKey}` };
    const u = getApiUrl();

    await Promise.all([
      fetch(`${u}/v1/circuit-breaker/status`, { headers: h }).then(r => r.ok ? r.json() : null).then(d => d && setCb(d)).catch(() => {}),
      fetch(`${u}/v1/firewall/violations`, { headers: h }).then(r => r.ok ? r.json() : null).then(d => { if (d) setViolations(Array.isArray(d) ? d : d.violations ?? []); }).catch(() => {}),
      fetch(`${u}/v1/alerts/predictive`, { headers: h }).then(r => r.ok ? r.json() : null).then(d => { if (d) setAlerts(Array.isArray(d) ? d : d.alerts ?? []); }).catch(() => {}),
    ]);
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  async function runRedTeam() {
    setRedTeamLoading(true);
    setRedTeamError("");
    setRedTeamResults(null);
    setRedTeamGrade("");
    try {
      const res = await fetch(`${base()}/v1/redteam/run`, {
        method: "POST", headers: headers(),
        body: JSON.stringify({ attack_types: ATTACK_TYPES, iterations: 100 }),
      });
      if (!res.ok) { setRedTeamError(`Error: ${res.status}`); setRedTeamLoading(false); return; }
      const data = await res.json();
      const jobId = data.job_id ?? data.id;

      if (!jobId) {
        // Sync response
        parseRedTeamResult(data);
        setRedTeamLoading(false);
        return;
      }

      // Poll
      for (let i = 0; i < 15; i++) {
        await new Promise(r => setTimeout(r, 2000));
        const pollRes = await fetch(`${base()}/v1/redteam/${jobId}`, { headers: headers() });
        if (!pollRes.ok) continue;
        const pollData = await pollRes.json();
        if (pollData.status === "complete" || pollData.status === "completed") {
          parseRedTeamResult(pollData);
          setRedTeamLoading(false);
          return;
        }
        if (pollData.status === "failed") {
          setRedTeamError("Red team simulation failed.");
          setRedTeamLoading(false);
          return;
        }
      }
      setRedTeamError("Red team timed out.");
    } catch (e) { setRedTeamError(e instanceof Error ? e.message : "Request failed"); }
    setRedTeamLoading(false);
  }

  function parseRedTeamResult(data: Record<string, unknown>) {
    const nested = (data.result as Record<string, unknown>) ?? {};
    const results = (data.results ?? data.attacks ?? nested.results ?? []) as RedTeamResult[];
    if (Array.isArray(results) && results.length > 0) {
      setRedTeamResults(results);
      const avgResilience = results.reduce((s, r) => s + (r.resilience ?? (r.total > 0 ? (r.blocked / r.total) * 100 : 0)), 0) / results.length;
      setRedTeamGrade(avgResilience >= 90 ? "A" : avgResilience >= 75 ? "B" : avgResilience >= 60 ? "C" : avgResilience >= 40 ? "D" : "F");
    } else {
      // Flat response — show raw
      setRedTeamResults([]);
      setRedTeamGrade(String(data.grade ?? data.immunity_score ?? ""));
    }
  }

  if (!mounted) return null;

  if (!hasKey) return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Protect</h1>
      <p className="text-muted text-sm mb-6">Memory security, firewall, and threat detection.</p>
      <ConnectKeyState />
    </div>
  );

  if (loading) return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Protect</h1>
      <p className="text-muted text-sm mb-6">Memory security, firewall, and threat detection.</p>
      <LoadingSkeleton rows={4} />
    </div>
  );

  const cbColor = cb?.state === "CLOSED" ? "text-green-400" : cb?.state === "OPEN" ? "text-red-400" : "text-yellow-400";

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Protect</h1>
      <p className="text-muted text-sm mb-6">Memory security, firewall, and threat detection.</p>

      {/* Circuit Breaker */}
      <div className={`${CARD} mb-6`}>
        <h2 className="text-lg font-semibold mb-3">Circuit Breaker</h2>
        {cb ? (
          <div className="flex items-center gap-4">
            <span className={`text-2xl font-bold font-mono ${cbColor}`}>{cb.state}</span>
            {cb.failures !== undefined && <span className="text-sm text-muted">Failures: {cb.failures}</span>}
            {cb.last_check && <span className="text-xs text-muted">Last check: {cb.last_check}</span>}
          </div>
        ) : (
          <p className="text-sm text-muted">Circuit breaker status unavailable.</p>
        )}
      </div>

      {/* Firewall Violations */}
      <div className={`${CARD} mb-6`}>
        <h2 className="text-lg font-semibold mb-3">Firewall Violations</h2>
        {violations.length > 0 ? (
          <div className="space-y-2">
            {violations.map((v, i) => (
              <div key={i} className="flex justify-between items-center py-2 border-b border-surface-light last:border-0 text-sm">
                <div>
                  <span className="font-mono text-xs text-foreground">{v.entry_id ?? v.id ?? `violation-${i}`}</span>
                  {v.reason && <span className="ml-2 text-muted">{v.reason}</span>}
                </div>
                <div className="flex items-center gap-3">
                  {v.omega !== undefined && <span className="text-xs font-mono" style={{ color: v.omega > 60 ? "#dc2626" : "#c9a962" }}>Ω {v.omega}</span>}
                  {v.timestamp && <span className="text-xs text-muted">{v.timestamp}</span>}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-6">
            <p style={{ fontSize: "36px", color: "#16a34a" }}>&#x2713;</p>
            <p className="text-sm text-muted mt-2">No firewall violations detected.</p>
          </div>
        )}
      </div>

      {/* Red Team */}
      <div className={`${CARD} mb-6`}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Red Team</h2>
          <button
            onClick={runRedTeam}
            disabled={redTeamLoading}
            className="text-sm font-semibold px-4 py-1.5 rounded bg-gold text-background hover:bg-gold-dim transition disabled:opacity-50"
          >
            {redTeamLoading ? "Running..." : "Run Red Team"}
          </button>
        </div>
        <p className="text-xs text-muted mb-4">6 attack vectors: injection, poisoning, replay, drift, tamper, sleeper.</p>
        {redTeamError && <p className="text-sm text-red-400 mb-3">{redTeamError}</p>}
        {redTeamResults && redTeamResults.length > 0 && (
          <>
            <table className="w-full text-sm" style={{ borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  {["Attack Type", "Blocked", "Total", "Resilience"].map(h => (
                    <th key={h} className="text-xs text-muted uppercase text-left pb-2 pr-4" style={{ borderBottom: "1px solid #e5e7eb" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {redTeamResults.map((r, i) => {
                  const pct = r.resilience ?? (r.total > 0 ? Math.round((r.blocked / r.total) * 100) : 0);
                  return (
                    <tr key={i}>
                      <td className="py-2 pr-4 font-mono text-xs font-semibold" style={{ borderBottom: "1px solid #f5f4f0" }}>{r.attack_type}</td>
                      <td className="py-2 pr-4 text-sm" style={{ borderBottom: "1px solid #f5f4f0" }}>{r.blocked}</td>
                      <td className="py-2 pr-4 text-sm" style={{ borderBottom: "1px solid #f5f4f0" }}>{r.total}</td>
                      <td className="py-2 pr-4 text-sm font-semibold" style={{ borderBottom: "1px solid #f5f4f0", color: pct >= 90 ? "#16a34a" : pct >= 60 ? "#c9a962" : "#dc2626" }}>{pct}%</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {redTeamGrade && (
              <p className="mt-4 text-sm">
                Overall grade: <strong className="text-lg" style={{ color: redTeamGrade <= "B" ? "#16a34a" : redTeamGrade <= "C" ? "#c9a962" : "#dc2626" }}>{redTeamGrade}</strong>
              </p>
            )}
          </>
        )}
        {redTeamResults && redTeamResults.length === 0 && redTeamGrade && (
          <p className="text-sm">Grade: <strong className="text-lg" style={{ color: "#c9a962" }}>{redTeamGrade}</strong></p>
        )}
      </div>

      {/* Predictive Alerts */}
      <div className={CARD}>
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
            <p className="text-sm text-muted mt-2">No active alerts.</p>
          </div>
        )}
      </div>
    </div>
  );
}
