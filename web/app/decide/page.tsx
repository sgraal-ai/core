export const metadata = { title: "DECIDE — Sgraal", description: "Before every memory-based action, get a risk score, a decision, and a full explanation. Under 10ms." };

const capabilities = [
  { title: "Risk Decision Engine", description: "omega_mem_final: 0\u2013100 risk score. USE_MEMORY / WARN / ASK_USER / BLOCK. Action multiplier: read 0.5\u00d7 \u00b7 irreversible 2.5\u00d7. Assurance score + confidence intervals." },
  { title: "Full Explanation", description: "Entry Shapley: which exact memory entry causes the risk. Causal graph: which entry caused drift in another. Natural language explanation in EN/DE/FR for developer, compliance officer, or executive." },
  { title: "Repair Plan", description: "REFRESH / DELETE / VERIFY / KEEP / WAIT per entry. Expected omega after heal. Closed-loop: heal + re-preflight in one call. MTTR prediction: p95 convergence steps." },
  { title: "Time Machine & Counterfactual", description: "Memory Time Machine: restore to any previous validated state. Counterfactual engine: \u2018what would the decision have been with different memory?\u2019 Decision twin: parallel shadow execution." },
  { title: "AI Advertising Integrity", description: "commercial_intent score (0\u20131). sponsorship_probability. affiliate_pattern_detected. cross_agent_spread_risk. ad_integrity: PASS / WARN / BLOCK. Detects economically manipulated recommendations." },
];

export default function DecidePage() {
  return (
    <div className="max-w-4xl mx-auto py-16 px-6">
      <p className="text-gold font-mono text-sm tracking-widest uppercase mb-3">DECIDE</p>
      <h1 className="text-4xl sm:text-5xl font-bold mb-4">What the agent should do.</h1>
      <p className="text-muted text-lg mb-12">Before every memory-based action, get a risk score, a decision, and a full explanation. Under 10ms.</p>

      <h2 className="text-xl font-semibold mb-6">How it works</h2>
      <div className="space-y-6 mb-14">
        {[
          ["Send your memory state and action type", "POST /v1/preflight with memory entries, action_type (read/write/financial/irreversible), and domain."],
          ["108 models evaluate in parallel", "Freshness decay (Weibull) \u00b7 drift detection (5-method ensemble) \u00b7 provenance \u00b7 conflict \u00b7 causal graph \u00b7 commercial intent."],
          ["Get a decision + full explanation", "omega_mem_final (0\u2013100) \u00b7 USE_MEMORY / WARN / ASK_USER / BLOCK \u00b7 Entry Shapley attribution \u00b7 repair plan."],
        ].map(([title, desc], i) => (
          <div key={i} className="flex gap-4">
            <span className="w-7 h-7 rounded-full bg-gold text-background flex items-center justify-center font-mono font-bold text-xs shrink-0 mt-0.5">{i + 1}</span>
            <div><p className="font-semibold text-foreground mb-1">{title}</p><p className="text-muted text-sm">{desc}</p></div>
          </div>
        ))}
      </div>

      <h2 className="text-xl font-semibold mb-6">Capabilities</h2>
      <div className="space-y-4 mb-14">
        {capabilities.map((c) => (
          <div key={c.title} className="border border-surface-light bg-surface rounded-xl p-6">
            <p className="font-semibold text-gold mb-2">{c.title}</p>
            <p className="text-muted text-sm leading-relaxed">{c.description}</p>
          </div>
        ))}
      </div>

      <div className="bg-surface border border-surface-light rounded-xl p-6 mb-14">
        <p className="font-mono text-xs text-muted mb-3">Integration</p>
        <pre className="text-sm font-mono text-foreground/80 overflow-x-auto leading-relaxed">{`from sgraal import SgraalClient

client = SgraalClient(api_key="demo")
result = client.preflight(
    memory_state=[{
        "id": "mem_001",
        "type": "tool_state",
        "timestamp_age_days": 54,
        "source_trust": 0.6
    }],
    action_type="irreversible",
    domain="fintech"
)
print(result.recommended_action)  # BLOCK
print(result.omega_mem_final)      # 78.4
print(result.entry_shapley)        # {"mem_001": 0.67}`}</pre>
      </div>

      <div className="text-center">
        <p className="text-xl font-semibold mb-4">Ready to make safer decisions?</p>
        <a href="https://app.sgraal.com" className="bg-gold text-background font-semibold px-8 py-3 rounded-lg hover:bg-gold-dim transition inline-block">Get API Key</a>
      </div>
    </div>
  );
}
