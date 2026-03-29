"use client";

import { useState } from "react";

const DEFAULT_MEMORY = JSON.stringify(
  [{ id: "mem_payment_history", type: "tool_state", timestamp_age_days: 54, source_trust: 0.6, source_conflict: 0.4 }],
  null, 2
);

function omegaColor(v: number) {
  if (v <= 30) return "#16a34a";
  if (v <= 60) return "#ca8a04";
  return "#dc2626";
}

const ACTION_COLORS: Record<string, string> = {
  USE_MEMORY: "#16a34a", WARN: "#ca8a04", ASK_USER: "#ea580c", BLOCK: "#dc2626",
};

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
    <div className="max-w-3xl mx-auto py-20 px-8">
      <h1 className="font-headline text-4xl font-extrabold tracking-tighter text-on-background mb-2">
        Try Sgraal <span className="text-primary-container">live.</span>
      </h1>
      <p className="text-secondary text-lg mb-12">No signup. No API key needed. Real scoring.</p>

      <div className="space-y-5 mb-8">
        <div>
          <label className="text-xs font-bold tracking-widest uppercase text-secondary block mb-2">Memory state (JSON)</label>
          <textarea value={memory} onChange={(e) => setMemory(e.target.value)} rows={6}
            className="w-full bg-surface-container-lowest border-b border-outline-variant rounded-md px-4 py-3 text-sm font-mono text-on-surface focus:outline-none focus:border-primary-container transition-colors resize-y" />
        </div>
        <div className="grid grid-cols-2 gap-5">
          <div>
            <label className="text-xs font-bold tracking-widest uppercase text-secondary block mb-2">Action type</label>
            <select value={actionType} onChange={(e) => setActionType(e.target.value)}
              className="w-full bg-surface-container-lowest border-b border-outline-variant rounded-md px-4 py-2.5 text-sm text-on-surface focus:outline-none focus:border-primary-container">
              <option value="read">read</option><option value="write">write</option>
              <option value="financial">financial</option><option value="irreversible">irreversible</option>
            </select>
          </div>
          <div>
            <label className="text-xs font-bold tracking-widest uppercase text-secondary block mb-2">Domain</label>
            <select value={domain} onChange={(e) => setDomain(e.target.value)}
              className="w-full bg-surface-container-lowest border-b border-outline-variant rounded-md px-4 py-2.5 text-sm text-on-surface focus:outline-none focus:border-primary-container">
              <option value="general">general</option><option value="fintech">fintech</option>
              <option value="medical">healthcare</option><option value="legal">legal</option>
            </select>
          </div>
        </div>
        <button onClick={run} disabled={loading}
          className="w-full gold-gradient-bg py-3.5 rounded-md text-white font-bold text-base disabled:opacity-50 transition-opacity">
          {loading ? "Running..." : "Run Preflight"}
        </button>
      </div>

      {error && <p className="text-error text-sm text-center mb-6">{error}</p>}

      {result && omega !== null && action && (
        <div className="space-y-8">
          <div className="flex items-center justify-center gap-10">
            <svg width="120" height="120" viewBox="0 0 120 120">
              <circle cx="60" cy="60" r="52" fill="none" stroke="#e9e8e5" strokeWidth="8" />
              <circle cx="60" cy="60" r="52" fill="none" stroke={omegaColor(omega)} strokeWidth="8"
                strokeDasharray={`${omega * 3.27} 327`} strokeLinecap="round" transform="rotate(-90 60 60)" />
              <text x="60" y="56" textAnchor="middle" fill="#1a1c1a" fontSize="28" fontWeight="bold" fontFamily="Manrope">{omega}</text>
              <text x="60" y="74" textAnchor="middle" fill="#6b6b6b" fontSize="10">omega</text>
            </svg>
            <span className="inline-block px-5 py-2.5 rounded-md text-white text-sm font-bold font-mono"
              style={{ backgroundColor: ACTION_COLORS[action] || "#6b6b6b" }}>
              {action}
            </span>
          </div>
          <div>
            <button onClick={() => setShowJson(!showJson)} className="text-sm text-secondary hover:text-on-surface transition-colors">
              {showJson ? "Hide" : "Show"} full response JSON
            </button>
            {showJson && (
              <pre className="mt-3 bg-[#0b0f14] rounded-xl p-5 text-xs overflow-x-auto max-h-96 overflow-y-auto text-[#e2e8f0] font-mono">
                {JSON.stringify(result, null, 2)}
              </pre>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
