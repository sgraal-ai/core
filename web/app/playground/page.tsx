"use client";

import { useState } from "react";

const DEFAULT_MEMORY = JSON.stringify(
  [{ id: "mem_payment_history", type: "tool_state", timestamp_age_days: 54, source_trust: 0.6, source_conflict: 0.4 }],
  null, 2
);

const ACTION_COLORS: Record<string, string> = {
  USE_MEMORY: "#16a34a", WARN: "#ca8a04", ASK_USER: "#ea580c", BLOCK: "#dc2626",
};

function omegaColor(v: number) {
  if (v <= 30) return "#16a34a";
  if (v <= 60) return "#ca8a04";
  return "#dc2626";
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
    setError(""); setResult(null); setLoading(true);
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
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally { setLoading(false); }
  }

  const omega = typeof result?.omega_mem_final === "number" ? (result.omega_mem_final as number) : null;
  const action = typeof result?.recommended_action === "string" ? (result.recommended_action as string) : null;

  return (
    <div className="max-w-3xl mx-auto py-16 px-6">
      <h1 className="text-3xl sm:text-4xl mb-2" style={{ fontFamily: "'Manrope', sans-serif", fontWeight: 800, color: "var(--on-surface)" }}>
        Try Sgraal <span style={{ color: "var(--primary-container)" }}>live.</span>
      </h1>
      <p className="text-lg mb-10" style={{ color: "var(--on-surface-variant)" }}>No signup. No API key needed. Real scoring.</p>

      <div className="space-y-4 mb-6">
        <div>
          <label className="text-sm block mb-1" style={{ color: "var(--on-surface-variant)" }}>Memory state (JSON)</label>
          <textarea value={memory} onChange={(e) => setMemory(e.target.value)} rows={6}
            className="w-full rounded-md px-4 py-3 text-sm resize-y focus:outline-none transition"
            style={{ backgroundColor: "var(--surface-container-lowest)", borderBottom: "1px solid var(--outline-variant)", fontFamily: "'JetBrains Mono', monospace", color: "var(--on-surface)" }} />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm block mb-1" style={{ color: "var(--on-surface-variant)" }}>Action type</label>
            <select value={actionType} onChange={(e) => setActionType(e.target.value)}
              className="w-full rounded-md px-4 py-2.5 text-sm focus:outline-none"
              style={{ backgroundColor: "var(--surface-container-lowest)", borderBottom: "1px solid var(--outline-variant)", color: "var(--on-surface)" }}>
              <option value="read">read</option><option value="write">write</option>
              <option value="financial">financial</option><option value="irreversible">irreversible</option>
            </select>
          </div>
          <div>
            <label className="text-sm block mb-1" style={{ color: "var(--on-surface-variant)" }}>Domain</label>
            <select value={domain} onChange={(e) => setDomain(e.target.value)}
              className="w-full rounded-md px-4 py-2.5 text-sm focus:outline-none"
              style={{ backgroundColor: "var(--surface-container-lowest)", borderBottom: "1px solid var(--outline-variant)", color: "var(--on-surface)" }}>
              <option value="general">general</option><option value="fintech">fintech</option>
              <option value="medical">healthcare</option><option value="legal">legal</option>
            </select>
          </div>
        </div>
        <button onClick={run} disabled={loading} className="w-full py-3 rounded-md transition disabled:opacity-50 text-base"
          style={{ background: "linear-gradient(135deg, #745b1c, #c9a962)", color: "#533d00", fontWeight: 600 }}>
          {loading ? "Running..." : "Run Preflight"}
        </button>
      </div>

      {error && <p className="text-sm text-center mb-6" style={{ color: "#dc2626" }}>{error}</p>}

      {result && omega !== null && action && (
        <div className="space-y-6">
          <div className="flex items-center justify-center gap-8">
            <svg width="120" height="120" viewBox="0 0 120 120">
              <circle cx="60" cy="60" r="52" fill="none" stroke="var(--surface-container-high)" strokeWidth="8" />
              <circle cx="60" cy="60" r="52" fill="none" stroke={omegaColor(omega)} strokeWidth="8"
                strokeDasharray={`${omega * 3.27} 327`} strokeLinecap="round" transform="rotate(-90 60 60)" />
              <text x="60" y="56" textAnchor="middle" fill="var(--on-surface)" fontSize="28" fontWeight="bold" fontFamily="Manrope">{omega}</text>
              <text x="60" y="74" textAnchor="middle" fill="var(--on-surface-variant)" fontSize="10">omega</text>
            </svg>
            <span className="inline-block px-4 py-2 rounded-md text-white text-sm" style={{ backgroundColor: ACTION_COLORS[action] || "#6b6b6b", fontFamily: "'JetBrains Mono', monospace", fontWeight: 700 }}>
              {action}
            </span>
          </div>
          <div>
            <button onClick={() => setShowJson(!showJson)} className="text-sm transition" style={{ color: "var(--on-surface-variant)" }}>
              {showJson ? "Hide" : "Show"} full response JSON
            </button>
            {showJson && (
              <pre className="mt-2 rounded-lg p-4 text-xs overflow-x-auto max-h-96 overflow-y-auto"
                style={{ backgroundColor: "var(--obsidian)", color: "#e2e8f0", fontFamily: "'JetBrains Mono', monospace" }}>
                {JSON.stringify(result, null, 2)}
              </pre>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
