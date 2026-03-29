export const metadata = { title: "DECIDE — Sgraal", description: "Before every memory-based action, get a risk score, a decision, and a full explanation. Under 10ms." };

const capabilities = [
  { title: "Risk Decision Engine", description: "omega_mem_final: 0\u2013100 risk score. USE_MEMORY / WARN / ASK_USER / BLOCK. Action multiplier: read 0.5\u00d7 \u00b7 irreversible 2.5\u00d7. Assurance score + confidence intervals." },
  { title: "Full Explanation", description: "Entry Shapley: which exact memory entry causes the risk. Causal graph: which entry caused drift in another. Natural language explanation in EN/DE/FR for developer, compliance officer, or executive." },
  { title: "Repair Plan", description: "REFRESH / DELETE / VERIFY / KEEP / WAIT per entry. Expected omega after heal. Closed-loop: heal + re-preflight in one call. MTTR prediction: p95 convergence steps." },
  { title: "Time Machine & Counterfactual", description: "Memory Time Machine: restore to any previous validated state. Counterfactual engine: \u2018what would the decision have been with different memory?\u2019 Decision twin: parallel shadow execution." },
  { title: "AI Advertising Integrity", description: "commercial_intent score (0\u20131). sponsorship_probability. affiliate_pattern_detected. cross_agent_spread_risk. ad_integrity: PASS / WARN / BLOCK. Detects economically manipulated recommendations." },
];

const howSteps = [
  ["Send your memory state and action type", "POST /v1/preflight with memory entries, action_type (read/write/financial/irreversible), and domain."],
  ["108 models evaluate in parallel", "Freshness decay (Weibull) \u00b7 drift detection (5-method ensemble) \u00b7 provenance \u00b7 conflict \u00b7 causal graph \u00b7 commercial intent."],
  ["Get a decision + full explanation", "omega_mem_final (0\u2013100) \u00b7 USE_MEMORY / WARN / ASK_USER / BLOCK \u00b7 Entry Shapley attribution \u00b7 repair plan."],
];

const S = {
  label: { fontFamily: "'Inter', sans-serif" as const, color: "var(--primary-container)", letterSpacing: "0.1em" } as const,
  h1: { fontFamily: "'Manrope', sans-serif" as const, fontWeight: 800 as const, color: "var(--on-surface)" } as const,
  desc: { color: "var(--on-surface-variant)" } as const,
  h2: { fontFamily: "'Manrope', sans-serif" as const, fontWeight: 700 as const, color: "var(--on-surface)" } as const,
  stepTitle: { fontWeight: 600 as const, color: "var(--on-surface)" } as const,
  card: { backgroundColor: "var(--surface-container-lowest)", boxShadow: "0 2px 12px rgba(11,15,20,0.06)" } as const,
  cardTitle: { fontFamily: "'Manrope', sans-serif" as const, fontWeight: 700 as const, color: "var(--primary-container)" } as const,
  code: { backgroundColor: "var(--obsidian)" } as const,
  codeText: { fontFamily: "'JetBrains Mono', monospace" as const, color: "#e2e8f0" } as const,
  cta: { background: "linear-gradient(135deg, #745b1c, #c9a962)", color: "#533d00", fontWeight: 600 as const } as const,
  step: { backgroundColor: "var(--primary-container)", color: "var(--on-primary-container)", fontFamily: "'Manrope', sans-serif" as const, fontWeight: 700 as const } as const,
};

export default function DecidePage() {
  return (
    <div className="max-w-4xl mx-auto py-16 px-6">
      <p className="text-xs uppercase tracking-widest mb-3" style={S.label}>DECIDE</p>
      <h1 className="text-4xl sm:text-5xl mb-4" style={S.h1}>What the agent should do.</h1>
      <p className="text-lg mb-12" style={S.desc}>Before every memory-based action, get a risk score, a decision, and a full explanation. Under 10ms.</p>

      <div className="py-10 px-6 -mx-6 mb-14 rounded-lg" style={{ backgroundColor: "var(--surface-container-low)" }}>
        <h2 className="text-xl mb-6" style={S.h2}>How it works</h2>
        <div className="space-y-6">
          {howSteps.map(([title, desc], i) => (
            <div key={i} className="flex gap-4">
              <span className="w-7 h-7 rounded-full flex items-center justify-center text-xs shrink-0 mt-0.5" style={S.step}>{i + 1}</span>
              <div><p className="mb-1" style={S.stepTitle}>{title}</p><p className="text-sm" style={S.desc}>{desc}</p></div>
            </div>
          ))}
        </div>
      </div>

      <h2 className="text-xl mb-6" style={S.h2}>Capabilities</h2>
      <div className="space-y-4 mb-14">
        {capabilities.map((c) => (
          <div key={c.title} className="rounded-lg p-6" style={S.card}>
            <p className="mb-2" style={S.cardTitle}>{c.title}</p>
            <p className="text-sm leading-relaxed" style={S.desc}>{c.description}</p>
          </div>
        ))}
      </div>

      <div className="rounded-lg p-6 mb-14" style={S.code}>
        <p className="text-xs mb-3" style={{ color: "rgba(255,255,255,0.5)" }}>Integration</p>
        <pre className="text-sm overflow-x-auto leading-relaxed" style={S.codeText}>{`from sgraal import SgraalClient

client = SgraalClient(api_key="demo")
result = client.preflight(
    memory_state=[{
        "id": "mem_001", "type": "tool_state",
        "timestamp_age_days": 54, "source_trust": 0.6
    }],
    action_type="irreversible", domain="fintech"
)
print(result.recommended_action)  # BLOCK
print(result.omega_mem_final)      # 78.4`}</pre>
      </div>

      <div className="text-center">
        <p className="text-xl mb-4" style={S.h2}>Ready to make safer decisions?</p>
        <a href="https://app.sgraal.com" className="px-8 py-3 rounded-md transition inline-block" style={S.cta}>Get API Key</a>
      </div>
    </div>
  );
}
