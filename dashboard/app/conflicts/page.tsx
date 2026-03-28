"use client";

import { useState, useEffect } from "react";

interface Conflict {
  id: string;
  entry_a: string;
  entry_b: string;
  similarity: number;
  status: "pending" | "resolved";
}

const STRATEGIES = ["keep_newer", "keep_trusted", "merge", "manual"];

export default function ConflictsPage() {
  const [conflicts, setConflicts] = useState<Conflict[]>([]);
  const [strategy, setStrategy] = useState("keep_newer");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const apiUrl = typeof window !== "undefined" ? localStorage.getItem("sgraal_api_url") || "" : "";
    const apiKey = typeof window !== "undefined" ? localStorage.getItem("sgraal_api_key") || "" : "";
    if (!apiUrl || !apiKey) {
      setConflicts([
        { id: "c1", entry_a: "mem_001", entry_b: "mem_042", similarity: 0.92, status: "pending" },
        { id: "c2", entry_a: "mem_015", entry_b: "mem_089", similarity: 0.87, status: "pending" },
        { id: "c3", entry_a: "mem_033", entry_b: "mem_077", similarity: 0.95, status: "resolved" },
      ]);
      setLoading(false);
      return;
    }
    fetch(`${apiUrl}/v1/conflicts`, { headers: { Authorization: `Bearer ${apiKey}` } })
      .then((r) => r.json())
      .then((d) => setConflicts(d.conflicts || []))
      .catch(() => setConflicts([]))
      .finally(() => setLoading(false));
  }, []);

  const pendingCount = conflicts.filter((c) => c.status === "pending").length;

  function handleResolve(id: string) {
    setConflicts((prev) => prev.map((c) => (c.id === id ? { ...c, status: "resolved" as const } : c)));
  }

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

      {loading ? (
        <p className="text-muted">Loading conflicts...</p>
      ) : conflicts.length === 0 ? (
        <p className="text-green-400">No conflicts detected.</p>
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
