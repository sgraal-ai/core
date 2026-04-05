"use client";

import { useState, useEffect, useCallback, Fragment } from "react";
import { getApiKey, getApiUrl } from "../lib/storage";
import { LoadingSkeleton, ConnectKeyState } from "../components/LoadingSkeleton";

interface AuditEntry {
  timestamp: string;
  agent_id: string;
  domain: string;
  action_type: string;
  omega: number;
  decision: string;
  request_id: string;
  component_breakdown?: Record<string, number>;
  repair_plan?: string[];
  explainability_note?: string;
}

const DECISION_BADGE: Record<string, { bg: string; color: string }> = {
  BLOCK: { bg: "#fee2e2", color: "#dc2626" },
  WARN: { bg: "#fef9c3", color: "#a16207" },
  ASK_USER: { bg: "#ffedd5", color: "#c2410c" },
  USE_MEMORY: { bg: "#dcfce7", color: "#16a34a" },
};

type SortKey = "timestamp" | "agent_id" | "domain" | "omega" | "decision";
const TH: React.CSSProperties = { fontSize: "12px", color: "#6b7280", textTransform: "uppercase", padding: "8px 16px", textAlign: "left", borderBottom: "1px solid #e5e7eb", letterSpacing: "0.05em", cursor: "pointer", userSelect: "none" };
const TD: React.CSSProperties = { fontSize: "14px", color: "#0B0F14", padding: "12px 16px", borderBottom: "1px solid #f5f4f0" };
const SEL: React.CSSProperties = { background: "#ffffff", border: "1px solid #e5e7eb", borderRadius: "6px", padding: "8px 12px", fontSize: "14px", color: "#0B0F14" };

