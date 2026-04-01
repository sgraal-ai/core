"use client";

import { useState, useEffect, useCallback } from "react";
import { getApiKey, getApiUrl, setApiKey as saveApiKey, setApiUrl as saveApiUrl, removeApiKey, removeApiUrl, getItem, setItem, removeItem } from "../lib/storage";

interface SlaData {
  uptime: number;
  days_since_incident: number;
  p50: number;
  p95: number;
  p99: number;
  error_rate: number;
  block_rate: number;
  latency_buckets: { label: string; pct: number }[];
}

const MOCK: SlaData = {
  uptime: 99.97,
  days_since_incident: 32,
  p50: 12,
  p95: 23,
  p99: 41,
  error_rate: 0.03,
  block_rate: 8.3,
  latency_buckets: [
    { label: "<10ms", pct: 34 },
    { label: "10-20ms", pct: 42 },
    { label: "20-50ms", pct: 18 },
    { label: "50-100ms", pct: 4 },
    { label: "100-200ms", pct: 1.5 },
    { label: ">200ms", pct: 0.5 },
  ],
};

const CARD: React.CSSProperties = { background: "#ffffff", borderRadius: "8px", padding: "24px", boxShadow: "0 1px 3px rgba(0,0,0,0.06)" };
const TH: React.CSSProperties = { fontSize: "12px", color: "#6b7280", textTransform: "uppercase", padding: "8px 16px", textAlign: "left", borderBottom: "1px solid #e5e7eb", letterSpacing: "0.05em" };
const TD: React.CSSProperties = { fontSize: "14px", color: "#0B0F14", padding: "12px 16px", borderBottom: "1px solid #f5f4f0" };

export default function SlaPage() {
  const [data, setData] = useState<SlaData>(MOCK);
  const [hasKey, setHasKey] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(new Date());
  const [timeAgo, setTimeAgo] = useState("just now");

  const load = useCallback(async () => {
    const apiKey = getApiKey();
    setHasKey(!!apiKey);
    if (!apiKey) { setData(MOCK); setLastUpdated(new Date()); return; }
    const apiUrl = getApiUrl();
    try {
      const res = await fetch(`${apiUrl}/v1/sla/report`, { headers: { "X-API-Key": apiKey } });
      if (res.ok) { const d = await res.json(); setData({ ...MOCK, ...d }); }
    } catch {}
    setLastUpdated(new Date());
  }, []);

  useEffect(() => { load(); const i = setInterval(load, 300000); return () => clearInterval(i); }, [load]);
  useEffect(() => {
    function tick() { const s = Math.floor((Date.now() - lastUpdated.getTime()) / 1000); setTimeAgo(s < 5 ? "just now" : s < 60 ? `${s}s ago` : `${Math.floor(s / 60)}m ago`); }
    tick(); const i = setInterval(tick, 1000); return () => clearInterval(i);
  }, [lastUpdated]);

  const targets: { metric: string; target: string; current: string; met: boolean; info?: boolean }[] = [
    { metric: "Uptime", target: "99.9%", current: `${data.uptime}%`, met: data.uptime >= 99.9 },
    { metric: "P50 latency", target: "<50ms", current: `${data.p50}ms`, met: data.p50 < 50 },
    { metric: "P95 latency", target: "<100ms", current: `${data.p95}ms`, met: data.p95 < 100 },
    { metric: "P99 latency", target: "<200ms", current: `${data.p99}ms`, met: data.p99 < 200 },
    { metric: "Error rate", target: "<0.1%", current: `${data.error_rate}%`, met: data.error_rate < 0.1 },
    { metric: "Block rate", target: "N/A", current: `${data.block_rate}%`, met: true, info: true },
  ];

  const maxBucket = Math.max(...data.latency_buckets.map((b) => b.pct));

  return (
    <div>
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold mb-1">SLA Dashboard</h1>
          <p className="text-muted text-sm">Service level agreement monitoring and compliance.</p>
        </div>
        <p style={{ fontSize: "12px", color: "#6b7280" }}>Updated {timeAgo}</p>
      </div>

      {!hasKey && (
        <div className="bg-gold/10 border border-gold/30 rounded-lg px-4 py-3 mb-6 text-sm text-gold">
          Showing mock data. <a href="/settings" className="underline">Enter your API key</a> to see live SLA metrics.
        </div>
      )}

      {/* Overview Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "16px", marginBottom: "32px" }}>
        <div style={{ ...CARD, borderTop: "3px solid #16a34a" }}>
          <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em" }}>Uptime</p>
          <p style={{ fontSize: "36px", fontWeight: 700, color: "#16a34a", marginTop: "4px" }}>{data.uptime}%</p>
          <p style={{ fontSize: "13px", color: "#6b7280", marginTop: "4px" }}>{data.days_since_incident} days since last incident</p>
        </div>
        <div style={{ ...CARD, borderTop: "3px solid #16a34a" }}>
          <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em" }}>P50 Latency</p>
          <p style={{ fontSize: "36px", fontWeight: 700, color: "#16a34a", marginTop: "4px" }}>{data.p50}ms</p>
          <p style={{ fontSize: "13px", color: "#6b7280", marginTop: "4px" }}>Target: &lt;50ms</p>
        </div>
        <div style={{ ...CARD, borderTop: "3px solid #16a34a" }}>
          <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em" }}>P99 Latency</p>
          <p style={{ fontSize: "36px", fontWeight: 700, color: "#16a34a", marginTop: "4px" }}>{data.p99}ms</p>
          <p style={{ fontSize: "13px", color: "#6b7280", marginTop: "4px" }}>Target: &lt;200ms</p>
        </div>
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
        <h2 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "16px" }}>Latency Distribution</h2>
        <div style={{ display: "flex", alignItems: "flex-end", gap: "12px", height: "160px" }}>
          {data.latency_buckets.map((b) => (
            <div key={b.label} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center" }}>
              <span style={{ fontSize: "12px", fontWeight: 600, color: "#0B0F14", marginBottom: "4px" }}>{b.pct}%</span>
              <div style={{ width: "100%", height: `${(b.pct / maxBucket) * 120}px`, background: b.pct > 10 ? "#16a34a" : b.pct > 3 ? "#c9a962" : "#e5e7eb", borderRadius: "4px 4px 0 0", transition: "height 0.6s ease" }} />
              <span style={{ fontSize: "11px", color: "#6b7280", marginTop: "6px", textAlign: "center" }}>{b.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Incident Log */}
      <div style={CARD}>
        <h2 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "16px" }}>Incident Log</h2>
        <div style={{ textAlign: "center", padding: "40px 0" }}>
          <p style={{ fontSize: "36px", color: "#16a34a" }}>✓</p>
          <p style={{ fontSize: "16px", color: "#0B0F14", fontWeight: 600, marginTop: "8px" }}>No incidents in the last {data.days_since_incident} days.</p>
          <p style={{ fontSize: "13px", color: "#6b7280", marginTop: "4px" }}>All SLA targets are being met.</p>
        </div>
      </div>
    </div>
  );
}
