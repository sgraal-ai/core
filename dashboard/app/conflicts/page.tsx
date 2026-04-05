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

export default function ConflictsPage() {
  const [mounted, setMounted] = useState(false);
  const [conflicts, setConflicts] = useState<Conflict[]>([]);
  const [strategy, setStrategy] = useState("keep_newer");
  const [loading, setLoading] = useState(true);
  const [hasKey, setHasKey] = useState(false);

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
            <option key={s} value={s}>{s.replace("_", " ")}</option>
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
                    Resolve ({strategy.replace("_", " ")})
                  </button>
                ) : (
                  <span className="text-green-400 text-sm">Resolved</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
