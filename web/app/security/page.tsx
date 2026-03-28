export const metadata = {
  title: "Security — Sgraal",
  description: "How Sgraal protects your data: SHA-256 hashing, TLS 1.3, zero memory storage, responsible disclosure.",
};

export default function SecurityPage() {
  return (
    <div className="max-w-3xl mx-auto py-16 px-6">
      <h1 className="text-3xl font-bold mb-2">Security</h1>
      <p className="text-muted text-lg mb-10">How we protect your agent memory data.</p>

      <section className="mb-10">
        <h2 className="text-xl font-semibold mb-3">What We Protect</h2>
        <ul className="space-y-2 text-foreground/90">
          <li className="flex gap-2"><span className="text-gold shrink-0">&#10003;</span> API keys stored as SHA-256 hashes — plaintext keys are never persisted</li>
          <li className="flex gap-2"><span className="text-gold shrink-0">&#10003;</span> All API communication encrypted via TLS 1.3</li>
          <li className="flex gap-2"><span className="text-gold shrink-0">&#10003;</span> OAuth tokens use one-time exchange with 300-second expiry</li>
          <li className="flex gap-2"><span className="text-gold shrink-0">&#10003;</span> CORS restricted to sgraal.com and app.sgraal.com</li>
          <li className="flex gap-2"><span className="text-gold shrink-0">&#10003;</span> Rate limiting on all mutating endpoints</li>
          <li className="flex gap-2"><span className="text-gold shrink-0">&#10003;</span> Row-level security on every database table</li>
        </ul>
      </section>

      <section className="mb-10">
        <h2 className="text-xl font-semibold mb-3">What We Never Store</h2>
        <ul className="space-y-2 text-foreground/90">
          <li className="flex gap-2"><span className="text-red-400 shrink-0">&#10005;</span> Memory content — processed in real time, never persisted beyond the request</li>
          <li className="flex gap-2"><span className="text-red-400 shrink-0">&#10005;</span> Plaintext API keys — only SHA-256 hashes are stored</li>
          <li className="flex gap-2"><span className="text-red-400 shrink-0">&#10005;</span> Embedding vectors — used for scoring, discarded after response</li>
          <li className="flex gap-2"><span className="text-red-400 shrink-0">&#10005;</span> PII from memory entries — the scoring engine is content-agnostic</li>
        </ul>
      </section>

      <section className="mb-10">
        <h2 className="text-xl font-semibold mb-3">Infrastructure</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {[
            { name: "API", desc: "Railway (US region), auto-scaling, health-checked" },
            { name: "Database", desc: "Supabase PostgreSQL with row-level security on every table" },
            { name: "State", desc: "Upstash Redis with TTL on all keys, encrypted at rest" },
            { name: "Frontend", desc: "Vercel Edge Network, static generation, no server-side user data" },
          ].map((i) => (
            <div key={i.name} className="border border-surface-light rounded-lg p-4">
              <p className="font-semibold text-foreground mb-1">{i.name}</p>
              <p className="text-muted text-sm">{i.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mb-10">
        <h2 className="text-xl font-semibold mb-3">Responsible Disclosure</h2>
        <div className="border border-gold/30 bg-surface rounded-lg p-6">
          <p className="text-foreground/90 mb-3">
            Found a vulnerability? We take security seriously and respond within <span className="text-gold font-semibold">48 hours</span>.
          </p>
          <p className="text-foreground/90 mb-3">
            Email: <a href="mailto:security@sgraal.com" className="text-gold hover:underline">security@sgraal.com</a>
          </p>
          <p className="text-muted text-sm">
            CVE disclosure timeline: 90 days from report to public disclosure. We coordinate with reporters on fix timelines.
          </p>
        </div>
      </section>

      <section>
        <h2 className="text-xl font-semibold mb-3">Open Source</h2>
        <p className="text-foreground/90">
          Sgraal is licensed under{" "}
          <a href="https://github.com/sgraal-ai/core/blob/main/LICENSE" target="_blank" rel="noopener noreferrer" className="text-gold hover:underline">Apache 2.0</a>.
          The scoring engine, API, and all SDKs are open source. Audit the code yourself.
        </p>
      </section>
    </div>
  );
}
