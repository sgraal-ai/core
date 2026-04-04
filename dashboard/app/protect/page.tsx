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

  function authHeaders() {
    return { Authorization: `Bearer ${getApiKey()}`, "Content-Type": "application/json" };
  }
  function apiBase() {
    return getApiUrl();
  }

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

    const hdrs = { Authorization: `Bearer ${getApiKey()}`, "Content-Type": "application/json" };
    const base = apiBase();

    try {
      // Step 1: Start red team run
      const res = await fetch(`${base}/v1/redteam/run`, {
        method: "POST", headers: hdrs,
        body: JSON.stringify({ attack_types: ATTACK_TYPES, iterations: 100 }),
      });
      if (!res.ok) { setRedTeamError(`Error: ${res.status}`); setRedTeamLoading(false); return; }
      const data = await res.json();
      const jobId = data.job_id ?? data.id ?? data.scan_id;

      // Sync response (no job_id)
      if (!jobId) {
        parseResults(data);
        setRedTeamLoading(false);
        return;
      }

      // Step 2: Poll for completion
      for (let i = 0; i < 15; i++) {
        await new Promise(r => setTimeout(r, 2000));
        const pollRes = await fetch(`${base}/v1/redteam/status/${jobId}`, { headers: hdrs });
        if (!pollRes.ok) continue;
        const pollData = await pollRes.json();
        const status = pollData.status ?? pollData.state;
        if (status === "complete" || status === "completed") {
          // Step 3: Fetch full report
          try {
            const reportRes = await fetch(`${base}/v1/redteam/report/${jobId}`, { headers: hdrs });
            if (reportRes.ok) {
              parseResults(await reportRes.json());
              setRedTeamLoading(false);
              return;
            }
          } catch {}
          // Fallback: use poll data directly
          parseResults(pollData);
          setRedTeamLoading(false);
          return;
        }
        if (status === "failed") {
          setRedTeamError("Simulation failed — try with a different memory state.");
          setRedTeamLoading(false);
          return;
        }
      }
      setRedTeamError("Simulation timed out after 30 seconds.");
    } catch (e) {
      setRedTeamError(e instanceof Error ? e.message : "Request failed");
    }
    setRedTeamLoading(false);
  }

  function parseResults(data: Record<string, unknown>) {
    const nested = (data.result as Record<string, unknown>) ?? {};
    const raw = (data.attack_results ?? data.results ?? data.attacks ?? nested.attack_results ?? nested.results ?? []) as RedTeamResult[];
    const grade = String(data.memory_readiness_grade ?? nested.memory_readiness_grade ?? data.grade ?? "");
    if (Array.isArray(raw) && raw.length > 0) {
      setRedTeamResults(raw);
      setRedTeamGrade(grade);
    } else {
      setRedTeamResults([]);
      setRedTeamGrade(grade);
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
          <div>
            <div className="flex items-center gap-4">
              <span className={`text-2xl font-bold font-mono ${cbColor}`}>{cb.state}</span>
              {cb.failures !== undefined && <span className="text-sm text-muted">Failures: {cb.failures}</span>}
              {cb.last_check && <span className="text-xs text-muted">Last check: {cb.last_check}</span>}
            </div>
            {cb.state === "CLOSED" && <p className="text-sm text-muted mt-2">No safety blocks triggered — system operating normally.</p>}
            {cb.state === "OPEN" && <p className="text-sm text-red-400 mt-2">Safety block active — repeated high-risk patterns detected. Agents are paused.</p>}
          </div>
        ) : (
          <p className="text-sm text-muted">Circuit breaker status unavailable.</p>
        )}
      </div>

      {/* Firewall Violations */}
      <div className={`${CARD} mb-6`}>
        <h2 className="text-lg font-semibold mb-3">Firewall Violations</h2>
        {violations.length > 0 ? (
          <div>
            <p className="text-sm text-muted mb-3">{violations.length} injection attempt{violations.length > 1 ? "s" : ""} blocked before reaching your agents.</p>
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
          </div>
        ) : (
          <div className="text-center py-6">
            <p style={{ fontSize: "36px", color: "#16a34a" }}>&#x2713;</p>
            <p className="text-sm text-muted mt-2">No injection attempts detected. Your write firewall is clean.</p>
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
                  const pct = r.resilience != null ? Math.round(r.resilience * 100) : (r.total > 0 ? Math.round((r.blocked / r.total) * 100) : 0);
                  return (
                    <tr key={i}>
                      <td className="py-2 pr-4 font-mono text-xs font-semibold" style={{ borderBottom: "1px solid #f5f4f0" }}>{r.attack_type}</td>
                      <td className="py-2 pr-4 text-sm" style={{ borderBottom: "1px solid #f5f4f0" }}>{r.blocked}</td>
                      <td className="py-2 pr-4 text-sm" style={{ borderBottom: "1px solid #f5f4f0" }}>{r.total}</td>
                      <td className="py-2 pr-4 text-sm font-semibold" style={{ borderBottom: "1px solid #f5f4f0", color: (r.resilience ?? 0) >= 0.9 ? "#16a34a" : (r.resilience ?? 0) >= 0.7 ? "#c9a962" : "#dc2626" }}>{pct}%</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {redTeamGrade && (
              <>
                <p className="mt-4 text-sm">
                  Overall grade: <strong className="text-lg" style={{ color: redTeamGrade <= "B" ? "#16a34a" : redTeamGrade <= "C" ? "#c9a962" : "#dc2626" }}>{redTeamGrade}</strong>
                </p>
                {redTeamGrade <= "B" ? (
                  <p className="text-sm text-muted mt-3">Your memory system withstood {Math.round(redTeamResults.reduce((s, r) => s + (r.resilience ?? 0), 0) / redTeamResults.length * 100)}% of simulated attacks across 6 attack vectors.</p>
                ) : (
                  <p className="text-sm text-red-400 mt-3">Vulnerabilities detected. Review attack types below and consider hardening your memory policies.</p>
                )}
              </>
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
            <p className="text-sm text-muted mt-2">No emerging threats detected. All agents are within normal risk parameters.</p>
          </div>
        )}
      </div>
    </div>
  );
}
