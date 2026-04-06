"use client";

import { useState, useEffect } from "react";
import { getApiKey, getApiUrl } from "../lib/storage";
import { LoadingSkeleton, ConnectKeyState } from "../components/LoadingSkeleton";

interface Conflict {
  id: string;
  entry_a: string;
  entry_b: string;
  similarity: number;
  status: "pending" | "resolved";
}

const STRATEGIES = ["keep_newer", "keep_trusted", "merge", "manual"];

const CARD: React.CSSProperties = { background: "#ffffff", borderRadius: "8px", padding: "20px", boxShadow: "0 1px 3px rgba(0,0,0,0.06)" };
const INPUT: React.CSSProperties = { width: "100%", background: "#ffffff", border: "1px solid #e5e7eb", borderRadius: "6px", padding: "8px 12px", fontSize: "14px", color: "#0B0F14" };
const DOMAINS = ["general", "fintech", "medical", "legal", "coding"];

interface Verdict { verdict_id: string; winner: string; confidence: number; method: string; z3_verified?: boolean; explanation: string; }

export default function ConflictsPage() {
  const [mounted, setMounted] = useState(false);
  const [conflicts, setConflicts] = useState<Conflict[]>([]);
  const [strategy, setStrategy] = useState("keep_newer");
  const [loading, setLoading] = useState(true);
  const [hasKey, setHasKey] = useState(false);

  // Court Arbitration
  const [arbA, setArbA] = useState({ content: "", agent_id: "", age: "5", trust: "0.9" });
  const [arbB, setArbB] = useState({ content: "", agent_id: "", age: "10", trust: "0.7" });
  const [arbDomain, setArbDomain] = useState("general");
  const [arbLoading, setArbLoading] = useState(false);
  const [arbResult, setArbResult] = useState<Verdict | null>(null);
  const [arbError, setArbError] = useState("");
  const [pastVerdicts, setPastVerdicts] = useState<Verdict[]>([]);

  useEffect(() => {
    setMounted(true);
    const apiUrl = getApiUrl();
    const apiKey = getApiKey();
    setHasKey(!!apiKey);
    if (!apiUrl || !apiKey) {
      setLoading(false);
      return;
    }
    fetch(`${apiUrl}/v1/conflicts`, { headers: { Authorization: `Bearer ${apiKey}` } })
      .then((r) => { if (!r.ok) throw new Error(); return r.json(); })
      .then((d) => setConflicts(d.conflicts || []))
      .catch(() => setConflicts([]))
      .finally(() => setLoading(false));
  }, []);

  const pendingCount = conflicts.filter((c) => c.status === "pending").length;

  async function handleResolve(id: string) {
    const apiKey = getApiKey();
    if (!apiKey) return;
    try {
      await fetch(`${getApiUrl()}/v1/conflicts/${id}/resolve`, {
        method: "POST",
        headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
        body: JSON.stringify({ strategy }),
      });
    } catch {}
    setConflicts((prev) => prev.map((c) => (c.id === id ? { ...c, status: "resolved" as const } : c)));
  }

  if (!mounted) return null;

  if (!hasKey) return (
    <div>
      <h1 className="text-2xl font-bold text-foreground mb-6">Memory Conflicts</h1>
      <ConnectKeyState />
    </div>
  );

  if (loading) return (
    <div>
      <h1 className="text-2xl font-bold text-foreground mb-6">Memory Conflicts</h1>
      <LoadingSkeleton rows={4} />
    </div>
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-foreground">Memory Conflicts</h1>
        {pendingCount > 0 && (
          <span className="bg-red-500 text-white text-xs font-bold px-2 py-1 rounded-full">
            {pendingCount}
          </span>
        )}
      </div>

      <div className="mb-4 flex items-center gap-3">
        <label className="text-sm text-muted">Resolution Strategy:</label>
        <select
          value={strategy}
          onChange={(e) => setStrategy(e.target.value)}
          className="bg-surface border border-surface-light rounded px-3 py-1 text-sm"
          data-testid="strategy-selector"
        >
          {STRATEGIES.map((s) => (
            <option key={s} value={s}>{s.replace(/_/g, " ")}</option>
          ))}
        </select>
      </div>

      {conflicts.length === 0 ? (
        <div style={{ textAlign: "center", padding: "80px 0" }}>
          <p style={{ fontSize: "48px", color: "#16a34a" }}>✓</p>
          <h3 style={{ fontSize: "20px", color: "#0B0F14", fontWeight: 700, marginTop: "8px" }}>No memory conflicts detected</h3>
          <p style={{ fontSize: "14px", color: "#6b7280", marginTop: "8px", maxWidth: "360px", marginLeft: "auto", marginRight: "auto", lineHeight: 1.6 }}>
            When agents store conflicting information, it will appear here for resolution.
          </p>
          <p style={{ fontSize: "13px", color: "#6b7280", marginTop: "12px" }}>Last checked: just now</p>
        </div>
      ) : (
        <div className="space-y-4">
          {conflicts.map((c) => (
            <div key={c.id} className="border border-surface-light rounded-lg p-4 flex items-center justify-between">
              <div className="flex gap-8">
                <div>
                  <p className="text-sm text-muted">Entry A</p>
                  <p className="font-mono text-foreground">{c.entry_a}</p>
                </div>
                <div className="text-muted text-2xl">⟷</div>
                <div>
                  <p className="text-sm text-muted">Entry B</p>
                  <p className="font-mono text-foreground">{c.entry_b}</p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <span className="text-sm text-muted">
                  Similarity: <span className="text-gold">{(c.similarity * 100).toFixed(0)}%</span>
                </span>
                {c.status === "pending" ? (
                  <button
                    onClick={() => handleResolve(c.id)}
                    className="bg-gold text-black px-3 py-1 rounded text-sm font-medium hover:bg-gold/80 transition"
                    data-testid="resolve-button"
                  >
                    Resolve ({strategy.replace(/_/g, " ")})
                  </button>
                ) : (
                  <span className="text-green-400 text-sm">Resolved</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
      {/* Court Arbitration */}
      <div style={{ ...CARD, marginTop: "32px" }}>
        <h2 style={{ fontSize: "18px", fontWeight: 700, marginBottom: "4px" }}>Court Arbitration</h2>
        <p style={{ fontSize: "13px", color: "#6b7280", marginBottom: "16px" }}>Submit conflicting memory entries for formal arbitration. Sgraal uses omega scoring + causal inference + Z3 formal verification to determine the authoritative version.</p>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginBottom: "16px" }}>
          <div>
            <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", marginBottom: "6px" }}>Entry A</p>
            <input placeholder="Content..." value={arbA.content} onChange={e => setArbA({ ...arbA, content: e.target.value })} style={{ ...INPUT, marginBottom: "6px" }} />
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "6px" }}>
              <input placeholder="Agent ID" value={arbA.agent_id} onChange={e => setArbA({ ...arbA, agent_id: e.target.value })} style={{ ...INPUT, fontSize: "12px", padding: "6px 8px" }} />
              <input placeholder="Age (days)" value={arbA.age} onChange={e => setArbA({ ...arbA, age: e.target.value })} style={{ ...INPUT, fontSize: "12px", padding: "6px 8px" }} />
              <input placeholder="Trust (0-1)" value={arbA.trust} onChange={e => setArbA({ ...arbA, trust: e.target.value })} style={{ ...INPUT, fontSize: "12px", padding: "6px 8px" }} />
            </div>
          </div>
          <div>
            <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", marginBottom: "6px" }}>Entry B</p>
            <input placeholder="Content..." value={arbB.content} onChange={e => setArbB({ ...arbB, content: e.target.value })} style={{ ...INPUT, marginBottom: "6px" }} />
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "6px" }}>
              <input placeholder="Agent ID" value={arbB.agent_id} onChange={e => setArbB({ ...arbB, agent_id: e.target.value })} style={{ ...INPUT, fontSize: "12px", padding: "6px 8px" }} />
              <input placeholder="Age (days)" value={arbB.age} onChange={e => setArbB({ ...arbB, age: e.target.value })} style={{ ...INPUT, fontSize: "12px", padding: "6px 8px" }} />
              <input placeholder="Trust (0-1)" value={arbB.trust} onChange={e => setArbB({ ...arbB, trust: e.target.value })} style={{ ...INPUT, fontSize: "12px", padding: "6px 8px" }} />
            </div>
          </div>
        </div>

        <div style={{ display: "flex", gap: "12px", alignItems: "center", marginBottom: "16px" }}>
          <select value={arbDomain} onChange={e => setArbDomain(e.target.value)} style={{ ...INPUT, width: "160px" }}>
            {DOMAINS.map(d => <option key={d} value={d}>{d}</option>)}
          </select>
          <button onClick={async () => {
            if (!arbA.content || !arbB.content) { setArbError("Both entries required"); return; }
            setArbLoading(true); setArbError(""); setArbResult(null);
            const apiKey = getApiKey(); const apiUrl = getApiUrl();
            try {
              const res = await fetch(`${apiUrl}/v1/court/arbitrate`, {
                method: "POST", headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
                body: JSON.stringify({ entry_a: { content: arbA.content, agent_id: arbA.agent_id, timestamp_age_days: Number(arbA.age), source_trust: Number(arbA.trust) }, entry_b: { content: arbB.content, agent_id: arbB.agent_id, timestamp_age_days: Number(arbB.age), source_trust: Number(arbB.trust) }, domain: arbDomain }),
              });
              if (res.ok) { const d = await res.json(); setArbResult(d); }
              else setArbError(`Error: ${res.status}`);
            } catch { setArbError("Request failed"); }
            setArbLoading(false);
            // Fetch past verdicts
            try {
              const vRes = await fetch(`${apiUrl}/v1/court/verdicts?limit=5`, { headers: { Authorization: `Bearer ${apiKey}` } });
              if (vRes.ok) { const vd = await vRes.json(); setPastVerdicts(Array.isArray(vd) ? vd : vd.verdicts ?? []); }
            } catch {}
          }} disabled={arbLoading} style={{ background: "#c9a962", color: "#0B0F14", fontWeight: 600, padding: "8px 20px", borderRadius: "6px", fontSize: "14px", border: "none", cursor: arbLoading ? "not-allowed" : "pointer", opacity: arbLoading ? 0.6 : 1 }}>
            {arbLoading ? "Arbitrating..." : "Arbitrate"}
          </button>
        </div>

        {arbError && <p style={{ fontSize: "13px", color: "#dc2626", marginBottom: "12px" }}>{arbError}</p>}

        {arbResult && (
          <div style={{ border: "1px solid #e5e7eb", borderRadius: "8px", padding: "16px", marginBottom: "16px" }}>
            <div style={{ display: "flex", gap: "16px", marginBottom: "12px" }}>
              <div style={{ flex: 1, padding: "12px", borderRadius: "6px", background: arbResult.winner === "A" ? "#dcfce7" : "#fef2f2", border: `1px solid ${arbResult.winner === "A" ? "#bbf7d0" : "#fecaca"}` }}>
                <p style={{ fontSize: "11px", color: "#6b7280", textTransform: "uppercase", marginBottom: "4px" }}>Entry A {arbResult.winner === "A" && <span style={{ color: "#16a34a", fontWeight: 700 }}>WINNER</span>}</p>
                <p style={{ fontSize: "13px" }}>{arbA.content}</p>
              </div>
              <div style={{ flex: 1, padding: "12px", borderRadius: "6px", background: arbResult.winner === "B" ? "#dcfce7" : "#fef2f2", border: `1px solid ${arbResult.winner === "B" ? "#bbf7d0" : "#fecaca"}` }}>
                <p style={{ fontSize: "11px", color: "#6b7280", textTransform: "uppercase", marginBottom: "4px" }}>Entry B {arbResult.winner === "B" && <span style={{ color: "#16a34a", fontWeight: 700 }}>WINNER</span>}</p>
                <p style={{ fontSize: "13px" }}>{arbB.content}</p>
              </div>
            </div>
            <div style={{ display: "flex", gap: "16px", fontSize: "13px", flexWrap: "wrap" }}>
              <span>Confidence: <strong>{(arbResult.confidence * 100).toFixed(0)}%</strong></span>
              <span style={{ background: "#dbeafe", color: "#1e40af", borderRadius: "4px", padding: "1px 8px", fontSize: "11px" }}>{arbResult.method}</span>
              {arbResult.z3_verified && <span style={{ color: "#16a34a" }}>&#x2713; Z3 logical consistency verified</span>}
            </div>
            {arbResult.explanation && <p style={{ fontSize: "13px", color: "#6b7280", marginTop: "8px" }}>{arbResult.explanation}</p>}
            <p style={{ fontSize: "11px", color: "#9ca3af", fontFamily: "monospace", marginTop: "6px" }}>verdict_id: {arbResult.verdict_id}</p>
          </div>
        )}

        {pastVerdicts.length > 0 && (
          <div>
            <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", marginBottom: "8px" }}>Past Verdicts</p>
            {pastVerdicts.slice(0, 5).map((v, i) => (
              <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid #f5f4f0", fontSize: "13px" }}>
                <span>Winner: <strong>{v.winner}</strong> — {v.method}</span>
                <span style={{ color: "#6b7280", fontFamily: "monospace", fontSize: "11px" }}>{v.verdict_id}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
