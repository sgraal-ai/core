"use client";

import { useState, useEffect, useCallback } from "react";

interface Summary {
  total_calls: number;
  block_rate: number;
  avg_omega: number;
  decisions: Record<string, number>;
  domain_breakdown: { domain: string; decisions: number; avg_omega: number; block_rate: number }[];
  daily: { label: string; value: number }[];
}

interface TokenWaste { wasted: number; saved: number; roi: number; }

const MOCK_SUMMARY: Summary = {
  total_calls: 24847, block_rate: 8.3, avg_omega: 34.2,
  decisions: { USE_MEMORY: 68, WARN: 18, ASK_USER: 8, BLOCK: 6 },
  domain_breakdown: [
    { domain: "fintech", decisions: 8421, avg_omega: 41.3, block_rate: 12.4 },
    { domain: "healthcare", decisions: 3892, avg_omega: 38.7, block_rate: 9.8 },
    { domain: "legal", decisions: 2104, avg_omega: 35.1, block_rate: 7.2 },
    { domain: "general", decisions: 10430, avg_omega: 22.8, block_rate: 4.1 },
  ],
  daily: [
    { label: "Mon", value: 2840 }, { label: "Tue", value: 3120 }, { label: "Wed", value: 2980 },
    { label: "Thu", value: 3540 }, { label: "Fri", value: 3210 }, { label: "Sat", value: 3890 },
    { label: "Sun", value: 3267 },
  ],
};
const MOCK_WASTE: TokenWaste = { wasted: 847, saved: 719, roi: 8.4 };

const DECISION_COLORS: Record<string, string> = { USE_MEMORY: "#16a34a", WARN: "#eab308", ASK_USER: "#f97316", BLOCK: "#dc2626" };
const CARD: React.CSSProperties = { background: "#ffffff", borderRadius: "8px", padding: "20px", boxShadow: "0 1px 3px rgba(0,0,0,0.06)" };

