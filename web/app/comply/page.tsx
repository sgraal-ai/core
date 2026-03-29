export const metadata = { title: "COMPLY — Sgraal", description: "EU AI Act, HIPAA, MiFID2, Basel4, FDA, GDPR — built into every preflight call. Full audit trail. Cryptographic proof." };

const capabilities = [
  { title: "Compliance Engine", description: "4 built-in profiles: EU AI Act (Article 9, 12, 13), HIPAA §164.312, MiFID2, Basel4. Non-compliant + irreversible = automatic BLOCK." },
  { title: "Memory Portability", description: "Memory Passport: cryptographically signed portable envelope. Cross-LLM Translator: OpenAI ↔ Anthropic ↔ Llama. Memory-DNS: globally unique identifiers. Memory Inheritance: validated transfer." },
  { title: "Multi-agent Coordination", description: "ATC: namespace conflict prevention. Memory Court: causal inference + Z3 SMT solver. Memory Commons: shared org memory with RBAC. Cross-agent Firewall: validated writes, threshold-gated reads." },
  { title: "Audit Trail & Last Will", description: "Tamper-proof audit log with SHA256 chain. Memory Last Will: GDPR + EU AI Act 10-year retention — handled simultaneously. legal_hold_entries: never deleted. SIEM export." },
];

const howSteps = [
  ["Every decision is compliance-checked in real time", "Compliance profile evaluated on every preflight. Non-compliant + irreversible = automatic BLOCK."],
  ["Every decision is logged with tamper-proof audit trail", "SHA256 hash chain. request_id, omega, action_override_chain — all recorded. SIEM export: Splunk / Datadog / Elastic."],
  ["Compliance reports generated on demand", "/v1/compliance/eu-ai-act/report — Article 9/12/13/14/17 evidence. Conformity declaration template."],
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

export default function ComplyPage() {
  return (
    <div className="max-w-4xl mx-auto py-16 px-6">
      <p className="text-xs uppercase tracking-widest mb-3" style={S.label}>COMPLY</p>
      <h1 className="text-4xl sm:text-5xl mb-4" style={S.h1}>Meet every regulation. Prove it.</h1>
      <p className="text-lg mb-12" style={S.desc}>EU AI Act, HIPAA, MiFID2, Basel4, FDA, GDPR — built into every preflight call. Full audit trail. Cryptographic proof.</p>
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
        <pre className="text-sm overflow-x-auto leading-relaxed" style={S.codeText}>{`result = client.preflight(
    memory_state=[...],
    action_type="financial",
    compliance_profile="EU_AI_ACT"
)
print(result.compliance_result.compliant)      # False
print(result.recommended_action)               # "BLOCK"`}</pre>
      </div>
      <div className="text-center">
        <p className="text-xl mb-4" style={S.h2}>Ready to prove compliance?</p>
        <a href="https://app.sgraal.com" className="px-8 py-3 rounded-md transition inline-block" style={S.cta}>Get API Key</a>
      </div>
    </div>
  );
}
