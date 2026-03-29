export const metadata = { title: "DECIDE — Sgraal", description: "Before every memory-based action, get a risk score, a decision, and a full explanation. Under 10ms." };

const capabilities = [
  { title: "Risk Decision Engine", description: "omega_mem_final: 0–100 risk score. USE_MEMORY / WARN / ASK_USER / BLOCK. Action multiplier: read 0.5× · irreversible 2.5×. Assurance score + confidence intervals." },
  { title: "Full Explanation", description: "Entry Shapley: which exact memory entry causes the risk. Causal graph: which entry caused drift in another. Natural language explanation in EN/DE/FR for developer, compliance officer, or executive." },
  { title: "Repair Plan", description: "REFRESH / DELETE / VERIFY / KEEP / WAIT per entry. Expected omega after heal. Closed-loop: heal + re-preflight in one call. MTTR prediction: p95 convergence steps." },
  { title: "Time Machine & Counterfactual", description: "Memory Time Machine: restore to any previous validated state. Counterfactual engine: what would the decision have been with different memory? Decision twin: parallel shadow execution." },
  { title: "AI Advertising Integrity", description: "commercial_intent score (0–1). sponsorship_probability. affiliate_pattern_detected. cross_agent_spread_risk. ad_integrity: PASS / WARN / BLOCK." },
];

const howSteps = [
  ["Send your memory state and action type", "POST /v1/preflight with memory entries, action_type (read/write/financial/irreversible), and domain."],
  ["108 models evaluate in parallel", "Freshness decay (Weibull) · drift detection (5-method ensemble) · provenance · conflict · causal graph · commercial intent."],
  ["Get a decision + full explanation", "omega_mem_final (0–100) · USE_MEMORY / WARN / ASK_USER / BLOCK · Entry Shapley attribution · repair plan."],
];

export default function DecidePage() {
  return (
    <div style={{ backgroundColor: "#ffffff", paddingTop: "5rem" }}>
      <div style={{ maxWidth: "80rem", margin: "0 auto", padding: "5rem 2rem" }}>
        <p className="font-bold tracking-widest text-xs uppercase mb-4" style={{ color: "#c9a962" }}>DECIDE</p>
        <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-black mb-4" style={{ fontFamily: "'Manrope', sans-serif" }}>What the agent should do.</h1>
        <p className="text-lg mb-16 text-gray-500">Before every memory-based action, get a risk score, a decision, and a full explanation. Under 10ms.</p>
      </div>

      <div style={{ backgroundColor: "#f9f9f9" }} style={{ padding: "5rem 2rem" }}>
        <div style={{ maxWidth: "56rem", margin: "0 auto" }}>
          <h2 className="text-2xl font-bold text-black mb-10" style={{ fontFamily: "'Manrope', sans-serif" }}>How it works</h2>
          <div className="space-y-8">
            {howSteps.map(([title, desc], i) => (
              <div key={i} className="flex gap-5">
                <span className="w-14 h-14 rounded-full flex items-center justify-center text-2xl font-bold shrink-0" style={{ border: "2px solid #c9a962", color: "#745b1c", backgroundColor: "#f9f9f9" }}>{i + 1}</span>
                <div><p className="font-bold text-black mb-1">{title}</p><p className="text-sm text-gray-500">{desc}</p></div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div style={{ maxWidth: "80rem", margin: "0 auto", padding: "5rem 2rem" }}>
        <h2 className="text-2xl font-bold text-black mb-10" style={{ fontFamily: "'Manrope', sans-serif" }}>Capabilities</h2>
        <div className="space-y-6">
          {capabilities.map((c) => (
            <div key={c.title} className="p-8 rounded-xl" style={{ backgroundColor: "#ffffff", boxShadow: "0 4px 24px rgba(11,15,20,0.08)", border: "1px solid rgba(208,197,180,0.2)" }}>
              <p className="font-bold mb-2" style={{ color: "#c9a962", fontFamily: "'Manrope', sans-serif" }}>{c.title}</p>
              <p className="text-sm leading-relaxed text-gray-500">{c.description}</p>
            </div>
          ))}
        </div>
      </div>

      <div style={{ maxWidth: "80rem", margin: "0 auto", padding: "0 2rem 2rem" }}>
        <div className="rounded-xl p-8" style={{ backgroundColor: "#0b0f14" }}>
          <p className="text-xs mb-4" style={{ color: "#6b6b6b" }}>Integration</p>
          <pre className="text-sm overflow-x-auto leading-relaxed" style={{ color: "#e2e8f0", backgroundColor: "#0b0f14" }}>{`from sgraal import SgraalClient
client = SgraalClient(api_key="demo")
result = client.preflight(
    memory_state=[{"id": "mem_001", "type": "tool_state",
        "timestamp_age_days": 54, "source_trust": 0.6}],
    action_type="irreversible", domain="fintech"
)
print(result.recommended_action)  # BLOCK
print(result.omega_mem_final)      # 78.4`}</pre>
        </div>
      </div>

      <div style={{ padding: "5rem 2rem", textAlign: "center" }} style={{ backgroundColor: "#f9f9f9" }}>
        <p className="text-2xl font-bold text-black mb-6" style={{ fontFamily: "'Manrope', sans-serif" }}>Ready to make safer decisions?</p>
        <a href="https://app.sgraal.com" className="px-8 py-4 text-lg font-bold text-white rounded-md inline-block" style={{ background: "linear-gradient(135deg, #745b1c, #c9a962)" }}>Get API Key</a>
      </div>
    </div>
  );
}
