const tiers = [
  {
    name: "Free", price: "$0", period: "", description: "10,000 calls/month",
    features: ["All core features", "Demo key — no credit card", "10 risk components + repair plan"],
    cta: "Start free", ctaHref: "/playground", highlight: false,
  },
  {
    name: "Pro", price: "$0.001", period: " / call", description: "After 10,000 free calls",
    features: ["Webhooks + streaming", "Compliance profiles", "Priority support"],
    cta: "Get API Key", ctaHref: "https://app.sgraal.com", highlight: true,
  },
  {
    name: "Enterprise", price: "Custom", period: "", description: "Volume pricing",
    features: ["ZK mode — memory content never leaves your system", "SIEM export (Splunk / Datadog / Elastic)", "On-prem deployment option", "EU AI Act conformity declaration", "Memory Immunity Certificate", "Dedicated SLA + support", "Red Team as a Service"],
    cta: "Contact us", ctaHref: "mailto:hello@sgraal.com", highlight: false,
  },
];

export function Pricing() {
  return (
    <section id="pricing" style={{ backgroundColor: '#faf9f6' }}>
      <div className="max-w-7xl mx-auto px-8 md:px-16 py-24">
        <h2 className="font-headline text-4xl md:text-5xl font-extrabold tracking-tight mb-4" style={{ color: '#1a1c1a' }}>
          Simple <span style={{ color: '#c9a962' }}>pricing</span>
        </h2>
        <p className="text-lg mb-16" style={{ color: '#5e5e5e' }}>Start free. Scale when you need to.</p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-start">
          {tiers.map((t) => (
            <div key={t.name}
              className={`p-8 rounded-xl flex flex-col justify-between ${t.highlight ? "scale-105 z-10 relative" : ""}`}
              style={t.highlight
                ? { backgroundColor: '#efeeeb', border: '2px solid #c9a962', boxShadow: '0 12px 40px rgba(11,15,20,0.08)' }
                : { backgroundColor: '#ffffff', border: '1px solid rgba(208,197,180,0.2)', boxShadow: '0 4px 24px rgba(11,15,20,0.06)' }
              }>
              {t.highlight && (
                <span className="absolute -top-4 left-1/2 -translate-x-1/2 text-[10px] font-bold uppercase tracking-widest px-4 py-1.5 rounded-full"
                  style={{ backgroundColor: '#c9a962', color: '#533d00' }}>
                  Most popular
                </span>
              )}
              <div>
                <p className="text-[10px] font-bold tracking-widest uppercase mb-6" style={{ color: '#5e5e5e' }}>{t.name}</p>
                <p className="text-4xl font-extrabold font-headline mb-1" style={{ color: '#1a1c1a' }}>
                  {t.price}{t.period && <span className="text-lg font-normal" style={{ color: '#5e5e5e' }}>{t.period}</span>}
                </p>
                <p className="text-sm mb-8" style={{ color: '#5e5e5e' }}>{t.description}</p>
                <ul className="text-sm space-y-3 mb-10" style={{ color: '#5e5e5e' }}>
                  {t.features.map((f) => <li key={f}>· {f}</li>)}
                </ul>
              </div>
              <a href={t.ctaHref}
                className={`text-center text-sm font-semibold px-6 py-3 rounded-md transition-colors block ${t.highlight ? "gold-gradient-bg text-white" : ""}`}
                style={t.highlight ? {} : { border: '2px solid #c9a962', color: '#745b1c' }}>
                {t.cta}
              </a>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
