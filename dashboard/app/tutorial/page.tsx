"use client";
import { useState, useEffect } from "react";
import { getItem, setItem } from "../lib/storage";

const API_URL = "https://api.sgraal.com";
const DEMO_KEY = "sg_demo_playground";
const MAX_CALLS = 20;

const STEPS = [
  { title: "Your first preflight call", desc: "Send a memory entry to the Sgraal scoring engine and get a risk assessment." },
  { title: "Understanding the response", desc: "Learn what omega_mem_final, recommended_action, and component_breakdown mean." },
  { title: "When to BLOCK", desc: "See what happens with stale, high-conflict memory — the engine protects your agent." },
  { title: "Healing blocked memory", desc: "Use /v1/heal to fix problematic entries and restore agent confidence." },
  { title: "You're ready!", desc: "You've mastered the basics of memory governance. Time to build!" },
];

const SAFE_ENTRY = { id: "tutorial_safe", content: "User prefers dark mode", type: "preference", timestamp_age_days: 3, source_trust: 0.95, source_conflict: 0.05, downstream_count: 2 };
const RISKY_ENTRY = { id: "tutorial_risky", content: "Stale compliance data from 2024", type: "policy", timestamp_age_days: 500, source_trust: 0.2, source_conflict: 0.8, downstream_count: 25 };

export default function TutorialPage() {
  const [step, setStep] = useState(0);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [healResult, setHealResult] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [callCount, setCallCount] = useState(0);
  const [completed, setCompleted] = useState(false);

  useEffect(() => {
    const saved = getItem("sgraal_tutorial_step");
    if (saved) setStep(parseInt(saved, 10));
    const cc = getItem("sgraal_tutorial_calls");
    if (cc) setCallCount(parseInt(cc, 10));
    if (getItem("sgraal_tutorial_done") === "true") setCompleted(true);
  }, []);

  useEffect(() => { setItem("sgraal_tutorial_step", String(step)); }, [step]);

  const rateLimited = callCount >= MAX_CALLS;

  const runPreflight = async (entry: Record<string, unknown>) => {
    if (rateLimited) return;
    setLoading(true);
    try {
      const r = await fetch(`${API_URL}/v1/preflight`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${DEMO_KEY}` },
        body: JSON.stringify({ memory_state: [entry] }),
      });
      const data = await r.json();
      setResult(data);
      const nc = callCount + 1;
      setCallCount(nc);
      setItem("sgraal_tutorial_calls", String(nc));
    } catch { /* ignore */ }
    setLoading(false);
  };

  const runHeal = async () => {
    if (rateLimited) return;
    setLoading(true);
    try {
      // Explain instead of heal (demo key can't heal)
      const r = await fetch(`${API_URL}/v1/explain`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${DEMO_KEY}` },
        body: JSON.stringify({ preflight_result: result, audience: "developer" }),
      });
      setHealResult(await r.json());
      const nc = callCount + 1;
      setCallCount(nc);
      setItem("sgraal_tutorial_calls", String(nc));
    } catch { /* ignore */ }
    setLoading(false);
  };

  const finish = () => {
    setCompleted(true);
    setItem("sgraal_tutorial_done", "true");
  };

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-1">Getting Started Tutorial</h1>
      <p className="text-muted text-sm mb-6">Learn memory governance in 5 steps.</p>

      {/* Progress */}
      <div className="flex gap-1 mb-8">
        {STEPS.map((_, i) => (
          <div key={i} className={`h-1.5 flex-1 rounded-full ${i <= step ? "bg-gold" : "bg-surface-light"}`} />
        ))}
      </div>

      {rateLimited && (
        <div className="bg-yellow-400/10 border border-yellow-400/30 rounded-lg p-4 mb-6 text-yellow-400 text-sm">
          Tutorial quota reached ({MAX_CALLS} calls). <a href="https://api.sgraal.com/v1/signup" className="underline">Sign up for unlimited access →</a>
        </div>
      )}

      <div className="bg-surface border border-surface-light rounded-xl p-6 mb-6">
        <div className="flex items-center gap-3 mb-3">
          <span className="bg-gold text-background text-xs font-bold w-6 h-6 rounded-full flex items-center justify-center">{step + 1}</span>
          <h2 className="text-lg font-semibold">{STEPS[step].title}</h2>
        </div>
        <p className="text-muted text-sm mb-4">{STEPS[step].desc}</p>

        {step === 0 && (
          <button onClick={() => runPreflight(SAFE_ENTRY)} disabled={loading || rateLimited}
            className="bg-gold text-background font-semibold px-6 py-2 rounded hover:bg-gold-dim transition disabled:opacity-50">
            {loading ? "Running..." : "Run this →"}
          </button>
        )}

        {step === 1 && result && (
          <div className="text-xs font-mono space-y-1">
            <p>omega_mem_final: <strong className="text-green-400">{String(result.omega_mem_final)}</strong> — lower is better</p>
            <p>recommended_action: <strong className="text-green-400">{String(result.recommended_action)}</strong> — safe to proceed</p>
            <p>assurance_score: <strong>{String(result.assurance_score)}%</strong></p>
          </div>
        )}

        {step === 2 && (
          <>
            <button onClick={() => runPreflight(RISKY_ENTRY)} disabled={loading || rateLimited}
              className="bg-red-400/20 text-red-400 border border-red-400/30 font-semibold px-6 py-2 rounded hover:bg-red-400/30 transition disabled:opacity-50">
              {loading ? "Running..." : "Send risky memory →"}
            </button>
            {result && (result.recommended_action === "BLOCK" || result.recommended_action === "ASK_USER") && (
              <p className="mt-4 text-sm text-gold">You have prevented your first memory failure!</p>
            )}
          </>
        )}

        {step === 3 && (
          <>
            <button onClick={runHeal} disabled={loading || rateLimited}
              className="bg-gold text-background font-semibold px-6 py-2 rounded hover:bg-gold-dim transition disabled:opacity-50">
              {loading ? "Healing..." : "Get repair explanation →"}
            </button>
            {healResult && <pre className="mt-3 text-xs text-muted font-mono bg-surface-light rounded p-3 overflow-x-auto">{JSON.stringify(healResult, null, 2)}</pre>}
          </>
        )}

        {step === 4 && (
          <div className="text-center py-4">
            {completed ? (
              <div>
                <p className="text-2xl mb-2">Memory Governance Expert — Level 1</p>
                <p className="text-muted text-sm">Tutorial complete. {callCount} API calls used.</p>
              </div>
            ) : (
              <button onClick={finish} className="bg-gold text-background font-semibold px-8 py-3 rounded-lg">
                Complete Tutorial
              </button>
            )}
          </div>
        )}
      </div>

      <div className="flex justify-between">
        <button onClick={() => setStep(Math.max(0, step - 1))} disabled={step === 0}
          className="text-sm text-muted hover:text-foreground disabled:opacity-30">← Back</button>
        <button onClick={() => setStep(Math.min(4, step + 1))} disabled={step === 4}
          className="text-sm text-gold hover:underline disabled:opacity-30">Next →</button>
      </div>
    </div>
  );
}
