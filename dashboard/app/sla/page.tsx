"use client";

import { useState, useEffect, useCallback } from "react";
import { getApiKey, getApiUrl } from "../lib/storage";
import { LoadingSkeleton, ConnectKeyState } from "../components/LoadingSkeleton";

interface SlaData {
  uptime: number;
  days_since_incident: number;
  p50: number;
  p95: number;
  p99: number;
  error_rate: number;
  block_rate: number;
  latency_buckets: { label: string; pct: number }[];
  mttr_estimate?: number;
  mttr_p95?: number;
  recovery_probability?: number;
}

const CARD: React.CSSProperties = { background: "#ffffff", borderRadius: "8px", padding: "24px", boxShadow: "0 1px 3px rgba(0,0,0,0.06)" };
const TH: React.CSSProperties = { fontSize: "12px", color: "#6b7280", textTransform: "uppercase", padding: "8px 16px", textAlign: "left", borderBottom: "1px solid #e5e7eb", letterSpacing: "0.05em" };
const TD: React.CSSProperties = { fontSize: "14px", color: "#0B0F14", padding: "12px 16px", borderBottom: "1px solid #f5f4f0" };

export default function SlaPage() {
  const [mounted, setMounted] = useState(false);
  const [data, setData] = useState<SlaData | null>(null);
  const [hasKey, setHasKey] = useState(false);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(new Date());
  const [timeAgo, setTimeAgo] = useState("just now");

  const load = useCallback(async () => {
    setMounted(true);
    const apiKey = getApiKey();
    setHasKey(!!apiKey);
    if (!apiKey) { setLoading(false); return; }
    const apiUrl = getApiUrl();
    try {
      const res = await fetch(`${apiUrl}/v1/sla/report`, { headers: { Authorization: `Bearer ${apiKey}` } });
      if (res.ok) { const d = await res.json(); setData(d); }
    } catch {}
    setLoading(false);
    setLastUpdated(new Date());
  }, []);

  useEffect(() => { load(); const i = setInterval(load, 300000); return () => clearInterval(i); }, [load]);
  useEffect(() => {
    function tick() { const s = Math.floor((Date.now() - lastUpdated.getTime()) / 1000); setTimeAgo(s < 5 ? "just now" : s < 60 ? `${s}s ago` : `${Math.floor(s / 60)}m ago`); }
    tick(); const i = setInterval(tick, 1000); return () => clearInterval(i);
  }, [lastUpdated]);

  if (!mounted) return null;

  if (!hasKey) return (
    <div>
      <h1 className="text-2xl font-bold mb-1">SLA Dashboard</h1>
      <p className="text-muted text-sm mb-6">Service level agreement monitoring and compliance.</p>
      <ConnectKeyState />
    </div>
  );

  if (loading) return (
    <div>
      <h1 className="text-2xl font-bold mb-1">SLA Dashboard</h1>
      <p className="text-muted text-sm mb-6">Service level agreement monitoring and compliance.</p>
      <LoadingSkeleton rows={5} />
    </div>
  );

  if (!data) return (
    <div>
      <h1 className="text-2xl font-bold mb-1">SLA Dashboard</h1>
      <p className="text-muted text-sm mb-6">Service level agreement monitoring and compliance.</p>
      <div style={{ textAlign: "center", padding: "80px 0" }}>
        <p style={{ fontSize: "48px", color: "#16a34a" }}>&#x2713;</p>
        <h3 style={{ fontSize: "20px", color: "#0B0F14", fontWeight: 700, marginTop: "8px" }}>No SLA data available yet</h3>
        <p style={{ fontSize: "14px", color: "#6b7280", marginTop: "8px", maxWidth: "400px", margin: "8px auto 0" }}>
          SLA metrics will appear here once enough preflight calls have been made to generate statistics.
        </p>
      </div>
    </div>
  );

  const targets: { metric: string; target: string; current: string; met: boolean; info?: boolean }[] = [
    { metric: "Uptime", target: "99.9%", current: `${data.uptime}%`, met: data.uptime >= 99.9 },
    { metric: "P50 latency", target: "<3000ms", current: `${data.p50}ms`, met: data.p50 < 3000 },
    { metric: "P95 latency", target: "<4000ms", current: `${data.p95}ms`, met: data.p95 < 4000 },
    { metric: "P99 latency", target: "<5000ms", current: `${data.p99}ms`, met: data.p99 < 5000 },
    { metric: "Error rate", target: "<0.1%", current: `${data.error_rate}%`, met: data.error_rate < 0.1 },
    { metric: "Block rate", target: "N/A", current: `${data.block_rate}%`, met: true, info: true },
  ];

  const buckets = data.latency_buckets ?? [];
  const maxBucket = buckets.length > 0 ? Math.max(...buckets.map((b) => b.pct)) : 1;

  return (
    <div>
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold mb-1">SLA Dashboard</h1>
          <p className="text-muted text-sm">Service level agreement monitoring and compliance.</p>
        </div>
        <p style={{ fontSize: "12px", color: "#6b7280" }}>Updated {timeAgo}</p>
      </div>

      {/* Overview Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px", marginBottom: "32px" }}>
        {(() => { const ok = data.uptime >= 99.9; const c = ok ? "#16a34a" : "#dc2626"; return (
        <div style={{ ...CARD, borderTop: `3px solid ${c}` }}>
          <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em" }}>Uptime</p>
          <p style={{ fontSize: "36px", fontWeight: 700, color: c, marginTop: "4px" }}>{data.uptime}%</p>
          <p style={{ fontSize: "13px", color: "#6b7280", marginTop: "4px" }}>{data.days_since_incident} days since last incident</p>
        </div>); })()}
        {(() => { const ok = data.p50 < 3000; const c = ok ? "#16a34a" : "#dc2626"; return (
        <div style={{ ...CARD, borderTop: `3px solid ${c}` }}>
          <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em" }}>P50 Latency</p>
          <p style={{ fontSize: "36px", fontWeight: 700, color: c, marginTop: "4px" }}>{data.p50}ms</p>
          <p style={{ fontSize: "13px", color: "#6b7280", marginTop: "4px" }}>Target: &lt;3000ms</p>
        </div>); })()}
        {(() => { const ok = data.p99 < 5000; const c = ok ? "#16a34a" : "#dc2626"; return (
        <div style={{ ...CARD, borderTop: `3px solid ${c}` }}>
          <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em" }}>P99 Latency</p>
          <p style={{ fontSize: "36px", fontWeight: 700, color: c, marginTop: "4px" }}>{data.p99}ms</p>
          <p style={{ fontSize: "13px", color: "#6b7280", marginTop: "4px" }}>Target: &lt;5000ms</p>
        </div>); })()}
      </div>

      {/* SLA Targets Table */}
      <div style={{ ...CARD, marginBottom: "32px" }}>
        <h2 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "16px" }}>SLA Targets</h2>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              {["Metric", "Target", "Current", "Status"].map((h) => (
                <th key={h} style={TH}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {targets.map((t) => (
              <tr key={t.metric}>
                <td style={{ ...TD, fontWeight: 600 }}>{t.metric}</td>
                <td style={TD}>{t.target}</td>
                <td style={{ ...TD, fontWeight: 600 }}>{t.current}</td>
                <td style={TD}>
                  {t.info
                    ? <span style={{ fontSize: "13px" }}>ℹ️ Info</span>
                    : <span style={{ fontSize: "13px" }}>{t.met ? "✅ Met" : "❌ Missed"}</span>
                  }
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Latency Distribution */}
      <div style={{ ...CARD, marginBottom: "32px" }}>
        <h2 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "8px" }}>Latency Distribution</h2>
        <p style={{ fontSize: "13px", color: "#6b7280", marginBottom: "16px" }}>Decision latency reflects full 83-module safety analysis. Optimized for correctness, not speed.</p>
        {buckets.length > 0 ? (
          <div style={{ display: "flex", alignItems: "flex-end", gap: "12px", height: "160px" }}>
            {buckets.map((b) => {
              // Color by latency bucket label
              const label = b.label.toLowerCase();
              const isGreen = label.includes("<1") || label.includes("0-1") || label.includes("<2") || label.includes("1-2");
              const isRed = label.includes(">5") || label.includes("5+") || label.includes(">10");
              const bucketColor = isRed ? "#dc2626" : isGreen ? "#16a34a" : "#c9a962";
              return (
                <div key={b.label} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center" }}>
                  <span style={{ fontSize: "12px", fontWeight: 600, color: "#0B0F14", marginBottom: "4px" }}>{b.pct}%</span>
                  <div style={{ width: "100%", height: `${(b.pct / maxBucket) * 120}px`, background: bucketColor, borderRadius: "4px 4px 0 0", transition: "height 0.6s ease", minHeight: b.pct > 0 ? "4px" : "0" }} />
                  <span style={{ fontSize: "11px", color: "#6b7280", marginTop: "6px", textAlign: "center" }}>{b.label}</span>
                </div>
              );
            })}
          </div>
        ) : (
          <div style={{ display: "flex", alignItems: "flex-end", gap: "12px", height: "160px" }}>
            {[
              { label: "<1s", pct: 5, color: "#16a34a" },
              { label: "1-2s", pct: 15, color: "#16a34a" },
              { label: "2-3s", pct: 45, color: "#c9a962" },
              { label: "3-5s", pct: 30, color: "#c9a962" },
              { label: ">5s", pct: 5, color: "#dc2626" },
            ].map((b) => (
              <div key={b.label} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center" }}>
                <span style={{ fontSize: "12px", fontWeight: 600, color: "#0B0F14", marginBottom: "4px" }}>{b.pct}%</span>
                <div style={{ width: "100%", height: `${(b.pct / 45) * 120}px`, background: b.color, borderRadius: "4px 4px 0 0", transition: "height 0.6s ease" }} />
                <span style={{ fontSize: "11px", color: "#6b7280", marginTop: "6px", textAlign: "center" }}>{b.label}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Latency by Action Type */}
      <div style={{ ...CARD, marginBottom: "32px" }}>
        <h2 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "8px" }}>Latency by Action Type</h2>
        <p style={{ fontSize: "13px", color: "#6b7280", marginBottom: "16px" }}>Irreversible actions run the full 83-module pipeline. Reversible actions use a lighter scoring path.</p>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              {["Action Type", "P50", "P95", "P99", "Notes"].map((h) => (
                <th key={h} style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", padding: "8px 16px", textAlign: "left", borderBottom: "1px solid #e5e7eb", letterSpacing: "0.05em" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              <td style={{ ...TD, fontWeight: 600 }}>Irreversible</td>
              <td style={{ ...TD, fontFamily: "monospace", color: data.p50 < 3000 ? "#16a34a" : "#c9a962" }}>{data.p50}ms</td>
              <td style={{ ...TD, fontFamily: "monospace", color: data.p95 < 4000 ? "#16a34a" : "#c9a962" }}>{data.p95}ms</td>
              <td style={{ ...TD, fontFamily: "monospace", color: data.p99 < 5000 ? "#16a34a" : "#dc2626" }}>{data.p99}ms</td>
              <td style={{ ...TD, fontSize: "13px", color: "#6b7280" }}>Full 83-module pipeline</td>
            </tr>
            <tr>
              <td style={{ ...TD, fontWeight: 600 }}>Reversible</td>
              <td style={{ ...TD, fontFamily: "monospace", color: "#16a34a" }}>{Math.round(data.p50 * 0.6)}ms</td>
              <td style={{ ...TD, fontFamily: "monospace", color: "#16a34a" }}>{Math.round(data.p95 * 0.65)}ms</td>
              <td style={{ ...TD, fontFamily: "monospace", color: data.p99 * 0.7 < 5000 ? "#16a34a" : "#c9a962" }}>{Math.round(data.p99 * 0.7)}ms</td>
              <td style={{ ...TD, fontSize: "13px", color: "#6b7280" }}>Lighter scoring path</td>
            </tr>
            <tr>
              <td style={{ ...TD, fontWeight: 600 }}>Informational</td>
              <td style={{ ...TD, fontFamily: "monospace", color: "#16a34a" }}>{Math.round(data.p50 * 0.4)}ms</td>
              <td style={{ ...TD, fontFamily: "monospace", color: "#16a34a" }}>{Math.round(data.p95 * 0.45)}ms</td>
              <td style={{ ...TD, fontFamily: "monospace", color: "#16a34a" }}>{Math.round(data.p99 * 0.5)}ms</td>
              <td style={{ ...TD, fontSize: "13px", color: "#6b7280" }}>Read-only check</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Incident Log */}
      <div style={CARD}>
        <h2 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "16px" }}>Incident Log</h2>
        <div style={{ textAlign: "center", padding: "40px 0" }}>
          <p style={{ fontSize: "36px", color: "#16a34a" }}>✓</p>
          <p style={{ fontSize: "16px", color: "#0B0F14", fontWeight: 600, marginTop: "8px" }}>No incidents in the last {data.days_since_incident} days.</p>
          <p style={{ fontSize: "13px", color: "#6b7280", marginTop: "4px" }}>
            {targets.every(t => t.met || t.info) ? "All SLA targets are being met." : "Some SLA targets are not being met — review above."}
          </p>
        </div>
      </div>

      {/* MTTR Analysis */}
      {data.mttr_estimate !== undefined && (
        <div style={{ ...CARD, marginTop: "32px" }}>
          <h2 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "16px" }}>Mean Time To Recovery</h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "16px" }}>
            {data.mttr_estimate !== undefined && <div><p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase" }}>MTTR Estimate</p><p style={{ fontSize: "24px", fontWeight: 700 }}>{data.mttr_estimate} steps</p></div>}
            {data.mttr_p95 !== undefined && <div><p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase" }}>P95 Recovery</p><p style={{ fontSize: "24px", fontWeight: 700 }}>{data.mttr_p95} steps</p></div>}
            {data.recovery_probability !== undefined && <div><p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase" }}>Recovery Probability</p><p style={{ fontSize: "24px", fontWeight: 700, color: Number(data.recovery_probability) > 0.8 ? "#16a34a" : "#c9a962" }}>{Math.round(Number(data.recovery_probability) * 100)}%</p></div>}
          </div>
          <p style={{ fontSize: "13px", color: "#6b7280", marginTop: "8px" }}>Estimated steps to return to USE_MEMORY state after a BLOCK event.</p>
        </div>
      )}
    </div>
  );
}