export default function AuditPage() {
  const [mounted, setMounted] = useState(false);
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [hasKey, setHasKey] = useState(false);
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState("7d");
  const [agentFilter, setAgentFilter] = useState("");
  const [decisionFilter, setDecisionFilter] = useState("");
  const [domainFilter, setDomainFilter] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("timestamp");
  const [sortAsc, setSortAsc] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [totalCount, setTotalCount] = useState(0);
  const perPage = 50;

  const load = useCallback(async () => {
    setMounted(true);
    const apiKey = getApiKey();
    setHasKey(!!apiKey);
    if (!apiKey) { setLoading(false); return; }
    const apiUrl = getApiUrl();
    try {
      const params = new URLSearchParams({ limit: String(perPage), offset: String(page * perPage) });
      if (agentFilter) params.set("agent_id", agentFilter);
      if (decisionFilter) params.set("decision", decisionFilter);
      if (domainFilter) params.set("domain", domainFilter);
      if (dateRange) params.set("range", dateRange);
      const res = await fetch(`${apiUrl}/v1/audit-log?${params}`, { headers: { Authorization: `Bearer ${apiKey}` } });
      if (res.ok) { const d = await res.json(); const parsed = Array.isArray(d) ? d : d.entries ?? []; setEntries(parsed); setTotalCount(d.count ?? parsed.length); }
    } catch {}
    setLoading(false);
  }, [agentFilter, decisionFilter, domainFilter, page, dateRange]);

  useEffect(() => { load(); }, [load]);

  function handleSort(key: SortKey) {
    if (sortKey === key) setSortAsc(!sortAsc); else { setSortKey(key); setSortAsc(true); }
  }

  const sorted = [...entries].sort((a, b) => {
    const av = a[sortKey], bv = b[sortKey];
    const cmp = typeof av === "number" && typeof bv === "number" ? av - bv : String(av).localeCompare(String(bv));
    return sortAsc ? cmp : -cmp;
  });

  const totalEntries = totalCount;

  async function exportCsv() {
    const apiKey = getApiKey();
    if (!apiKey) return;
    const apiUrl = getApiUrl();
    try {
      const res = await fetch(`${apiUrl}/v1/audit-log/export?format=csv`, {
        headers: { Authorization: `Bearer ${apiKey}` },
      });
      if (!res.ok) return;
      const data = await res.json();
      const content = (data.data ?? []).join("\n");
      const blob = new Blob([content], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "sgraal-audit-export.csv";
      a.click();
      URL.revokeObjectURL(url);
    } catch {}
  }

  if (!mounted) return null;

  if (!hasKey) return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Audit Log</h1>
      <p className="text-muted text-sm mb-6">View, search, and export preflight decision history.</p>
      <ConnectKeyState />
    </div>
  );

  if (loading) return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Audit Log</h1>
      <p className="text-muted text-sm mb-6">View, search, and export preflight decision history.</p>
      <LoadingSkeleton rows={6} />
    </div>
  );

  const HEADERS: [string, string][] = [["timestamp", "Timestamp"], ["agent_id", "Agent ID"], ["domain", "Domain"], ["action_type", "Action Type"], ["omega", "Omega"], ["decision", "Decision"], ["request_id", "Request ID"]];

  return (
    <div>
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold mb-1">Audit Log</h1>
          <p className="text-muted text-sm">View, search, and export preflight decision history.</p>
        </div>
      </div>

      {/* Filters */}
      <div style={{ display: "flex", gap: "12px", marginBottom: "24px", flexWrap: "wrap", alignItems: "center" }}>
        <select value={dateRange} onChange={(e) => setDateRange(e.target.value)} style={SEL}>
          <option value="24h">Last 24h</option><option value="7d">Last 7 days</option><option value="30d">Last 30 days</option>
        </select>
        <input type="text" placeholder="Agent ID..." value={agentFilter} onChange={(e) => setAgentFilter(e.target.value)} style={{ ...SEL, width: "180px" }} />
        <select value={decisionFilter} onChange={(e) => setDecisionFilter(e.target.value)} style={SEL}>
          <option value="">All decisions</option><option value="BLOCK">BLOCK</option><option value="WARN">WARN</option><option value="ASK_USER">ASK_USER</option><option value="USE_MEMORY">USE_MEMORY</option>
        </select>
        <select value={domainFilter} onChange={(e) => setDomainFilter(e.target.value)} style={SEL}>
          <option value="">All domains</option><option value="fintech">fintech</option><option value="healthcare">healthcare</option><option value="legal">legal</option><option value="coding">coding</option><option value="customer_support">customer_support</option><option value="general">general</option>
        </select>
        <button onClick={exportCsv} style={{ background: "#c9a962", color: "#0B0F14", fontWeight: 600, padding: "8px 16px", borderRadius: "6px", fontSize: "14px", border: "none", cursor: "pointer" }}>Export CSV</button>
      </div>

      {/* Table */}
      <div style={{ background: "#ffffff", borderRadius: "8px", boxShadow: "0 1px 3px rgba(0,0,0,0.06)", overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              {HEADERS.map(([key, label]) => (
                <th key={key} style={TH} onClick={() => ["timestamp", "agent_id", "domain", "omega", "decision"].includes(key) ? handleSort(key as SortKey) : null}>
                  {label} {sortKey === key ? (sortAsc ? "↑" : "↓") : ""}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((entry) => {
              const badge = DECISION_BADGE[entry.decision] || { bg: "#f3f4f6", color: "#6b7280" };
              const isExp = expandedId === entry.request_id;
              return (
                <Fragment key={entry.request_id}>
                  <tr onClick={() => setExpandedId(isExp ? null : entry.request_id)} style={{ cursor: "pointer" }} onMouseEnter={(e) => (e.currentTarget.style.background = "#faf9f6")} onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
                    <td style={{ ...TD, fontFamily: "monospace", fontSize: "13px" }}>{entry.timestamp}</td>
                    <td style={{ ...TD, fontFamily: "monospace", fontWeight: 600 }}>{entry.agent_id}</td>
                    <td style={TD}>{entry.domain}</td>
                    <td style={TD}>{entry.action_type}</td>
                    <td style={{ ...TD, color: entry.omega > 60 ? "#dc2626" : entry.omega > 30 ? "#c9a962" : "#16a34a", fontWeight: 600 }}>{entry.omega}</td>
                    <td style={TD}><span style={{ background: badge.bg, color: badge.color, borderRadius: "20px", padding: "2px 10px", fontSize: "12px", fontWeight: 600 }}>{entry.decision}</span></td>
                    <td style={{ ...TD, fontFamily: "monospace", fontSize: "12px", color: "#6b7280" }}>{entry.request_id}</td>
                  </tr>
                  {isExp && (
                    <tr>
                      <td colSpan={7} style={{ padding: "16px 24px", background: "#faf9f6", borderBottom: "1px solid #e5e7eb" }}>
                        {entry.component_breakdown && (
                          <div style={{ marginBottom: "12px" }}>
                            <p style={{ fontSize: "11px", color: "#6b7280", textTransform: "uppercase", marginBottom: "8px" }}>Component Breakdown</p>
                            <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "8px" }}>
                              {Object.entries(entry.component_breakdown).map(([k, v]) => (
                                <div key={k}>
                                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "#6b7280", marginBottom: "2px" }}><span>{k}</span><span>{v}</span></div>
                                  <div style={{ height: "4px", background: "#e5e7eb", borderRadius: "2px", overflow: "hidden" }}>
                                    <div style={{ width: `${v}%`, height: "100%", background: v > 60 ? "#dc2626" : v > 30 ? "#c9a962" : "#16a34a", borderRadius: "2px" }} />
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                        {entry.repair_plan && entry.repair_plan.length > 0 && (
                          <div style={{ marginBottom: "12px" }}>
                            <p style={{ fontSize: "11px", color: "#6b7280", textTransform: "uppercase", marginBottom: "4px" }}>Repair Plan</p>
                            <ul style={{ fontSize: "13px", color: "#0B0F14", paddingLeft: "16px" }}>{entry.repair_plan.map((r, i) => <li key={i}>{r}</li>)}</ul>
                          </div>
                        )}
                        {entry.explainability_note && (
                          <div>
                            <p style={{ fontSize: "11px", color: "#6b7280", textTransform: "uppercase", marginBottom: "4px" }}>Explanation</p>
                            <p style={{ fontSize: "13px", color: "#0B0F14" }}>{entry.explainability_note}</p>
                          </div>
                        )}
                        {!entry.component_breakdown && !entry.repair_plan && !entry.explainability_note && (
                          <p style={{ fontSize: "13px", color: "#6b7280" }}>No additional details available.</p>
                        )}
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>

      {totalCount > 0 ? (
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "16px" }}>
          <p style={{ fontSize: "13px", color: "#6b7280" }}>Showing {page * perPage + 1}-{Math.min((page + 1) * perPage, totalEntries)} of {totalEntries.toLocaleString()} entries</p>
          <div style={{ display: "flex", gap: "8px" }}>
            <button disabled={page === 0} onClick={() => setPage(page - 1)} style={{ padding: "6px 14px", borderRadius: "6px", border: "1px solid #e5e7eb", fontSize: "13px", cursor: page === 0 ? "not-allowed" : "pointer", opacity: page === 0 ? 0.4 : 1 }}>Previous</button>
            <button disabled={(page + 1) * perPage >= totalCount} onClick={() => setPage(page + 1)} style={{ padding: "6px 14px", borderRadius: "6px", border: "1px solid #e5e7eb", fontSize: "13px", cursor: (page + 1) * perPage >= totalCount ? "not-allowed" : "pointer", opacity: (page + 1) * perPage >= totalCount ? 0.4 : 1 }}>Next</button>
          </div>
        </div>
      ) : (
        <p className="text-sm text-muted text-center mt-4">No audit entries found.</p>
      )}
    </div>
  );
}
