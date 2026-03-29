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
    <div className="bg-background">
      <div className="max-w-4xl mx-auto py-20 px-8">
        <p className="text-primary-container font-bold tracking-widest text-xs uppercase mb-4">DECIDE</p>
        <h1 className="font-headline text-4xl md:text-5xl font-extrabold tracking-tighter text-on-background mb-4">What the agent should do.</h1>
        <p className="text-secondary text-lg mb-16">Before every memory-based action, get a risk score, a decision, and a full explanation. Under 10ms.</p>
      </div>

      <div className="bg-surface-container-low px-8 py-20">
        <div className="max-w-4xl mx-auto">
          <h2 className="font-headline text-2xl font-bold text-on-background mb-10">How it works</h2>
          <div className="space-y-8">
            {howSteps.map(([title, desc], i) => (
              <div key={i} className="flex gap-5">
                <span className="w-14 h-14 rounded-full border-2 border-primary-container bg-surface-container-low flex items-center justify-center text-2xl font-bold text-primary shrink-0">{i + 1}</span>
                <div><p className="font-headline font-bold text-on-surface mb-1">{title}</p><p className="text-secondary text-sm">{desc}</p></div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-8 py-20">
        <h2 className="font-headline text-2xl font-bold text-on-background mb-10">Capabilities</h2>
        <div className="space-y-6">
          {capabilities.map((c) => (
            <div key={c.title} className="bg-surface-container-lowest rounded-xl shadow-[0_12px_40px_rgba(11,15,20,0.04)] border border-outline-variant/10 p-8">
              <p className="text-primary-container font-bold font-headline mb-2">{c.title}</p>
              <p className="text-secondary text-sm leading-relaxed">{c.description}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-8 pb-8">
        <div className="bg-[#0b0f14] rounded-xl p-8">
          <p className="text-[#6b6b6b] text-xs mb-4">Integration</p>
          <pre className="text-sm overflow-x-auto leading-relaxed text-[#e2e8f0]">{`from sgraal import SgraalClient
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

      <div className="bg-surface-container-low px-8 py-20 text-center">
        <p className="font-headline text-2xl font-bold text-on-background mb-6">Ready to make safer decisions?</p>
        <a href="https://app.sgraal.com" className="gold-gradient-bg px-8 py-4 text-lg font-bold text-white rounded-md inline-block">Get API Key</a>
      </div>
    </div>
  );
}
