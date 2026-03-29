"use client";

import { useState } from "react";

const DEFAULT_MEMORY = JSON.stringify(
  [{ id: "mem_payment_history", type: "tool_state", timestamp_age_days: 54, source_trust: 0.6, source_conflict: 0.4 }],
  null,
  2
);

const ACTION_COLORS: Record<string, string> = {
  USE_MEMORY: "bg-green-500",
  WARN: "bg-yellow-500",
  ASK_USER: "bg-orange-500",
  BLOCK: "bg-red-500",
};

function omegaColor(v: number) {
  if (v <= 30) return "#22c55e";
  if (v <= 60) return "#eab308";
  return "#ef4444";
}

export default function PlaygroundPage() {
  const [memory, setMemory] = useState(DEFAULT_MEMORY);
  const [actionType, setActionType] = useState("irreversible");
  const [domain, setDomain] = useState("fintech");
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showJson, setShowJson] = useState(false);

  async function run() {
    setError("");
    setResult(null);
    setLoading(true);
    try {
      const parsed = JSON.parse(memory);
      const res = await fetch("https://api.sgraal.com/v1/preflight", {
        method: "POST",
        headers: { Authorization: "Bearer sg_demo_playground", "Content-Type": "application/json" },
        body: JSON.stringify({ memory_state: parsed, action_type: actionType, domain }),
      });
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      setResult(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong. Check your JSON and try again.");
    } finally {
      setLoading(false);
    }
  }

  const omega = typeof result?.omega_mem_final === "number" ? (result.omega_mem_final as number) : null;
  const action = typeof result?.recommended_action === "string" ? (result.recommended_action as string) : null;

  return (
    <div className="max-w-3xl mx-auto py-16 px-6">
      <h1 className="text-3xl sm:text-4xl font-bold mb-2">Try Sgraal <span className="text-gold">live.</span></h1>
      <p className="text-muted text-lg mb-10">No signup. No API key needed. Real scoring.</p>

      <div className="space-y-4 mb-6">
        <div>
          <label className="text-sm text-muted block mb-1">Memory state (JSON)</label>
          <textarea
            value={memory}
            onChange={(e) => setMemory(e.target.value)}
            rows={6}
            className="w-full bg-surface border border-surface-light rounded-lg px-4 py-3 font-mono text-sm text-foreground placeholder:text-muted focus:outline-none focus:border-gold transition resize-y"
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm text-muted block mb-1">Action type</label>
            <select value={actionType} onChange={(e) => setActionType(e.target.value)}
              className="w-full bg-surface border border-surface-light rounded-lg px-4 py-2.5 text-sm text-foreground focus:outline-none focus:border-gold">
              <option value="read">read</option>
              <option value="write">write</option>
              <option value="financial">financial</option>
              <option value="irreversible">irreversible</option>
            </select>
          </div>
          <div>
            <label className="text-sm text-muted block mb-1">Domain</label>
            <select value={domain} onChange={(e) => setDomain(e.target.value)}
              className="w-full bg-surface border border-surface-light rounded-lg px-4 py-2.5 text-sm text-foreground focus:outline-none focus:border-gold">
              <option value="general">general</option>
              <option value="fintech">fintech</option>
              <option value="medical">healthcare</option>
              <option value="legal">legal</option>
            </select>
          </div>
        </div>
        <button onClick={run} disabled={loading}
          className="w-full bg-gold text-background font-semibold py-3 rounded-lg hover:bg-gold-dim transition disabled:opacity-50 text-base">
          {loading ? "Running..." : "Run Preflight"}
        </button>
      </div>

      {error && <p className="text-red-400 text-sm text-center mb-6">{error}</p>}

      {result && omega !== null && action && (
        <div className="space-y-6">
          <div className="flex items-center justify-center gap-8">
            <div className="text-center">
              <svg width="120" height="120" viewBox="0 0 120 120">
                <circle cx="60" cy="60" r="52" fill="none" stroke="#1C2430" strokeWidth="8" />
                <circle cx="60" cy="60" r="52" fill="none" stroke={omegaColor(omega)} strokeWidth="8"
                  strokeDasharray={`${omega * 3.27} 327`} strokeLinecap="round" transform="rotate(-90 60 60)" />
                <text x="60" y="56" textAnchor="middle" fill="white" fontSize="28" fontWeight="bold" fontFamily="monospace">{omega}</text>
                <text x="60" y="74" textAnchor="middle" fill="#6B7280" fontSize="10">omega</text>
              </svg>
            </div>
            <div>
              <span className={`inline-block px-4 py-2 rounded-lg text-background font-mono font-bold text-sm ${ACTION_COLORS[action] || "bg-gray-500"}`}>
                {action}
              </span>
            </div>
          </div>

          <div>
            <button onClick={() => setShowJson(!showJson)}
              className="text-sm text-muted hover:text-foreground transition">
              {showJson ? "Hide" : "Show"} full response JSON
            </button>
            {showJson && (
              <pre className="mt-2 bg-surface border border-surface-light rounded-lg p-4 text-xs font-mono text-foreground/80 overflow-x-auto max-h-96 overflow-y-auto">
                {JSON.stringify(result, null, 2)}
              </pre>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
