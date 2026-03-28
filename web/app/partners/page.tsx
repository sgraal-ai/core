export const metadata = {
  title: "Partners — Sgraal",
  description: "Sgraal partner ecosystem: framework integrations, field reports, and the Sgraal Compliant badge.",
};

const BADGES = [
  "LangChain", "LangGraph", "LlamaIndex", "CrewAI", "AutoGen",
  "OpenAI", "Mem0", "Haystack", "Semantic Kernel", "Claude MCP",
  "Vercel AI SDK", "n8n", "Dify", "Zapier",
];

export default function PartnersPage() {
  return (
    <div className="max-w-4xl mx-auto py-16 px-6">
      <p className="text-gold font-mono text-sm tracking-widest uppercase mb-4">Partners</p>
      <h1 className="text-3xl sm:text-4xl font-bold mb-4">Building the memory governance ecosystem</h1>
      <p className="text-muted text-lg mb-12">
        Sgraal works with the frameworks your agents already use. No rip-and-replace.
      </p>

      <section className="mb-12">
        <h2 className="text-xl font-semibold mb-3">Field Report</h2>
        <div className="border border-gold/30 bg-surface rounded-xl p-8">
          <div className="flex items-start gap-4">
            <div className="text-gold text-3xl font-mono font-bold shrink-0">&ldquo;</div>
            <div>
              <p className="text-foreground/90 leading-relaxed mb-4">
                @grok ran 250 steps with zero drift using GrokGuard v2 + /v1/heal.
                healing_counter locked idempotent. 0.0% error rate. The preflight check adds
                under 15ms and has caught 3 stale tool_state entries that would have caused
                incorrect recommendations.
              </p>
              <div className="flex items-center gap-3">
                <span className="text-gold font-mono text-sm font-semibold">Grok / xAI</span>
                <span className="text-muted text-xs">Field report — GrokGuard v2 integration</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-xl font-semibold mb-6">Framework integrations</h2>
        <div className="flex flex-wrap gap-3">
          {BADGES.map((b) => (
            <span key={b} className="border border-surface-light bg-surface px-4 py-2 rounded-lg text-sm text-foreground/80 font-medium">
              {b}
            </span>
          ))}
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-xl font-semibold mb-3">Sgraal Compliant badge</h2>
        <div className="border border-surface-light rounded-lg p-6">
          <div className="flex items-center gap-6 mb-4">
            <div className="border-2 border-gold rounded-lg px-4 py-2 text-center">
              <p className="text-gold font-mono text-sm font-bold">SGRAAL</p>
              <p className="text-gold font-mono text-xs">COMPLIANT</p>
            </div>
            <div>
              <p className="text-foreground/90 text-sm mb-1">
                Add the Sgraal Compliant badge to your product to signal that your AI agent
                uses memory governance.
              </p>
              <p className="text-muted text-xs">
                Available as SVG and PNG. Requires active Sgraal integration.
              </p>
            </div>
          </div>
          <pre className="bg-background border border-surface-light rounded p-3 text-sm font-mono text-foreground/70 overflow-x-auto">
{`<a href="https://sgraal.com">
  <img src="https://sgraal.com/badge/compliant.svg"
       alt="Sgraal Compliant" width="120" />
</a>`}
          </pre>
        </div>
      </section>

      <section>
        <h2 className="text-xl font-semibold mb-3">Become a partner</h2>
        <p className="text-foreground/90 mb-2">
          Building an AI framework or memory system? We want to integrate.
        </p>
        <p className="text-foreground/90">
          Email <a href="mailto:partners@sgraal.com" className="text-gold hover:underline">partners@sgraal.com</a> with
          your framework, use case, and integration goals.
        </p>
      </section>
    </div>
  );
}