export default function AnalyticsPage() {
  const [summary, setSummary] = useState<Summary>(MOCK_SUMMARY);
  const [waste, setWaste] = useState<TokenWaste>(MOCK_WASTE);
  const [hasKey, setHasKey] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(new Date());
  const [timeAgo, setTimeAgo] = useState("just now");

  const load = useCallback(async () => {
    const apiKey = localStorage.getItem("sgraal_api_key") ?? "";
    setHasKey(!!apiKey);
    if (!apiKey) { setSummary(MOCK_SUMMARY); setWaste(MOCK_WASTE); setLastUpdated(new Date()); return; }
    const apiUrl = localStorage.getItem("sgraal_api_url") ?? "https://api.sgraal.com";
    const h = { "X-API-Key": apiKey };
    try {
      const [sR, wR] = await Promise.all([
        fetch(`${apiUrl}/v1/analytics/summary`, { headers: h }),
        fetch(`${apiUrl}/v1/analytics/token-waste`, { headers: h }),
      ]);
      if (sR.ok) { const d = await sR.json(); setSummary({ ...MOCK_SUMMARY, ...d }); }
      if (wR.ok) { const d = await wR.json(); setWaste({ ...MOCK_WASTE, ...d }); }
    } catch {}
    setLastUpdated(new Date());
  }, []);

  useEffect(() => { load(); const i = setInterval(load, 60000); return () => clearInterval(i); }, [load]);
  useEffect(() => {
    function tick() { const s = Math.floor((Date.now() - lastUpdated.getTime()) / 1000); setTimeAgo(s < 5 ? "just now" : s < 60 ? `${s}s ago` : `${Math.floor(s / 60)}m ago`); }
    tick(); const i = setInterval(tick, 1000); return () => clearInterval(i);
  }, [lastUpdated]);

  const maxDaily = Math.max(...summary.daily.map((d) => d.value));
  const fmt = (n: number) => n.toLocaleString();

  return (
    <div>
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold mb-1">Analytics</h1>
          <p className="text-muted text-sm">Fleet-wide decision analytics and token waste tracking.</p>
        </div>
        <p style={{ fontSize: "12px", color: "#6b7280" }}>Updated {timeAgo}</p>
      </div>

      {!hasKey && (
        <div className="bg-gold/10 border border-gold/30 rounded-lg px-4 py-3 mb-6 text-sm text-gold">
          Showing mock data. <a href="/settings" className="underline">Enter your API key</a> to see live analytics.
        </div>
      )}

      {/* KPI Row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "16px", marginBottom: "24px" }}>
        <div style={CARD}>
          <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em" }}>Total Decisions</p>
          <p style={{ fontSize: "28px", fontWeight: 700, color: "#0B0F14", marginTop: "4px" }}>{fmt(summary.total_calls)}</p>
          <p style={{ fontSize: "12px", color: "#16a34a", marginTop: "4px" }}>+12% this week</p>
        </div>
        <div style={CARD}>
          <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em" }}>Block Rate</p>
          <p style={{ fontSize: "28px", fontWeight: 700, color: "#0B0F14", marginTop: "4px" }}>{summary.block_rate}%</p>
          <p style={{ fontSize: "12px", color: "#16a34a", marginTop: "4px" }}>-2.1% vs last week</p>
        </div>
        <div style={CARD}>
          <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em" }}>Avg Omega Score</p>
          <p style={{ fontSize: "28px", fontWeight: 700, color: "#c9a962", marginTop: "4px" }}>{summary.avg_omega}</p>
          <p style={{ fontSize: "12px", color: "#6b7280", marginTop: "4px" }}>Fleet risk: Low</p>
        </div>
        <div style={CARD}>
          <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em" }}>Monthly Savings</p>
          <p style={{ fontSize: "28px", fontWeight: 700, color: "#0B0F14", marginTop: "4px" }}>${fmt(waste.saved)}</p>
          <p style={{ fontSize: "12px", color: "#c9a962", marginTop: "4px" }}>{waste.roi}x ROI</p>
        </div>
      </div>

      {/* Decision Breakdown */}
      <div style={{ ...CARD, marginBottom: "24px" }}>
        <h2 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "16px" }}>Decision Breakdown</h2>
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {Object.entries(summary.decisions).map(([key, pct]) => (
            <div key={key} style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <span style={{ width: "100px", fontSize: "13px", fontFamily: "monospace", color: "#0B0F14" }}>{key}</span>
              <div style={{ flex: 1, height: "20px", background: "#f5f4f0", borderRadius: "4px", overflow: "hidden" }}>
                <div style={{ width: `${pct}%`, height: "100%", background: DECISION_COLORS[key] || "#6b7280", borderRadius: "4px", transition: "width 0.8s ease" }} />
              </div>
              <span style={{ width: "40px", fontSize: "13px", fontWeight: 600, textAlign: "right" }}>{pct}%</span>
            </div>
          ))}
        </div>
      </div>

      {/* Token Waste Widget */}
      <div style={{ ...CARD, marginBottom: "24px", background: "rgba(201,169,98,0.06)", border: "1px solid rgba(201,169,98,0.2)" }}>
        <h2 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "12px" }}>Token Waste Analysis</h2>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "16px" }}>
          <div>
            <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase" }}>Wasted</p>
            <p style={{ fontSize: "24px", fontWeight: 700, color: "#dc2626" }}>${fmt(waste.wasted)}</p>
          </div>
          <div>
            <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase" }}>Saved with Sgraal</p>
            <p style={{ fontSize: "24px", fontWeight: 700, color: "#16a34a" }}>${fmt(waste.saved)}</p>
          </div>
          <div>
            <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase" }}>ROI</p>
            <p style={{ fontSize: "24px", fontWeight: 700, color: "#c9a962" }}>{waste.roi}x</p>
          </div>
        </div>
      </div>

      {/* Domain Table */}
      <div style={{ ...CARD, marginBottom: "24px" }}>
        <h2 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "12px" }}>Domain Breakdown</h2>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              {["Domain", "Decisions", "Avg Omega", "Block Rate"].map((h) => (
                <th key={h} style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", padding: "8px 16px", textAlign: "left", borderBottom: "1px solid #e5e7eb", letterSpacing: "0.05em" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {summary.domain_breakdown.map((row) => (
              <tr key={row.domain}>
                <td style={{ padding: "12px 16px", fontSize: "14px", fontWeight: 600, borderBottom: "1px solid #f5f4f0" }}>{row.domain}</td>
                <td style={{ padding: "12px 16px", fontSize: "14px", borderBottom: "1px solid #f5f4f0" }}>{fmt(row.decisions)}</td>
                <td style={{ padding: "12px 16px", fontSize: "14px", borderBottom: "1px solid #f5f4f0", color: row.avg_omega > 40 ? "#dc2626" : row.avg_omega > 25 ? "#c9a962" : "#16a34a" }}>{row.avg_omega}</td>
                <td style={{ padding: "12px 16px", fontSize: "14px", borderBottom: "1px solid #f5f4f0" }}>{row.block_rate}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Daily Chart */}
      <div style={CARD}>
        <h2 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "16px" }}>Daily Decisions (Last 7 Days)</h2>
        <div style={{ display: "flex", alignItems: "flex-end", gap: "12px", height: "160px" }}>
          {summary.daily.map((d) => (
            <div key={d.label} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center" }}>
              <span style={{ fontSize: "11px", fontWeight: 600, color: "#0B0F14", marginBottom: "4px" }}>{fmt(d.value)}</span>
              <div style={{ width: "100%", height: `${(d.value / maxDaily) * 120}px`, background: "linear-gradient(180deg, #c9a962, #745b1c)", borderRadius: "4px 4px 0 0", transition: "height 0.6s ease" }} />
              <span style={{ fontSize: "12px", color: "#6b7280", marginTop: "6px" }}>{d.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
