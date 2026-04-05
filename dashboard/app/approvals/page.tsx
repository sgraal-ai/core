"use client";

import { useState, useEffect, useCallback } from "react";
import { getApiKey, getApiUrl } from "../lib/storage";
import { LoadingSkeleton, ConnectKeyState } from "../components/LoadingSkeleton";

interface Approval {
  id: string;
  agent_id: string;
  action_type: string;
  domain: string;
  omega: number;
  explanation: string;
  memory_summary: string;
  timestamp: string;
}

interface HistoryRow {
  agent_id: string;
  action_type: string;
  omega: number;
  decision: "Approved" | "Rejected";
  timestamp: string;
}

function omegaBadgeStyle(omega: number): React.CSSProperties {
  const bg = omega <= 45 ? "rgba(22,163,74,0.1)" : omega <= 65 ? "rgba(234,136,0,0.1)" : "rgba(220,38,38,0.1)";
  const color = omega <= 45 ? "#16a34a" : omega <= 65 ? "#ea8800" : "#dc2626";
  return { background: bg, color, borderRadius: "20px", padding: "3px 10px", fontSize: "12px", fontWeight: 600 };
}

const TAG_STYLE: React.CSSProperties = {
  background: "rgba(201,169,98,0.1)",
  color: "#c9a962",
  borderRadius: "20px",
  padding: "3px 10px",
  fontSize: "12px",
};

