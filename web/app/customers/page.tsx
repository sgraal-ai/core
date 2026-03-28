export const metadata = {
  title: "Customer Stories — Sgraal",
  description: "How teams in fintech, healthcare, and legal use Sgraal to govern AI agent memory and reduce decision risk.",
};

const CASES = [
  {
    industry: "Fintech",
    stage: "Series B, 80 engineers",
    problem: "Customer-facing trading assistant recommended stale positions. A EUR/USD recommendation was based on 3-day-old tool_state data that had already been invalidated by a market event. The agent had no way to know.",
    solution: "Added Sgraal preflight to every trade recommendation path. Weibull decay flagged tool_state entries older than 6 hours. Repair plan auto-triggered REFETCH on stale market data before any irreversible action.",
    results: [
      { metric: "67%", label: "reduction in stale-data recommendations" },
      { metric: "0", label: "regulatory incidents since deployment" },
      { metric: "< 15ms", label: "added latency per decision" },
    ],
    quote: "We thought our memory layer was fine. Sgraal showed us 41% of our tool_state entries were stale at decision time.",
  },
  {
    industry: "Healthcare",
    stage: "Enterprise, 500+ employees",
    problem: "Clinical decision support agent needed HIPAA-compliant audit trail. Previous audit took 3 weeks of manual log review. No way to prove memory freshness or source trust at decision time.",
    solution: "Deployed Sgraal with HIPAA compliance profile. Every agent decision now includes omega score, component breakdown, and Shapley attribution. EU AI Act profile added for EU patient data.",
    results: [
      { metric: "1 day", label: "audit completion (was 3 weeks)" },
      { metric: "0", label: "freshness violations in 6 months" },
      { metric: "100%", label: "decision traceability" },
    ],
    quote: "The compliance team went from dreading audits to running them on demand. Every decision is traceable to the exact memory state.",
  },
  {
    industry: "Legal Tech",
    stage: "SMB, 25 employees",
    problem: "Contract review agent occasionally cited outdated regulatory requirements. EU AI Act Article 13 transparency requirements were approaching. No audit trail existed.",
    solution: "Integrated Sgraal Python SDK with @guard() decorator. EU AI Act compliance profile enforces Article 12 logging and Article 13 transparency on every decision.",
    results: [
      { metric: "Article 13", label: "EU AI Act transparency achieved" },
      { metric: "3 lawyers", label: "saved 4 hours/week on memory verification" },
      { metric: "12 hours", label: "average memory freshness (was 45 days)" },
    ],
    quote: "We went from hoping our agent used current law to proving it. The compliance profile caught 3 outdated citations in the first week.",
  },
];

export default function CustomersPage() {
  return (
    <div className="max-w-4xl mx-auto py-16 px-6">
      <p className="text-gold font-mono text-sm tracking-widest uppercase mb-4">Customer Stories</p>
      <h1 className="text-3xl sm:text-4xl font-bold mb-4">Teams shipping safer AI agents</h1>
      <p className="text-muted text-lg mb-12">
        Anonymous case studies from teams using Sgraal in production across regulated industries.
      </p>

      <div className="space-y-12">
        {CASES.map((c, i) => (
          <div key={i} className="border border-surface-light rounded-xl overflow-hidden">
            <div className="bg-surface px-6 py-4 border-b border-surface-light flex items-center justify-between">
              <div>
                <span className="text-gold font-mono text-sm font-semibold">{c.industry}</span>
                <span className="text-muted text-sm ml-3">{c.stage}</span>
              </div>
            </div>
            <div className="p-6">
              <h3 className="font-semibold text-foreground mb-2">The Problem</h3>
              <p className="text-foreground/80 text-sm mb-4">{c.problem}</p>
              <h3 className="font-semibold text-foreground mb-2">The Solution</h3>
              <p className="text-foreground/80 text-sm mb-4">{c.solution}</p>
              <div className="grid grid-cols-3 gap-4 mb-4">
                {c.results.map((r, j) => (
                  <div key={j} className="text-center">
                    <p className="text-2xl font-bold text-gold">{r.metric}</p>
                    <p className="text-muted text-xs mt-1">{r.label}</p>
                  </div>
                ))}
              </div>
              <div className="border-t border-surface-light pt-4 mt-4">
                <p className="text-foreground/70 text-sm italic">&ldquo;{c.quote}&rdquo;</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="text-center mt-12">
        <a href="/#signup" className="bg-gold text-background font-semibold px-8 py-3 rounded-lg hover:bg-gold-dim transition inline-block">
          Start your story →
        </a>
      </div>
    </div>
  );
}
