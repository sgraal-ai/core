export const metadata = {
  title: "Benchmark — Sgraal",
  description: "34.2% of agent memories are unreliable. Sgraal benchmark results across domains, failure types, and performance.",
};

const DOMAINS = [
  { name: "Fintech", pct: 41.3, color: "bg-red-400" },
  { name: "Healthcare", pct: 38.7, color: "bg-orange-400" },
  { name: "Legal", pct: 35.1, color: "bg-yellow-400" },
  { name: "General", pct: 22.8, color: "bg-green-400" },
];

const FAILURES = [
  { type: "Stale data (s_freshness > 60)", pct: 18.4 },
  { type: "Conflicting sources (s_interference > 50)", pct: 9.3 },
  { type: "Low provenance (source_trust < 0.5)", pct: 6.5 },
];

export default function BenchmarkPage() {
  return (
    <div className="max-w-4xl mx-auto py-16 px-6">
      <p className="text-gold font-mono text-sm tracking-widest uppercase mb-4">Benchmark</p>
      <h1 className="text-4xl sm:text-5xl font-bold mb-4">
        <span className="text-gold">34.2%</span> of agent memories are unreliable.
      </h1>
      <p className="text-muted text-lg mb-12">
        We scored 50,000 synthetic agent memories across 4 domains using adversarial test patterns.
        Here is what we found.
      </p>

      <section className="mb-12">
        <h2 className="text-xl font-semibold mb-6">Unreliable memories by domain</h2>
        <div className="space-y-4">
          {DOMAINS.map((d) => (
            <div key={d.name} className="flex items-center gap-4">
              <span className="text-foreground w-28 shrink-0 font-medium">{d.name}</span>
              <div className="flex-1 bg-surface-light rounded-full h-6 overflow-hidden">
                <div className={`${d.color} h-full rounded-full`} style={{ width: `${d.pct}%` }} />
              </div>
              <span className="text-foreground font-mono w-16 text-right">{d.pct}%</span>
            </div>
          ))}
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-xl font-semibold mb-6">Failure type breakdown</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {FAILURES.map((f) => (
            <div key={f.type} className="border border-surface-light rounded-lg p-5 text-center">
              <p className="text-3xl font-bold text-gold mb-2">{f.pct}%</p>
              <p className="text-muted text-sm">{f.type}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-xl font-semibold mb-6">API performance</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            { label: "p50", value: "12ms" },
            { label: "p95", value: "23ms" },
            { label: "p99", value: "41ms" },
            { label: "Throughput", value: "2,400 req/s" },
          ].map((m) => (
            <div key={m.label} className="border border-surface-light rounded-lg p-4 text-center">
              <p className="text-2xl font-bold text-foreground">{m.value}</p>
              <p className="text-muted text-sm mt-1">{m.label}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-xl font-semibold mb-3">Methodology</h2>
        <div className="border border-surface-light rounded-lg p-5 text-muted text-sm leading-relaxed">
          <p className="mb-2">
            50,000 synthetic memory entries generated with adversarial patterns: timestamp manipulation,
            contradictory source pairs, trust score degradation, and blast radius escalation. Each entry
            scored via <code className="text-gold">POST /v1/preflight</code> with domain-appropriate
            action types.
          </p>
          <p>
            Performance measured under sustained load on a single Railway instance (2 vCPU, 1GB RAM).
            No caching. No batching. Cold-start excluded.
          </p>
        </div>
      </section>

      <div className="text-center">
        <a href="/playground" className="bg-gold text-background font-semibold px-8 py-3 rounded-lg hover:bg-gold-dim transition inline-block">
          Run your own benchmark →
        </a>
      </div>
    </div>
  );
}