export default function ApprovalsPage() {
  const [mounted, setMounted] = useState(false);
  const [pending, setPending] = useState<Approval[]>([]);
  const [history, setHistory] = useState<HistoryRow[]>([]);
  const [hasKey, setHasKey] = useState(false);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(new Date());
  const [timeAgo, setTimeAgo] = useState("just now");
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  const loadApprovals = useCallback(async () => {
    setMounted(true);
    const apiKey = getApiKey();
    setHasKey(!!apiKey);

    if (!apiKey) {
      setLoading(false);
      return;
    }

    try {
      const apiUrl = getApiUrl();
      const res = await fetch(`${apiUrl}/v1/approvals`, {
        headers: { Authorization: `Bearer ${apiKey}` },
      });
      if (res.ok) {
        const data = await res.json();
        const all = Array.isArray(data) ? data : data.approvals ?? data.pending ?? [];
        setPending(all.filter((a: Record<string, unknown>) => a.status === "pending"));
      } else {
        setPending([]);
      }
    } catch {
      setPending([]);
    }

    // Fetch recent decisions for history table
    try {
      const apiUrl = getApiUrl();
      const histRes = await fetch(`${apiUrl}/v1/audit-log?limit=10`, {
        headers: { Authorization: `Bearer ${apiKey}` },
      });
      if (histRes.ok) {
        const histData = await histRes.json();
        const auditEntries = Array.isArray(histData) ? histData : histData.entries ?? [];
        const mapped: HistoryRow[] = auditEntries.map((entry: Record<string, unknown>) => ({
          agent_id: String(entry.agent_id ?? ""),
          action_type: String(entry.action_type ?? ""),
          omega: Number(entry.omega_mem_final ?? entry.omega ?? 0),
          decision: entry.decision === "BLOCK" ? "Rejected" as const : "Approved" as const,
          timestamp: String(entry.created_at ?? entry.timestamp ?? ""),
        }));
        setHistory(mapped);
      }
    } catch {
      // history fetch is non-critical
    }

    setLoading(false);
    setLastUpdated(new Date());
  }, []);

  useEffect(() => {
    loadApprovals();
    const interval = setInterval(loadApprovals, 30000);
    return () => clearInterval(interval);
  }, [loadApprovals]);

  useEffect(() => {
    function tick() {
      const diff = Math.floor((Date.now() - lastUpdated.getTime()) / 1000);
      if (diff < 5) setTimeAgo("just now");
      else if (diff < 60) setTimeAgo(`${diff}s ago`);
      else setTimeAgo(`${Math.floor(diff / 60)}m ago`);
    }
    tick();
    const t = setInterval(tick, 1000);
    return () => clearInterval(t);
  }, [lastUpdated]);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 3000);
    return () => clearTimeout(t);
  }, [toast]);

  function showToast(message: string, type: "success" | "error") {
    setToast({ message, type });
  }

  async function approveDecision(id: string) {
    const apiKey = getApiKey();
    if (!apiKey) { showToast("API key required", "error"); return; }
    const apiUrl = getApiUrl();
    try {
      const res = await fetch(`${apiUrl}/v1/approvals/${id}/approve`, {
        method: "POST",
        headers: { Authorization: `Bearer ${apiKey}` },
      });
      if (res.ok) {
        setPending(prev => prev.filter(p => p.id !== id));
        showToast("Approved", "success");
      } else {
        showToast(`Approve failed: ${res.status}`, "error");
      }
    } catch {
      showToast("Failed to approve", "error");
    }
  }

  async function rejectDecision(id: string) {
    const apiKey = getApiKey();
    if (!apiKey) { showToast("API key required", "error"); return; }
    const apiUrl = getApiUrl();
    try {
      const res = await fetch(`${apiUrl}/v1/approvals/${id}/reject`, {
        method: "POST",
        headers: { Authorization: `Bearer ${apiKey}` },
      });
      if (res.ok) {
        setPending(prev => prev.filter(p => p.id !== id));
        showToast("Rejected", "success");
      } else {
        showToast(`Reject failed: ${res.status}`, "error");
      }
    } catch {
      showToast("Failed to reject", "error");
    }
  }

  if (!mounted) return null;

  if (!hasKey) return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Approval Queue</h1>
      <p className="text-muted text-sm mb-6">Pending ASK_USER decisions waiting for human review.</p>
      <ConnectKeyState />
    </div>
  );

  if (loading) return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Approval Queue</h1>
      <p className="text-muted text-sm mb-6">Pending ASK_USER decisions waiting for human review.</p>
      <LoadingSkeleton rows={4} />
    </div>
  );

  const showEmpty = hasKey && pending.length === 0;

  return (
    <div>
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold mb-1">Approval Queue</h1>
          <p className="text-muted text-sm">Pending ASK_USER decisions waiting for human review.</p>
        </div>
        <div className="text-right">
          <p style={{ fontSize: "12px", color: "#6b7280" }}>Auto-refreshing every 30s</p>
          <p style={{ fontSize: "12px", color: "#6b7280" }}>Updated {timeAgo}</p>
        </div>
      </div>

      {/* Empty state */}
      {showEmpty && (
        <div style={{ textAlign: "center", padding: "80px 0" }}>
          <p style={{ fontSize: "48px", color: "#16a34a" }}>✓</p>
          <h3 style={{ fontSize: "20px", color: "#0B0F14", marginTop: "8px" }}>No pending approvals</h3>
          <p style={{ fontSize: "14px", color: "#6b7280", marginTop: "8px" }}>
            When an agent receives ASK_USER, it will appear here for your review.
          </p>
        </div>
      )}

      {/* Pending cards */}
      {pending.length > 0 && (
        <div>
          {pending.map((item) => (
            <div
              key={item.id}
              style={{
                background: "#ffffff",
                borderRadius: "8px",
                borderLeft: "4px solid #c9a962",
                padding: "24px",
                marginBottom: "16px",
                boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
              }}
            >
              {/* Top row */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontFamily: "monospace", fontSize: "14px", color: "#0B0F14", fontWeight: 600 }}>
                  {item.agent_id}
                </span>
                <span style={{ fontSize: "13px", color: "#6b7280" }}>{item.timestamp}</span>
              </div>

              {/* Badges */}
              <div style={{ display: "flex", gap: "8px", marginTop: "10px", flexWrap: "wrap" }}>
                <span style={TAG_STYLE}>{item.action_type}</span>
                <span style={TAG_STYLE}>{item.domain}</span>
                <span style={omegaBadgeStyle(item.omega)}>Ω {item.omega}</span>
              </div>

              {/* Explanation */}
              <div style={{ marginTop: "12px" }}>
                <p style={{ fontSize: "11px", color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                  Why ASK_USER:
                </p>
                <p style={{ fontSize: "15px", color: "#0B0F14", lineHeight: 1.6, marginTop: "4px" }}>
                  {item.explanation}
                </p>
              </div>

              {/* Memory summary */}
              <div style={{ marginTop: "8px" }}>
                <p style={{ fontSize: "11px", color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                  Memory:
                </p>
                <p style={{ fontSize: "14px", color: "#6b7280", marginTop: "2px" }}>{item.memory_summary}</p>
              </div>

              {/* Actions */}
              <div style={{ display: "flex", gap: "12px", marginTop: "16px", alignItems: "center" }}>
                <button
                  onClick={() => approveDecision(item.id)}
                  style={{
                    background: "#16a34a",
                    color: "white",
                    padding: "8px 24px",
                    borderRadius: "6px",
                    fontWeight: 600,
                    fontSize: "14px",
                    border: "none",
                    cursor: "pointer",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "#15803d")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "#16a34a")}
                >
                  Approve
                </button>
                <button
                  onClick={() => rejectDecision(item.id)}
                  style={{
                    background: "#dc2626",
                    color: "white",
                    padding: "8px 24px",
                    borderRadius: "6px",
                    fontWeight: 600,
                    fontSize: "14px",
                    border: "none",
                    cursor: "pointer",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "#b91c1c")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "#dc2626")}
                >
                  Reject
                </button>
                <a href={`/agent/${item.agent_id}`} style={{ color: "#c9a962", fontSize: "14px" }}>
                  View Details →
                </a>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* History */}
      <div style={{ marginTop: "48px" }}>
        <h2 style={{ fontSize: "20px", color: "#0B0F14", fontWeight: 700, marginBottom: "16px" }}>Recent Decisions</h2>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              {["Agent", "Action", "Omega", "Decision", "Timestamp"].map((h) => (
                <th
                  key={h}
                  style={{
                    fontSize: "12px",
                    color: "#6b7280",
                    textTransform: "uppercase",
                    padding: "8px 16px",
                    textAlign: "left",
                    borderBottom: "1px solid #e5e7eb",
                    letterSpacing: "0.05em",
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {history.map((row, i) => (
              <tr key={i}>
                <td style={{ fontSize: "14px", color: "#0B0F14", padding: "12px 16px", borderBottom: "1px solid #f5f4f0", fontFamily: "monospace" }}>
                  {row.agent_id}
                </td>
                <td style={{ fontSize: "14px", color: "#0B0F14", padding: "12px 16px", borderBottom: "1px solid #f5f4f0" }}>
                  {row.action_type}
                </td>
                <td style={{ padding: "12px 16px", borderBottom: "1px solid #f5f4f0" }}>
                  <span style={omegaBadgeStyle(row.omega)}>Ω {row.omega}</span>
                </td>
                <td style={{ padding: "12px 16px", borderBottom: "1px solid #f5f4f0" }}>
                  <span
                    style={{
                      background: row.decision === "Approved" ? "#dcfce7" : "#fee2e2",
                      color: row.decision === "Approved" ? "#16a34a" : "#dc2626",
                      borderRadius: "20px",
                      padding: "2px 10px",
                      fontSize: "12px",
                      fontWeight: 600,
                    }}
                  >
                    {row.decision}
                  </span>
                </td>
                <td style={{ fontSize: "14px", color: "#6b7280", padding: "12px 16px", borderBottom: "1px solid #f5f4f0" }}>
                  {row.timestamp}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Toast */}
      {toast && (
        <div
          style={{
            position: "fixed",
            bottom: "24px",
            right: "24px",
            background: toast.type === "success" ? "#16a34a" : "#dc2626",
            color: "white",
            padding: "12px 24px",
            borderRadius: "8px",
            fontSize: "14px",
            fontWeight: 600,
            boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
            zIndex: 100,
          }}
        >
          {toast.message}
        </div>
      )}
    </div>
  );
}
