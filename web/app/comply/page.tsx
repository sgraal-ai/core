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

export default function ComplyPage() {
  return (
    <div style={{ backgroundColor: "#faf9f6" }}>
      <div className="max-w-7xl mx-auto px-8 md:px-16 py-20">
        <p className="text-primary-container font-bold tracking-widest text-xs uppercase mb-4">COMPLY</p>
        <h1 className="font-headline text-4xl md:text-5xl font-extrabold tracking-tighter text-on-background mb-4">Meet every regulation. Prove it.</h1>
        <p className="text-secondary text-lg mb-16">EU AI Act, HIPAA, MiFID2, Basel4, FDA, GDPR — built into every preflight call. Full audit trail. Cryptographic proof.</p>
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
      <div className="max-w-7xl mx-auto px-8 md:px-16 py-20">
        <h2 className="font-headline text-2xl font-bold text-on-background mb-10">Capabilities</h2>
        <div className="space-y-6">
          {capabilities.map((c) => (
            <div key={c.title} className="p-8 rounded-xl flex flex-col" style={{ backgroundColor: "#ffffff", boxShadow: "0 4px 24px rgba(11,15,20,0.08)", border: "1px solid rgba(208,197,180,0.2)" }}>
              <p className="text-primary-container font-bold font-headline mb-2">{c.title}</p>
              <p className="text-secondary text-sm leading-relaxed">{c.description}</p>
            </div>
          ))}
        </div>
      </div>
      <div className="max-w-7xl mx-auto px-8 md:px-16 pb-8">
        <div className="bg-[#0b0f14] rounded-xl p-8">
          <p className="text-[#6b6b6b] text-xs mb-4">Integration</p>
          <pre className="text-sm overflow-x-auto leading-relaxed text-[#e2e8f0]">{`result = client.preflight(
    memory_state=[...],
    action_type="financial",
    compliance_profile="EU_AI_ACT"
)
print(result.compliance_result.compliant)  # False
print(result.recommended_action)           # "BLOCK"`}</pre>
        </div>
      </div>
      <div className="px-8 md:px-16 py-20 text-center" style={{ backgroundColor: "#f4f3f0" }}>
        <p className="font-headline text-2xl font-bold text-on-background mb-6">Ready to prove compliance?</p>
        <a href="https://app.sgraal.com" className="gold-gradient-bg px-8 py-4 text-lg font-bold text-white rounded-md inline-block">Get API Key</a>
      </div>
    </div>
  );
}
