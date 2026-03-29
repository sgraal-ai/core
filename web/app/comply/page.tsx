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
    <div style={{ backgroundColor: "#ffffff" }}>
      <div style={{ maxWidth: "80rem", margin: "0 auto", padding: "5rem 2rem" }}>
        <p className="font-bold tracking-widest text-xs uppercase mb-4" style={{ color: "#c9a962" }}>COMPLY</p>
        <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-black mb-4" style={{ fontFamily: "'Manrope', sans-serif" }}>Meet every regulation. Prove it.</h1>
        <p className="text-lg mb-16 text-gray-500">EU AI Act, HIPAA, MiFID2, Basel4, FDA, GDPR — built into every preflight call. Full audit trail. Cryptographic proof.</p>
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
          <pre className="text-sm overflow-x-auto leading-relaxed" style={{ color: "#e2e8f0", backgroundColor: "#0b0f14" }}>{`result = client.preflight(
    memory_state=[...],
    action_type="financial",
    compliance_profile="EU_AI_ACT"
)
print(result.compliance_result.compliant)  # False
print(result.recommended_action)           # "BLOCK"`}</pre>
        </div>
      </div>
      <div style={{ padding: "5rem 2rem", textAlign: "center" }} style={{ backgroundColor: "#f9f9f9" }}>
        <p className="text-2xl font-bold text-black mb-6" style={{ fontFamily: "'Manrope', sans-serif" }}>Ready to prove compliance?</p>
        <a href="https://app.sgraal.com" className="px-8 py-4 text-lg font-bold text-white rounded-md inline-block" style={{ background: "linear-gradient(135deg, #745b1c, #c9a962)" }}>Get API Key</a>
      </div>
    </div>
  );
}
