"use client";
import { useState } from "react";

const DEMO_ENTRIES = [
  { id: "trade_hist", content: "Recent trading history for EUR/USD pair", type: "tool_state", timestamp_age_days: 2, source_trust: 0.95, source_conflict: 0.05, downstream_count: 5 },
  { id: "risk_model", content: "VaR model parameters calibrated Q1 2026", type: "semantic", timestamp_age_days: 30, source_trust: 0.8, source_conflict: 0.15, downstream_count: 12 },
  { id: "compliance", content: "MiFID II reporting requirements", type: "policy", timestamp_age_days: 90, source_trust: 0.99, source_conflict: 0.01, downstream_count: 20 },
];

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://api.sgraal.com";

export default function PlaygroundPage() {
  const [domain, setDomain] = useState("fintech");
  const [actionType, setActionType] = useState("irreversible");
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [explain, setExplain] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [tab, setTab] = useState<"visual" | "json" | "explain">("visual");

  const run = async () => {
    setLoading(true); setError(""); setResult(null); setExplain(null);
    try {
      const r = await fetch(`${API_URL}/v1/preflight`, {
        method: "POST", headers: { "Content-Type": "application/json", Authorization: "Bearer sg_demo_playground" },
        body: JSON.stringify({ memory_state: DEMO_ENTRIES, domain, action_type: actionType }),
      });
      if (!r.ok) throw new Error(`${r.status}: ${await r.text()}`);
      const data = await r.json();
      setResult(data);
      // Also fetch explanation
      const er = await fetch(`${API_URL}/v1/explain`, {
        method: "POST", headers: { "Content-Type": "application/json", Authorization: "Bearer sg_demo_playground" },
        body: JSON.stringify({ preflight_result: data, audience: "developer", language: "en" }),
      });
      if (er.ok) setExplain(await er.json());
    } catch (e) { setError(String(e)); }
    setLoading(false);
  };

  const omega = (result?.omega_mem_final as number) ?? 0;
  const action = (result?.recommended_action as string) ?? "";
  const actionColor = action === "USE_MEMORY" ? "text-green-400" : action === "WARN" ? "text-yellow-400" : action === "ASK_USER" ? "text-orange-400" : "text-red-400";
  const gaugeColor = omega < 25 ? "#4ade80" : omega < 50 ? "#facc15" : omega < 75 ? "#fb923c" : "#f87171";

  return (
    <div className="min-h-screen bg-[#0B0F14] text-white px-4 py-12 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-2">Sgraal Playground</h1>
      <p className="text-gray-400 text-sm mb-8">Test the Omega_MEM preflight API live — no signup required.</p>

      <div className="flex gap-4 mb-6">
        <div>
          <label className="text-xs text-gray-500 block mb-1">Domain</label>
          <select value={domain} onChange={e => setDomain(e.target.value)} className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm">
            <option value="general">General</option>
            <option value="fintech">Fintech</option>
            <option value="medical">Healthcare</option>
            <option value="legal">Legal</option>
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-500 block mb-1">Action Type</label>
          <select value={actionType} onChange={e => setActionType(e.target.value)} className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm">
            <option value="reversible">Reversible</option>
            <option value="irreversible">Irreversible</option>
            <option value="destructive">Destructive</option>
          </select>
        </div>
        <div className="flex items-end">
          <button onClick={run} disabled={loading} className="bg-[#C9A962] text-black font-semibold px-6 py-2 rounded hover:bg-[#d4b872] transition disabled:opacity-50">
            {loading ? "Running..." : "Run Preflight →"}
          </button>
        </div>
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 mb-6">
        <p className="text-xs text-gray-500 mb-2">Memory State (3 entries, {domain} domain)</p>
        <pre className="text-xs text-gray-400 overflow-x-auto">{JSON.stringify(DEMO_ENTRIES, null, 2)}</pre>
      </div>

      {error && <div className="bg-red-400/10 border border-red-400/30 rounded-lg p-4 mb-6 text-red-400 text-sm">{error}</div>}

      {result && (
        <>
          <div className="flex gap-8 items-center mb-8">
            <div className="text-center">
              <svg width="120" height="120" viewBox="0 0 120 120">
                <circle cx="60" cy="60" r="54" fill="none" stroke="#1f2937" strokeWidth="8" />
                <circle cx="60" cy="60" r="54" fill="none" stroke={gaugeColor} strokeWidth="8"
                  strokeDasharray={`${omega * 3.39} 339`} strokeLinecap="round" transform="rotate(-90 60 60)" />
                <text x="60" y="55" textAnchor="middle" fill="white" fontSize="28" fontWeight="bold">{omega}</text>
                <text x="60" y="75" textAnchor="middle" fill="#9ca3af" fontSize="11">Ω_MEM</text>
              </svg>
            </div>
            <div>
              <p className={`text-2xl font-bold ${actionColor}`}>{action}</p>
              <p className="text-gray-400 text-sm mt-1">{(result as Record<string, unknown>).assurance_score as number}% assurance</p>
              {Boolean((result as Record<string, unknown>).demo) ? <span className="text-xs text-[#C9A962] font-mono mt-2 block">DEMO MODE</span> : null}
            </div>
          </div>

          <div className="flex gap-2 mb-4">
            {(["visual", "json", "explain"] as const).map(t => (
              <button key={t} onClick={() => setTab(t)} className={`px-4 py-1.5 rounded text-sm font-mono ${tab === t ? "bg-[#C9A962] text-black" : "bg-gray-800 text-gray-400"}`}>
                {t === "visual" ? "Visual" : t === "json" ? "Raw JSON" : "Explain"}
              </button>
            ))}
          </div>

          {tab === "visual" && (
            <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
              <h3 className="text-sm font-semibold mb-3">Component Breakdown</h3>
              {Object.entries((result.component_breakdown as Record<string, number>) || {}).map(([k, v]) => (
                <div key={k} className="flex items-center gap-2 mb-1">
                  <span className="text-xs text-gray-500 w-32 font-mono">{k}</span>
                  <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: `${Math.min(v, 100)}%`, backgroundColor: v > 60 ? "#f87171" : v > 30 ? "#facc15" : "#4ade80" }} />
                  </div>
                  <span className="text-xs text-gray-400 w-10 text-right">{v}</span>
                </div>
              ))}
              <h3 className="text-sm font-semibold mt-5 mb-3">Repair Plan ({((result.repair_plan as unknown[]) || []).length} actions)</h3>
              {((result.repair_plan as Array<Record<string, unknown>>) || []).slice(0, 5).map((r, i) => (
                <div key={i} className="text-xs text-gray-400 mb-1 font-mono">
                  <span className="text-[#C9A962]">{r.action as string}</span> — {r.reason as string}
                </div>
              ))}
            </div>
          )}

          {tab === "json" && (
            <div className="bg-gray-900 border border-gray-800 rounded-lg p-5 max-h-96 overflow-y-auto">
              <pre className="text-xs text-gray-300 font-mono">{JSON.stringify(result, null, 2)}</pre>
            </div>
          )}

          {tab === "explain" && explain && (
            <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
              <p className="text-sm mb-3">{explain.summary as string}</p>
              <p className="text-xs text-gray-400 mb-2"><strong className="text-gray-300">Root cause:</strong> {explain.root_cause as string}</p>
              <p className="text-xs text-gray-400 mb-2"><strong className="text-gray-300">Action:</strong> {explain.recommended_action_human as string}</p>
              <p className="text-xs text-gray-400"><strong className="text-gray-300">Timeline:</strong> {explain.timeline as string}</p>
            </div>
          )}
        </>
      )}

      <p className="text-xs text-gray-600 mt-8 text-center">
        Using demo key — limited to preflight + explain. <a href="https://api.sgraal.com/v1/signup" className="text-[#C9A962] hover:underline">Sign up for full access →</a>
      </p>
    </div>
  );
}
