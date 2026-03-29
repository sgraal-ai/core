export const metadata = { title: "COMPLY — Sgraal", description: "EU AI Act, HIPAA, MiFID2, Basel4, FDA, GDPR — built into every preflight call. Full audit trail. Cryptographic proof." };

const capabilities = [
  { title: "Compliance Engine", description: "4 built-in profiles: EU AI Act (Article 9, 12, 13), HIPAA \u00a7164.312, MiFID2, Basel4. Non-compliant + irreversible = automatic BLOCK. Conformity score 0\u20131. Declaration template export." },
  { title: "Memory Portability", description: "Memory Passport: cryptographically signed, portable memory envelope \u2014 provenance, freshness, conflict state, policy flags. Cross-LLM Translator: OpenAI \u2194 Anthropic \u2194 Llama compatible. Memory-DNS: globally unique identifiers (mem://user/123/preference/language). Memory Inheritance: validated memory transfer between agents." },
  { title: "Multi-agent Coordination", description: "Agent Air Traffic Control (ATC): which agent writes to which namespace, conflict prevention. Memory Court: formal causal inference + Z3 SMT solver for contradicting agents. Memory Commons: shared organizational memory graph with RBAC. Cross-agent Firewall: agent A writes \u2192 Sgraal validates \u2192 agent B sees only if omega < 50." },
  { title: "Audit Trail & Last Will", description: "Full tamper-proof audit log with SHA256 chain. Memory Last Will & Testament: GDPR right-to-be-forgotten AND EU AI Act 10-year audit trail \u2014 handled simultaneously. legal_hold_entries: never deleted. SIEM export." },
];

export default function ComplyPage() {
  return (
    <div className="max-w-4xl mx-auto py-16 px-6">
      <p className="text-gold font-mono text-sm tracking-widest uppercase mb-3">COMPLY</p>
      <h1 className="text-4xl sm:text-5xl font-bold mb-4">Meet every regulation. Prove it.</h1>
      <p className="text-muted text-lg mb-12">EU AI Act, HIPAA, MiFID2, Basel4, FDA, GDPR \u2014 built into every preflight call. Full audit trail. Cryptographic proof.</p>

      <h2 className="text-xl font-semibold mb-6">How it works</h2>
      <div className="space-y-6 mb-14">
        {[
          ["Every decision is compliance-checked in real time", "Compliance profile (EU_AI_ACT / HIPAA / MIFID2 / BASEL4 / FDA) is evaluated on every preflight call. Non-compliant + irreversible action = automatic BLOCK before the decision is made."],
          ["Every decision is logged with tamper-proof audit trail", "SHA256 hash chain. request_id, omega_mem_final, component_breakdown, action_override_chain \u2014 all recorded. SIEM export: Splunk / Datadog / Elastic."],
          ["Compliance reports generated on demand", "/v1/compliance/eu-ai-act/report \u2014 Article 9/12/13/14/17 evidence. Conformity declaration template. Chain verify endpoint."],
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
        <pre className="text-sm font-mono text-foreground/80 overflow-x-auto leading-relaxed">{`result = client.preflight(
    memory_state=[...],
    action_type="financial",
    compliance_profile="EU_AI_ACT"
)
print(result.compliance_result.compliant)      # False
print(result.compliance_result.failed_article) # "Article_12"
print(result.recommended_action)               # "BLOCK"`}</pre>
      </div>

      <div className="text-center">
        <p className="text-xl font-semibold mb-4">Ready to prove compliance?</p>
        <a href="https://app.sgraal.com" className="bg-gold text-background font-semibold px-8 py-3 rounded-lg hover:bg-gold-dim transition inline-block">Get API Key</a>
      </div>
    </div>
  );
}
