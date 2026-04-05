"use client";

import { useState, useEffect, useCallback } from "react";
import { getApiKey, getApiUrl } from "../lib/storage";
import { LoadingSkeleton, ConnectKeyState } from "../components/LoadingSkeleton";

interface Summary {
  total_calls: number;
  block_rate: number;
  avg_omega: number;
  trend: string | null;
}

interface WastefulEntry {
  entry_id: string;
  estimated_tokens: number;
  omega: number;
}

interface TokenWaste {
  blocked_retrievals: number;
  warn_retrievals: number;
  estimated_tokens_wasted: number;
  estimated_cost_usd: number;
  savings_if_filtered: number;
  roi_multiple: number;
  top_wasteful_entries: WastefulEntry[];
  recommendation: string;
}

const CARD: React.CSSProperties = { background: "#ffffff", borderRadius: "8px", padding: "20px", boxShadow: "0 1px 3px rgba(0,0,0,0.06)" };

export default function AnalyticsPage() {
  const [mounted, setMounted] = useState(false);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [waste, setWaste] = useState<TokenWaste | null>(null);
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
    const h = { Authorization: `Bearer ${apiKey}` };
    try {
      const [sR, wR] = await Promise.all([
        fetch(`${apiUrl}/v1/analytics/summary`, { headers: h }),
        fetch(`${apiUrl}/v1/analytics/token-waste`, { headers: h }),
      ]);
      if (sR.ok) setSummary(await sR.json());
      if (wR.ok) setWaste(await wR.json());
    } catch {}
    setLoading(false);
    setLastUpdated(new Date());
  }, []);

  useEffect(() => { load(); const i = setInterval(load, 60000); return () => clearInterval(i); }, [load]);
  useEffect(() => {
    function tick() { const s = Math.floor((Date.now() - lastUpdated.getTime()) / 1000); setTimeAgo(s < 5 ? "just now" : s < 60 ? `${s}s ago` : `${Math.floor(s / 60)}m ago`); }
    tick(); const i = setInterval(tick, 1000); return () => clearInterval(i);
  }, [lastUpdated]);

  if (!mounted) return null;

  if (!hasKey) return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Analytics</h1>
      <p className="text-muted text-sm mb-6">Fleet-wide decision analytics and token waste tracking.</p>
      <ConnectKeyState />
    </div>
  );

  if (loading) return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Analytics</h1>
      <p className="text-muted text-sm mb-6">Fleet-wide decision analytics and token waste tracking.</p>
      <LoadingSkeleton rows={5} />
    </div>
  );

  if (!summary || !waste) return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Analytics</h1>
      <p className="text-muted text-sm mb-6">Fleet-wide decision analytics and token waste tracking.</p>
      <div style={{ textAlign: "center", padding: "60px 0" }}>
        <p style={{ fontSize: "36px", color: "#6b7280" }}>&#x2014;</p>
        <p className="text-sm text-muted mt-2">Analytics data unavailable. Make preflight calls to generate statistics.</p>
      </div>
    </div>
  );

  const fmt = (n: number) => n.toLocaleString();
  const fmtUsd = (n: number) => `$${n.toFixed(2)}`;
  const omegaLabel = summary.avg_omega < 30 ? "Low" : summary.avg_omega < 60 ? "Medium" : "High";
  const omegaColor = summary.avg_omega < 30 ? "#16a34a" : summary.avg_omega < 60 ? "#c9a962" : "#dc2626";
  const trendLabel = summary.trend ?? "stable";

  // Derive decision breakdown from waste data
  const totalDecisions = summary.total_calls || 1;
  const blockPct = summary.block_rate ?? 0;
  const warnPct = totalDecisions > 0 ? Math.round((waste.warn_retrievals / totalDecisions) * 100) : 0;
  const usePct = Math.max(0, 100 - blockPct - warnPct);

  const decisions = [
    { key: "USE_MEMORY", pct: usePct, color: "#16a34a" },
    { key: "WARN", pct: warnPct, color: "#eab308" },
    { key: "BLOCK", pct: blockPct, color: "#dc2626" },
  ];

  const wastefulEntries = waste.top_wasteful_entries ?? [];

  return (
    <div>
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold mb-1">Analytics</h1>
          <p className="text-muted text-sm">Fleet-wide decision analytics and token waste tracking.</p>
        </div>
        <p style={{ fontSize: "12px", color: "#6b7280" }}>Updated {timeAgo}</p>
      </div>

      {/* KPI Row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "16px", marginBottom: "24px" }}>
        <div style={CARD}>
          <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em" }}>Total Decisions</p>
          <p style={{ fontSize: "28px", fontWeight: 700, color: "#0B0F14", marginTop: "4px" }}>{fmt(summary.total_calls)}</p>
          <p style={{ fontSize: "12px", color: "#6b7280", marginTop: "4px" }}>Trend: {trendLabel}</p>
        </div>
        <div style={CARD}>
          <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em" }}>Block Rate</p>
          <p style={{ fontSize: "28px", fontWeight: 700, color: blockPct > 20 ? "#dc2626" : "#0B0F14", marginTop: "4px" }}>{blockPct}%</p>
          <p style={{ fontSize: "12px", color: "#6b7280", marginTop: "4px" }}>{waste.blocked_retrievals} blocked calls</p>
        </div>
        <div style={CARD}>
          <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em" }}>Avg Omega Score</p>
          <p style={{ fontSize: "28px", fontWeight: 700, color: omegaColor, marginTop: "4px" }}>{summary.avg_omega}</p>
          <p style={{ fontSize: "12px", color: "#6b7280", marginTop: "4px" }}>Fleet risk: {omegaLabel}</p>
        </div>
        <div style={CARD}>
          <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em" }}>Savings Potential</p>
          <p style={{ fontSize: "28px", fontWeight: 700, color: "#0B0F14", marginTop: "4px" }}>{fmtUsd(waste.savings_if_filtered)}</p>
          <p style={{ fontSize: "12px", color: "#c9a962", marginTop: "4px" }}>{waste.roi_multiple}x ROI</p>
        </div>
      </div>

      {/* Decision Breakdown */}
      <div style={{ ...CARD, marginBottom: "24px" }}>
        <h2 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "16px" }}>Decision Breakdown</h2>
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {decisions.map(({ key, pct, color }) => (
            <div key={key} style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <span style={{ width: "100px", fontSize: "13px", fontFamily: "monospace", color: "#0B0F14" }}>{key}</span>
              <div style={{ flex: 1, height: "20px", background: "#f5f4f0", borderRadius: "4px", overflow: "hidden" }}>
                <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: "4px", transition: "width 0.8s ease" }} />
              </div>
              <span style={{ width: "40px", fontSize: "13px", fontWeight: 600, textAlign: "right" }}>{pct}%</span>
            </div>
          ))}
        </div>
      </div>

      {/* Token Waste Widget */}
      <div style={{ ...CARD, marginBottom: "24px", background: "rgba(201,169,98,0.06)", border: "1px solid rgba(201,169,98,0.2)" }}>
        <h2 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "12px" }}>Token Waste Analysis</h2>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: "16px" }}>
          <div>
            <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase" }}>Tokens Wasted</p>
            <p style={{ fontSize: "24px", fontWeight: 700, color: "#dc2626" }}>{fmt(waste.estimated_tokens_wasted)}</p>
          </div>
          <div>
            <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase" }}>Cost</p>
            <p style={{ fontSize: "24px", fontWeight: 700, color: "#dc2626" }}>{fmtUsd(waste.estimated_cost_usd)}</p>
          </div>
          <div>
            <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase" }}>Savings if Filtered</p>
            <p style={{ fontSize: "24px", fontWeight: 700, color: "#16a34a" }}>{fmtUsd(waste.savings_if_filtered)}</p>
          </div>
          <div>
            <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase" }}>ROI</p>
            <p style={{ fontSize: "24px", fontWeight: 700, color: "#c9a962" }}>{waste.roi_multiple}x</p>
          </div>
        </div>
        {waste.recommendation && (
          <p style={{ fontSize: "13px", color: "#6b7280", marginTop: "12px", fontStyle: "italic" }}>{waste.recommendation}</p>
        )}
      </div>

      {/* Top Wasteful Entries */}
      {wastefulEntries.length > 0 && (
        <div style={{ ...CARD, marginBottom: "24px" }}>
          <h2 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "12px" }}>Top Wasteful Entries</h2>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                {["Entry ID", "Est. Tokens", "Omega"].map((h) => (
                  <th key={h} style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", padding: "8px 16px", textAlign: "left", borderBottom: "1px solid #e5e7eb", letterSpacing: "0.05em" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {wastefulEntries.map((e) => (
                <tr key={e.entry_id}>
                  <td style={{ padding: "12px 16px", fontSize: "14px", fontFamily: "monospace", fontWeight: 600, borderBottom: "1px solid #f5f4f0" }}>{e.entry_id}</td>
                  <td style={{ padding: "12px 16px", fontSize: "14px", borderBottom: "1px solid #f5f4f0" }}>{fmt(e.estimated_tokens)}</td>
                  <td style={{ padding: "12px 16px", fontSize: "14px", fontWeight: 600, borderBottom: "1px solid #f5f4f0", color: e.omega > 60 ? "#dc2626" : e.omega > 30 ? "#c9a962" : "#16a34a" }}>{e.omega}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
