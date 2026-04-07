"use client";

import { useState, useEffect, useCallback } from "react";
import { getApiKey, getApiUrl } from "../lib/storage";
import { LoadingSkeleton, ConnectKeyState } from "../components/LoadingSkeleton";

interface Summary {
  total_calls: number;
  block_rate: number;
  avg_omega: number;
  trend: string | null;
  first_preflight_at?: string;
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
  const [auditEntries, setAuditEntries] = useState<Array<Record<string, unknown>>>([]);
  const [memTypes, setMemTypes] = useState<Record<string, number> | null>(null);
  const [repairEff, setRepairEff] = useState<Record<string, unknown> | null>(null);
  const [projVolume, setProjVolume] = useState(100000);

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
    // Fetch audit entries for domain/agent breakdown
    try {
      const aR = await fetch(`${apiUrl}/v1/audit-log?limit=500`, { headers: h });
      if (aR.ok) { const d = await aR.json(); setAuditEntries(d.entries ?? []); }
    } catch {}
    // Fetch memory type distribution and repair effectiveness
    try {
      const [mtR, reR] = await Promise.all([
        fetch(`${apiUrl}/v1/analytics/memory-types`, { headers: h }),
        fetch(`${apiUrl}/v1/repair/effectiveness`, { headers: h }),
      ]);
      if (mtR.ok) { const d = await mtR.json(); setMemTypes(d.distribution ?? null); }
      if (reR.ok) setRepairEff(await reR.json());
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

  // Derive fleet KPIs from audit log data (primary source) with API summary as fallback
  const auditTotal = auditEntries.length;
  const auditBlocks = auditEntries.filter(e => e.decision === "BLOCK").length;
  const auditWarns = auditEntries.filter(e => e.decision === "WARN" || e.decision === "ASK_USER").length;
  const auditUse = auditEntries.filter(e => e.decision === "USE_MEMORY").length;
  const auditOmegaSum = auditEntries.reduce((s, e) => s + Number(e.omega_mem_final ?? 0), 0);

  const totalDecisions = auditTotal > 0 ? auditTotal : (summary?.total_calls ?? 0);
  const blockPct = totalDecisions > 0 ? Math.round((auditBlocks / totalDecisions) * 100) : (summary?.block_rate ?? 0);
  const warnPct = totalDecisions > 0 ? Math.round((auditWarns / totalDecisions) * 100) : 0;
  const usePct = totalDecisions > 0 ? Math.round((auditUse / totalDecisions) * 100) : Math.max(0, 100 - blockPct - warnPct);
  const avgOmega = totalDecisions > 0 ? Math.round(auditOmegaSum / totalDecisions * 10) / 10 : (summary?.avg_omega ?? 0);

  if (!loading && totalDecisions === 0 && !summary && !waste) return (
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
  const omegaLabel = avgOmega < 30 ? "Low" : avgOmega < 60 ? "Medium" : "High";
  const omegaColor = avgOmega < 30 ? "#16a34a" : avgOmega < 60 ? "#c9a962" : "#dc2626";
  const trendLabel = summary?.trend ?? "stable";

  const askUserCount = auditEntries.filter(e => e.decision === "ASK_USER").length;
  const askUserPct = totalDecisions > 0 ? Math.round((askUserCount / totalDecisions) * 100) : 0;
  const decisions = [
    { key: "USE_MEMORY", pct: usePct, count: auditUse, color: "#16a34a" },
    { key: "WARN", pct: warnPct, count: auditWarns - askUserCount, color: "#ca8a04" },
    { key: "ASK_USER", pct: askUserPct, count: askUserCount, color: "#2563eb" },
    { key: "BLOCK", pct: blockPct, count: auditBlocks, color: "#dc2626" },
  ];

  const wastefulEntries = waste?.top_wasteful_entries ?? [];

  return (
    <div>
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold mb-1">Analytics</h1>
          <p className="text-muted text-sm">Fleet-wide decision analytics and token waste tracking.</p>
        </div>
        <p style={{ fontSize: "12px", color: "#6b7280" }}>Updated {timeAgo}</p>
      </div>

      {/* Top Issues */}
      {totalDecisions > 0 && (() => {
        const issues: { title: string; desc: string; domain: string; severity: "red" | "amber" }[] = [];
        // Per-domain analysis
        const byDom: Record<string, { total: number; block: number; warn: number; askUser: number }> = {};
        for (const e of auditEntries) {
          const d = String(e.domain || "unknown");
          if (!byDom[d]) byDom[d] = { total: 0, block: 0, warn: 0, askUser: 0 };
          byDom[d].total++;
          if (e.decision === "BLOCK") byDom[d].block++;
          if (e.decision === "WARN") byDom[d].warn++;
          if (e.decision === "ASK_USER") byDom[d].askUser++;
        }
        for (const [dom, s] of Object.entries(byDom)) {
          const br = s.total > 0 ? s.block / s.total : 0;
          const wr = s.total > 0 ? s.warn / s.total : 0;
          const ar = s.total > 0 ? s.askUser / s.total : 0;
          if (br > 0.4) issues.push({ title: `High BLOCK rate in ${dom}`, desc: `${Math.round(br * 100)}% of calls blocked — likely stale or conflicting memory`, domain: dom, severity: br > 0.7 ? "red" : "amber" });
          else if (wr > 0.3) issues.push({ title: `Elevated WARN rate in ${dom}`, desc: `${Math.round(wr * 100)}% warnings — consider tuning thresholds`, domain: dom, severity: "amber" });
          if (ar > 0.2) issues.push({ title: `Repeated ASK_USER in ${dom}`, desc: `${Math.round(ar * 100)}% require human review — automate or adjust policies`, domain: dom, severity: "amber" });
        }
        if (avgOmega > 50) issues.push({ title: "Fleet-wide high risk", desc: `Average omega ${avgOmega} — systematic memory quality issue`, domain: "all", severity: "red" });
        const top3 = issues.sort((a, b) => (a.severity === "red" ? 0 : 1) - (b.severity === "red" ? 0 : 1)).slice(0, 3);
        if (top3.length === 0) return null;
        return (
          <div style={{ display: "flex", gap: "12px", marginBottom: "24px", flexWrap: "wrap" }}>
            {top3.map((issue, i) => (
              <div key={i} style={{ ...CARD, flex: "1 1 280px", borderLeft: `4px solid ${issue.severity === "red" ? "#dc2626" : "#c9a962"}` }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                  <span style={{ fontSize: "14px" }}>{issue.severity === "red" ? "\uD83D\uDD34" : "\u26A0\uFE0F"}</span>
                  <span style={{ fontSize: "14px", fontWeight: 700, color: "#0B0F14" }}>{issue.title}</span>
                </div>
                <p style={{ fontSize: "13px", color: "#6b7280", marginBottom: "6px" }}>{issue.desc}</p>
                <span style={{ background: "#f3f4f6", color: "#6b7280", borderRadius: "20px", padding: "2px 8px", fontSize: "11px" }}>{issue.domain}</span>
              </div>
            ))}
          </div>
        );
      })()}

      {/* KPI Row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "16px", marginBottom: "24px" }}>
        <div style={CARD}>
          <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em" }}>Total Decisions</p>
          <p style={{ fontSize: "28px", fontWeight: 700, color: "#0B0F14", marginTop: "4px" }}>{fmt(totalDecisions)}</p>
          <p style={{ fontSize: "12px", color: "#6b7280", marginTop: "4px" }}>Trend: {trendLabel}</p>
        </div>
        <div style={CARD}>
          <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em" }}>Block Rate</p>
          <p style={{ fontSize: "28px", fontWeight: 700, color: blockPct > 20 ? "#dc2626" : "#0B0F14", marginTop: "4px" }}>{blockPct}%</p>
          <p style={{ fontSize: "12px", color: "#6b7280", marginTop: "4px" }}>{auditBlocks} blocked calls</p>
        </div>
        <div style={CARD}>
          <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em" }}>Avg Omega Score</p>
          <p style={{ fontSize: "28px", fontWeight: 700, color: omegaColor, marginTop: "4px" }}>{avgOmega}</p>
          <p style={{ fontSize: "12px", color: "#6b7280", marginTop: "4px" }}>Fleet risk: {omegaLabel}</p>
        </div>
        <div style={CARD}>
          <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em" }}>Risk Prevention</p>
          <p style={{ fontSize: "28px", fontWeight: 700, color: "#0B0F14", marginTop: "4px" }}>Prevented {auditBlocks} unsafe</p>
          <p style={{ fontSize: "12px", color: blockPct > 50 ? "#dc2626" : blockPct > 20 ? "#c9a962" : "#16a34a", fontWeight: 600, marginTop: "4px" }}>Estimated risk avoided: {blockPct > 50 ? "HIGH" : blockPct > 20 ? "MEDIUM" : "LOW"}</p>
        </div>
        {(() => {
          const estWaste = auditBlocks * 1200 + (auditWarns - askUserCount) * 400;
          const wasteColor = estWaste > 200000 ? "#dc2626" : estWaste > 50000 ? "#c9a962" : "#16a34a";
          return (
            <div style={CARD}>
              <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em" }}>Est. Token Waste</p>
              <p style={{ fontSize: "28px", fontWeight: 700, color: wasteColor, marginTop: "4px" }}>{fmt(estWaste)}</p>
              <p style={{ fontSize: "12px", color: "#6b7280", marginTop: "4px" }}>from blocked &amp; warned calls</p>
            </div>
          );
        })()}
      </div>

      {/* Decision Breakdown */}
      <div style={{ ...CARD, marginBottom: "24px" }}>
        <h2 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "16px" }}>Decision Breakdown</h2>
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {decisions.map(({ key, pct, count, color }) => (
            <div key={key} style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <span style={{ width: "100px", fontSize: "13px", fontFamily: "monospace", color: "#0B0F14" }}>{key}</span>
              <div style={{ flex: 1, height: "20px", background: "#f5f4f0", borderRadius: "4px", overflow: "hidden" }}>
                <div style={{ width: `${Math.max(pct, 1)}%`, height: "100%", background: color, borderRadius: "4px", transition: "width 0.8s ease" }} />
              </div>
              <span style={{ width: "80px", fontSize: "13px", fontWeight: 600, textAlign: "right" }}>{pct}% <span style={{ color: "#6b7280", fontWeight: 400 }}>({count})</span></span>
            </div>
          ))}
        </div>
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
                  <td style={{ padding: "12px 16px", fontSize: "14px", fontFamily: "monospace", fontWeight: 600, borderBottom: "1px solid #f5f4f0" }}>{/^high_omega_\d+$/.test(e.entry_id) ? `Memory entry ${Number(e.entry_id.split("_").pop()) + 1}` : e.entry_id.length > 12 ? e.entry_id.slice(0, 12) + "..." : e.entry_id}</td>
                  <td style={{ padding: "12px 16px", fontSize: "14px", borderBottom: "1px solid #f5f4f0" }}>{fmt(e.estimated_tokens)}</td>
                  <td style={{ padding: "12px 16px", fontSize: "14px", fontWeight: 600, borderBottom: "1px solid #f5f4f0", color: e.omega > 60 ? "#dc2626" : e.omega > 30 ? "#c9a962" : "#16a34a" }}>{e.omega}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {/* Domain Breakdown */}
      {auditEntries.length > 0 && (() => {
        const byDomain: Record<string, { total: number; block: number; warn: number; use: number; omegaSum: number }> = {};
        for (const e of auditEntries) {
          const d = String(e.domain || "unknown");
          if (!byDomain[d]) byDomain[d] = { total: 0, block: 0, warn: 0, use: 0, omegaSum: 0 };
          byDomain[d].total++;
          if (e.decision === "BLOCK") byDomain[d].block++;
          else if (e.decision === "WARN" || e.decision === "ASK_USER") byDomain[d].warn++;
          else byDomain[d].use++;
          byDomain[d].omegaSum += Number(e.omega_mem_final ?? 0);
        }
        const rows = Object.entries(byDomain).map(([domain, s]) => ({
          domain, total: s.total,
          blockPct: s.total > 0 ? Math.round((s.block / s.total) * 100) : 0,
          warnPct: s.total > 0 ? Math.round((s.warn / s.total) * 100) : 0,
          usePct: s.total > 0 ? Math.round((s.use / s.total) * 100) : 0,
          avgOmega: s.total > 0 ? Math.round(s.omegaSum / s.total * 10) / 10 : 0,
        })).sort((a, b) => b.blockPct - a.blockPct);
        const TH: React.CSSProperties = { fontSize: "12px", color: "#6b7280", textTransform: "uppercase", padding: "8px 16px", textAlign: "left", borderBottom: "1px solid #e5e7eb", letterSpacing: "0.05em" };
        const TD: React.CSSProperties = { fontSize: "14px", padding: "12px 16px", borderBottom: "1px solid #f5f4f0" };
        return (
          <div style={{ ...CARD, marginTop: "24px" }}>
            <h2 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "4px" }}>Domain Breakdown</h2>
            <p className="text-sm text-muted mb-4">Domains with highest block rates may need threshold adjustment.</p>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead><tr>
                {["Domain", "Calls", "BLOCK %", "WARN %", "USE %", "Avg Omega", "Rec."].map(h => <th key={h} style={TH}>{h}</th>)}
              </tr></thead>
              <tbody>
                {rows.map(r => (
                  <tr key={r.domain}>
                    <td style={{ ...TD, fontWeight: 600 }}>{r.domain}</td>
                    <td style={TD}>{r.total}</td>
                    <td style={{ ...TD, fontWeight: 600 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span style={{ color: r.blockPct > 70 ? "#dc2626" : r.blockPct > 30 ? "#c9a962" : "#16a34a", minWidth: "32px" }}>{r.blockPct}%</span>
                        <div style={{ width: "60px", height: "8px", background: "#f5f4f0", borderRadius: "4px", overflow: "hidden" }}>
                          <div style={{ width: `${r.blockPct}%`, height: "100%", background: r.blockPct > 70 ? "#dc2626" : r.blockPct > 30 ? "#c9a962" : "#16a34a", borderRadius: "4px" }} />
                        </div>
                      </div>
                    </td>
                    <td style={{ ...TD, color: r.warnPct > 20 ? "#c9a962" : "#6b7280" }}>{r.warnPct}%</td>
                    <td style={{ ...TD, color: "#16a34a" }}>{r.usePct}%</td>
                    <td style={{ ...TD, color: r.avgOmega > 50 ? "#dc2626" : r.avgOmega > 25 ? "#c9a962" : "#16a34a" }}>{r.avgOmega}</td>
                    <td style={{ ...TD, fontSize: "12px", color: "#6b7280" }}>
                      {r.blockPct > 70 ? <span style={{ color: "#dc2626" }}>Immediate attention</span>
                        : r.blockPct > 40 ? <span style={{ color: "#c9a962" }}>Review memory freshness</span>
                        : r.warnPct > 30 ? <span style={{ color: "#c9a962" }}>Tune thresholds</span>
                        : r.blockPct < 10 ? <span style={{ color: "#16a34a" }}>Healthy</span>
                        : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      })()}

      {/* Decision Trend — Last 7 Days */}
      {auditEntries.length > 0 && (() => {
        const now = new Date();
        const dayBuckets: { label: string; block: number; warn: number; total: number }[] = [];
        for (let d = 6; d >= 0; d--) {
          const date = new Date(now);
          date.setDate(date.getDate() - d);
          const key = date.toISOString().slice(0, 10);
          const label = date.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
          const dayEntries = auditEntries.filter(e => {
            try { const ts = String((e as Record<string, unknown>).timestamp ?? (e as Record<string, unknown>).created_at ?? ""); return ts.slice(0, 10) === key; } catch { return false; }
          });
          dayBuckets.push({
            label, total: dayEntries.length,
            block: dayEntries.filter(e => e.decision === "BLOCK").length,
            warn: dayEntries.filter(e => e.decision === "WARN" || e.decision === "ASK_USER").length,
          });
        }
        const maxTotal = Math.max(...dayBuckets.map(b => b.total), 1);
        const hasDayData = dayBuckets.some(b => b.total > 0);
        if (!hasDayData) return null;
        return (
          <div style={{ ...CARD, marginTop: "24px" }}>
            <h2 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "4px" }}>Decision Trend — Last 7 Days</h2>
            <p className="text-sm text-muted mb-4">Daily BLOCK and WARN rates across all agents.</p>
            <div style={{ display: "flex", alignItems: "flex-end", gap: "8px", height: "140px" }}>
              {dayBuckets.map((b, i) => {
                const blockH = b.total > 0 ? (b.block / maxTotal) * 120 : 0;
                const warnH = b.total > 0 ? (b.warn / maxTotal) * 120 : 0;
                return (
                  <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "flex-end", height: "100%" }}>
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "flex-end", flex: 1 }}>
                      {blockH > 0 && <div style={{ width: "100%", height: `${blockH}px`, background: "#dc2626", borderRadius: "3px 3px 0 0", minHeight: "2px" }} title={`BLOCK: ${b.block}`} />}
                      {warnH > 0 && <div style={{ width: "100%", height: `${warnH}px`, background: "#c9a962", minHeight: "2px" }} title={`WARN: ${b.warn}`} />}
                    </div>
                    <span style={{ fontSize: "10px", color: "#6b7280", marginTop: "6px", textAlign: "center", lineHeight: 1.2 }}>{b.label.split(",")[0]}</span>
                  </div>
                );
              })}
            </div>
            <div style={{ display: "flex", gap: "16px", marginTop: "12px", fontSize: "12px", color: "#6b7280" }}>
              <span><span style={{ display: "inline-block", width: "10px", height: "10px", background: "#dc2626", borderRadius: "2px", marginRight: "4px" }} />BLOCK</span>
              <span><span style={{ display: "inline-block", width: "10px", height: "10px", background: "#c9a962", borderRadius: "2px", marginRight: "4px" }} />WARN</span>
            </div>
          </div>
        );
      })()}

      {/* Agent Breakdown */}
      {auditEntries.length > 0 && (() => {
        const byAgent: Record<string, { total: number; block: number; omegaSum: number; lastDecision: string }> = {};
        for (const e of auditEntries) {
          const a = String(e.agent_id || "unknown");
          if (!byAgent[a]) byAgent[a] = { total: 0, block: 0, omegaSum: 0, lastDecision: "" };
          byAgent[a].total++;
          if (e.decision === "BLOCK") byAgent[a].block++;
          byAgent[a].omegaSum += Number(e.omega_mem_final ?? 0);
          byAgent[a].lastDecision = String(e.decision ?? "");
        }
        const rows = Object.entries(byAgent).map(([agent, s]) => ({
          agent, total: s.total,
          blockPct: s.total > 0 ? Math.round((s.block / s.total) * 100) : 0,
          avgOmega: s.total > 0 ? Math.round(s.omegaSum / s.total * 10) / 10 : 0,
          lastDecision: s.lastDecision,
        })).sort((a, b) => b.blockPct - a.blockPct);
        const TH: React.CSSProperties = { fontSize: "12px", color: "#6b7280", textTransform: "uppercase", padding: "8px 16px", textAlign: "left", borderBottom: "1px solid #e5e7eb", letterSpacing: "0.05em" };
        const TD: React.CSSProperties = { fontSize: "14px", padding: "12px 16px", borderBottom: "1px solid #f5f4f0" };
        const decisionColor: Record<string, string> = { BLOCK: "#dc2626", WARN: "#c9a962", ASK_USER: "#f97316", USE_MEMORY: "#16a34a" };
        return (
          <div style={{ ...CARD, marginTop: "24px" }}>
            <h2 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "4px" }}>Agent Breakdown</h2>
            <p className="text-sm text-muted mb-4">Agents with consistently high block rates may have stale or misconfigured memory.</p>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead><tr>
                {["Agent", "Calls", "BLOCK %", "Avg Omega", "Last Decision"].map(h => <th key={h} style={TH}>{h}</th>)}
              </tr></thead>
              <tbody>
                {rows.map(r => (
                  <tr key={r.agent}>
                    <td style={{ ...TD, fontFamily: "monospace", fontSize: "13px", fontWeight: 600 }}>{r.agent}</td>
                    <td style={TD}>{r.total}</td>
                    <td style={{ ...TD, color: r.blockPct > 20 ? "#dc2626" : "#6b7280", fontWeight: 600 }}>{r.blockPct}%</td>
                    <td style={{ ...TD, color: r.avgOmega > 50 ? "#dc2626" : r.avgOmega > 25 ? "#c9a962" : "#16a34a" }}>{r.avgOmega}</td>
                    <td style={TD}>
                      <span style={{ background: decisionColor[r.lastDecision] ? `${decisionColor[r.lastDecision]}20` : "#f3f4f6", color: decisionColor[r.lastDecision] || "#6b7280", borderRadius: "20px", padding: "2px 10px", fontSize: "12px", fontWeight: 600 }}>{r.lastDecision}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      })()}
      {/* Memory Type Distribution */}
      {memTypes && Object.keys(memTypes).length > 0 && (() => {
        const total = Object.values(memTypes).reduce((s, v) => s + v, 0);
        const maxCount = Math.max(...Object.values(memTypes), 1);
        return (
          <div style={{ ...CARD, marginTop: "24px" }}>
            <h2 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "4px" }}>Memory Type Distribution</h2>
            <p className="text-sm text-muted mb-4">Shows what kinds of memory your agents use most. High tool_state usage may indicate agents relying on volatile data.</p>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {Object.entries(memTypes).filter(([, v]) => v > 0).sort(([, a], [, b]) => b - a).map(([type, count]) => (
                <div key={type} style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                  <span style={{ width: "120px", fontSize: "13px", fontFamily: "monospace" }}>{type}</span>
                  <div style={{ flex: 1, height: "16px", background: "#f5f4f0", borderRadius: "4px", overflow: "hidden" }}>
                    <div style={{ width: `${(count / maxCount) * 100}%`, height: "100%", background: "#c9a962", borderRadius: "4px", transition: "width 0.6s ease" }} />
                  </div>
                  <span style={{ width: "60px", fontSize: "13px", fontWeight: 600, textAlign: "right" }}>{count}</span>
                  <span style={{ width: "40px", fontSize: "12px", color: "#6b7280", textAlign: "right" }}>{total > 0 ? Math.round((count / total) * 100) : 0}%</span>
                </div>
              ))}
            </div>
          </div>
        );
      })()}

      {/* Repair Effectiveness */}
      {repairEff && (
        <div style={{ ...CARD, marginTop: "24px" }}>
          <h2 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "4px" }}>Repair Effectiveness</h2>
          <p className="text-sm text-muted mb-4">How often suggested repairs are actually applied, and whether they improve memory health.</p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "16px" }}>
            <div>
              <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase" }}>Adoption Rate</p>
              <p style={{ fontSize: "28px", fontWeight: 700, color: Number(repairEff.avg_adoption_rate ?? 0) > 0.5 ? "#16a34a" : "#c9a962" }}>
                {Math.round(Number(repairEff.avg_adoption_rate ?? 0) * 100)}%
              </p>
            </div>
            <div>
              <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase" }}>Outcomes Tracked</p>
              <p style={{ fontSize: "28px", fontWeight: 700 }}>{Number(repairEff.count ?? 0)}</p>
            </div>
          </div>
          {Number(repairEff.count ?? 0) === 0 && (
            <p className="text-sm text-muted mt-3">No repair outcomes tracked yet — submit outcomes via agent detail to activate learning.</p>
          )}
        </div>
      )}

      {/* Per-Module Latency */}
      {auditEntries.length > 0 && (() => {
        // Get per_module_latency from the most recent audit entry that has it
        const latestWithLatency = auditEntries.find(e => e.per_module_latency && typeof e.per_module_latency === "object");
        if (!latestWithLatency) return null;
        const latency = latestWithLatency.per_module_latency as Record<string, number>;
        return (
          <div style={{ ...CARD, marginTop: "24px" }}>
            <h2 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "4px" }}>Per-Module Latency</h2>
            <p className="text-sm text-muted mb-4">Which scoring modules take the most time. High latency modules are candidates for optimization.</p>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              {Object.entries(latency).sort(([, a], [, b]) => b - a).map(([mod, ms]) => (
                <div key={mod} style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                  <span style={{ width: "160px", fontSize: "13px", fontFamily: "monospace" }}>{mod}</span>
                  <div style={{ flex: 1, height: "12px", background: "#f5f4f0", borderRadius: "3px", overflow: "hidden" }}>
                    <div style={{ width: `${Math.min((ms / Math.max(...Object.values(latency), 1)) * 100, 100)}%`, height: "100%", background: ms > 500 ? "#dc2626" : ms > 100 ? "#c9a962" : "#16a34a", borderRadius: "3px" }} />
                  </div>
                  <span style={{ width: "60px", fontSize: "13px", fontWeight: 600, textAlign: "right", color: ms > 500 ? "#dc2626" : "#6b7280" }}>{ms}ms</span>
                </div>
              ))}
            </div>
          </div>
        );
      })()}

      {/* Activation Funnel */}
      {summary?.first_preflight_at && (
        <div style={{ ...CARD, marginTop: "24px" }}>
          <h2 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "4px" }}>Activation Funnel</h2>
          <p className="text-sm text-muted mb-4">Time from API key creation to first preflight call. Track how quickly new users integrate.</p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "16px" }}>
            <div>
              <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase" }}>First Preflight</p>
              <p style={{ fontSize: "14px", fontFamily: "monospace" }}>{new Date(String(summary.first_preflight_at)).toLocaleString()}</p>
            </div>
            <div>
              <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase" }}>Time Active</p>
              <p style={{ fontSize: "14px", fontWeight: 600 }}>
                {(() => {
                  const diff = Date.now() - new Date(String(summary.first_preflight_at)).getTime();
                  const days = Math.floor(diff / 86400000);
                  const hours = Math.floor((diff % 86400000) / 3600000);
                  return days > 0 ? `${days}d ${hours}h` : `${hours}h`;
                })()}
              </p>
            </div>
            <div>
              <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase" }}>Total Decisions</p>
              <p style={{ fontSize: "14px", fontWeight: 600 }}>{fmt(totalDecisions)}</p>
            </div>
          </div>
        </div>
      )}
      {/* ROI Projection */}
      {totalDecisions > 0 && (() => {
        const projBlockRate = blockPct / 100;
        const projWarnRate = warnPct / 100;
        const projBlocked = Math.round(projVolume * projBlockRate);
        const estWastePerCall = totalDecisions > 0 ? (auditBlocks * 1200 + (auditWarns - askUserCount) * 400) / totalDecisions : 0;
        const projTokenSavings = Math.round(estWastePerCall * projVolume);
        return (
          <div style={{ ...CARD, marginTop: "24px", borderLeft: "4px solid #c9a962" }}>
            <h2 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "4px" }}>ROI Projection</h2>
            <p className="text-sm text-muted mb-4">Estimate impact at scale based on current decision patterns.</p>
            <div style={{ marginBottom: "16px" }}>
              <label style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", display: "block", marginBottom: "4px" }}>Monthly call volume</label>
              <input type="number" value={projVolume} onChange={(e) => setProjVolume(Math.max(0, Number(e.target.value) || 0))}
                style={{ background: "#ffffff", border: "1px solid #e5e7eb", borderRadius: "6px", padding: "8px 12px", fontSize: "14px", width: "200px" }} />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "16px" }}>
              <div>
                <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase" }}>Blocked Harmful Actions</p>
                <p style={{ fontSize: "24px", fontWeight: 700, color: "#dc2626" }}>{fmt(projBlocked)}</p>
              </div>
              <div>
                <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase" }}>Token Savings vs Unguarded</p>
                <p style={{ fontSize: "24px", fontWeight: 700, color: "#c9a962" }}>{fmt(projTokenSavings)}</p>
              </div>
              <div>
                <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase" }}>Compliance Events Prevented</p>
                <p style={{ fontSize: "24px", fontWeight: 700, color: "#16a34a" }}>{fmt(Math.round(projVolume * projWarnRate + projBlocked))}</p>
              </div>
            </div>
          </div>
        );
      })()}

      {/* Cost Analytics */}
      <div style={{ ...CARD, marginTop: "24px", borderLeft: "4px solid #c9a962" }}>
        <h2 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "4px" }}>Cost Analytics</h2>
        <p className="text-sm text-muted mb-4">Estimated API cost breakdown by decision type and projected spend.</p>
        {totalDecisions > 0 ? (() => {
          const costPerCall = 0.001; // $0.001 per preflight call
          const totalCost = totalDecisions * costPerCall;
          const blockCost = auditBlocks * costPerCall;
          const warnCost = (auditWarns - askUserCount) * costPerCall;
          const askCost = askUserCount * costPerCall;
          const useCost = auditUse * costPerCall;
          const projectedMonthly = totalCost * 30; // rough projection
          return (
            <div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "16px", marginBottom: "16px" }}>
                <div>
                  <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase" }}>Total Cost</p>
                  <p style={{ fontSize: "24px", fontWeight: 700, color: "#c9a962" }}>${totalCost.toFixed(2)}</p>
                </div>
                <div>
                  <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase" }}>BLOCK Cost</p>
                  <p style={{ fontSize: "18px", fontWeight: 700, color: "#dc2626" }}>${blockCost.toFixed(2)}</p>
                </div>
                <div>
                  <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase" }}>WARN Cost</p>
                  <p style={{ fontSize: "18px", fontWeight: 700, color: "#ca8a04" }}>${warnCost.toFixed(2)}</p>
                </div>
                <div>
                  <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase" }}>USE Cost</p>
                  <p style={{ fontSize: "18px", fontWeight: 700, color: "#16a34a" }}>${useCost.toFixed(2)}</p>
                </div>
              </div>
              <p style={{ fontSize: "13px", color: "#6b7280" }}>Projected 30-day spend: <strong style={{ color: "#c9a962" }}>${projectedMonthly.toFixed(2)}</strong> at current rate ({fmt(totalDecisions)} calls observed)</p>
            </div>
          );
        })() : (
          <p className="text-sm text-muted">Submit outcomes to unlock cost analytics.</p>
        )}
      </div>
    </div>
  );
}
