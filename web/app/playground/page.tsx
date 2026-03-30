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

const GOLD_GRADIENT = "linear-gradient(135deg, #745b1c, #c9a962)";
const GOLD = "#c9a962";

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
    <div style={{ maxWidth: "48rem", margin: "0 auto", padding: "5rem 2rem 4rem" }}>
      <h1 style={{ fontSize: "2.5rem", fontWeight: 800, letterSpacing: "-0.03em", color: "#000000", marginBottom: "0.5rem", fontFamily: "'Manrope', sans-serif" }}>
        Try Sgraal <span style={{ color: GOLD }}>live.</span>
      </h1>
      <p style={{ color: "#6b7280", fontSize: "1.125rem", marginBottom: "3rem" }}>No signup. No API key needed. Real scoring.</p>

      <div style={{ marginBottom: "2rem" }}>
        <div style={{ marginBottom: "1.25rem" }}>
          <label style={{ fontSize: "0.75rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase" as const, color: "#6b7280", display: "block", marginBottom: "0.5rem" }}>
            MEMORY STATE (JSON)
          </label>
          <textarea
            value={memory}
            onChange={(e) => setMemory(e.target.value)}
            rows={6}
            style={{ width: "100%", background: "#ffffff", border: "1px solid #e5e7eb", borderRadius: "0.375rem", padding: "0.75rem 1rem", fontSize: "0.875rem", fontFamily: "monospace", color: "#000000", resize: "vertical" as const, outline: "none", boxSizing: "border-box" as const }}
          />
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.25rem", marginBottom: "1.25rem" }}>
          <div>
            <label style={{ fontSize: "0.75rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase" as const, color: "#6b7280", display: "block", marginBottom: "0.5rem" }}>
              ACTION TYPE
            </label>
            <select
              value={actionType}
              onChange={(e) => setActionType(e.target.value)}
              style={{ width: "100%", background: "#ffffff", border: "1px solid #e5e7eb", borderRadius: "0.375rem", padding: "0.625rem 1rem", fontSize: "0.875rem", color: "#000000", outline: "none" }}
            >
              <option value="read">read</option>
              <option value="write">write</option>
              <option value="financial">financial</option>
              <option value="irreversible">irreversible</option>
            </select>
          </div>
          <div>
            <label style={{ fontSize: "0.75rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase" as const, color: "#6b7280", display: "block", marginBottom: "0.5rem" }}>
              DOMAIN
            </label>
            <select
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              style={{ width: "100%", background: "#ffffff", border: "1px solid #e5e7eb", borderRadius: "0.375rem", padding: "0.625rem 1rem", fontSize: "0.875rem", color: "#000000", outline: "none" }}
            >
              <option value="general">general</option>
              <option value="fintech">fintech</option>
              <option value="medical">healthcare</option>
              <option value="legal">legal</option>
            </select>
          </div>
        </div>

        <button
          onClick={run}
          disabled={loading}
          style={{ width: "100%", background: loading ? "#9ca3af" : GOLD_GRADIENT, padding: "0.875rem", borderRadius: "0.375rem", color: "#ffffff", fontWeight: 700, fontSize: "1rem", border: "none", cursor: loading ? "not-allowed" : "pointer" }}
        >
          {loading ? "Running..." : "Run Preflight"}
        </button>
      </div>

      {error && (
        <p style={{ color: "#dc2626", fontSize: "0.875rem", textAlign: "center", marginBottom: "1.5rem" }}>{error}</p>
      )}

      {result && omega !== null && action && (
        <div style={{ marginTop: "2rem" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "2.5rem", marginBottom: "2rem" }}>
            <svg width="120" height="120" viewBox="0 0 120 120">
              <circle cx="60" cy="60" r="52" fill="none" stroke="#e5e7eb" strokeWidth="8" />
              <circle cx="60" cy="60" r="52" fill="none" stroke={omegaColor(omega)} strokeWidth="8"
                strokeDasharray={`${omega * 3.27} 327`} strokeLinecap="round" transform="rotate(-90 60 60)" />
              <text x="60" y="56" textAnchor="middle" fill="#000000" fontSize="28" fontWeight="bold" fontFamily="Manrope">{omega}</text>
              <text x="60" y="74" textAnchor="middle" fill="#6b7280" fontSize="10">omega</text>
            </svg>
            <span style={{ display: "inline-block", padding: "0.625rem 1.25rem", borderRadius: "0.375rem", color: "#ffffff", fontSize: "0.875rem", fontWeight: 700, fontFamily: "monospace", backgroundColor: ACTION_COLORS[action] || "#6b7280" }}>
              {action}
            </span>
          </div>
          <div>
            <button
              onClick={() => setShowJson(!showJson)}
              style={{ fontSize: "0.875rem", color: "#6b7280", background: "none", border: "none", cursor: "pointer", padding: 0 }}
            >
              {showJson ? "Hide" : "Show"} full response JSON
            </button>
            {showJson && (
              <pre style={{ marginTop: "0.75rem", background: "#0b0f14", borderRadius: "0.75rem", padding: "1.25rem", fontSize: "0.75rem", overflowX: "auto" as const, maxHeight: "24rem", overflowY: "auto" as const, color: "#e2e8f0", fontFamily: "monospace" }}>
                {JSON.stringify(result, null, 2)}
              </pre>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
