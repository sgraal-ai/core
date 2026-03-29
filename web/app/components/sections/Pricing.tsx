const tiers = [
  {
    name: "Free", price: "$0", period: "", description: "10,000 calls/month",
    features: ["All core features", "Demo key — no credit card", "10 risk components + repair plan"],
    cta: "Start free", ctaHref: "/playground", highlight: false, topBorder: "none",
  },
  {
    name: "Pro", price: "$0.001", period: " / call", description: "After 10,000 free calls",
    features: ["Webhooks + streaming", "Compliance profiles", "Priority support"],
    cta: "Get API Key", ctaHref: "#signup", highlight: true, topBorder: "3px solid var(--primary-container)",
  },
  {
    name: "Enterprise", price: "Custom", period: "", description: "Volume pricing",
    features: ["ZK mode — memory content never leaves your system", "SIEM export (Splunk / Datadog / Elastic)", "On-prem deployment option", "EU AI Act conformity declaration", "Memory Immunity Certificate", "Dedicated SLA + support", "Red Team as a Service"],
    cta: "Contact us", ctaHref: "mailto:hello@sgraal.com", highlight: false, topBorder: "3px solid rgba(26,28,26,0.2)",
  },
];

export function Pricing() {
  return (
    <section id="pricing" className="px-6 py-14 max-w-5xl mx-auto">
      <h2 className="text-3xl sm:text-4xl text-center mb-4" style={{ fontFamily: "'Manrope', sans-serif", fontWeight: 800, color: "var(--on-surface)" }}>
        Simple <span style={{ color: "var(--primary-container)" }}>pricing</span>
      </h2>
      <p className="text-center max-w-xl mx-auto mb-14" style={{ fontFamily: "'Inter', sans-serif", color: "var(--on-surface-variant)" }}>
        Start free. Scale when you need to.
      </p>
      <div className="grid md:grid-cols-3 gap-6">
        {tiers.map((t) => (
          <div key={t.name} className="rounded-lg p-7 flex flex-col justify-between"
            style={{ backgroundColor: "var(--surface-container-lowest)", boxShadow: t.highlight ? "0 12px 40px rgba(11,15,20,0.08)" : "0 2px 12px rgba(11,15,20,0.06)", borderTop: t.topBorder }}>
            <div>
              <p className="text-xs uppercase tracking-widest mb-2" style={{ fontFamily: "'Inter', sans-serif", color: "var(--on-surface-variant)", letterSpacing: "0.1em" }}>{t.name}</p>
              <p className="text-4xl mb-1" style={{ fontFamily: "'Manrope', sans-serif", fontWeight: 800, color: "var(--on-surface)" }}>
                {t.price}{t.period && <span className="text-lg font-normal" style={{ color: "var(--on-surface-variant)" }}>{t.period}</span>}
              </p>
              <p className="text-sm mb-6" style={{ color: "var(--on-surface-variant)" }}>{t.description}</p>
              <ul className="text-sm space-y-2 mb-8" style={{ fontFamily: "'Inter', sans-serif", color: "var(--on-surface-variant)" }}>
                {t.features.map((f) => <li key={f}>{f}</li>)}
              </ul>
            </div>
            <a href={t.ctaHref} className="text-center text-sm px-6 py-2.5 rounded-md transition block"
              style={t.highlight
                ? { background: "linear-gradient(135deg, #745b1c, #c9a962)", color: "#533d00", fontWeight: 600 }
                : { color: "var(--on-surface)", fontWeight: 500 }}>
              {t.cta}
            </a>
          </div>
        ))}
      </div>
    </section>
  );
}
