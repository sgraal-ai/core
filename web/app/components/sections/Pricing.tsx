const tiers = [
  {
    name: "Free", price: "$0", period: "", description: "10,000 calls/month",
    features: ["All core features", "Demo key — no credit card", "10 risk components + repair plan"],
    cta: "Start free", ctaHref: "/playground", highlight: false,
    btnClass: "border-2 border-primary-container text-primary rounded-md",
  },
  {
    name: "Pro", price: "$0.001", period: " / call", description: "After 10,000 free calls",
    features: ["Webhooks + streaming", "Compliance profiles", "Priority support"],
    cta: "Get API Key", ctaHref: "https://app.sgraal.com", highlight: true,
    btnClass: "gold-gradient-bg text-white rounded-md",
  },
  {
    name: "Enterprise", price: "Custom", period: "", description: "Volume pricing",
    features: ["ZK mode — memory content never leaves your system", "SIEM export (Splunk / Datadog / Elastic)", "On-prem deployment option", "EU AI Act conformity declaration", "Memory Immunity Certificate", "Dedicated SLA + support", "Red Team as a Service"],
    cta: "Contact us", ctaHref: "mailto:hello@sgraal.com", highlight: false,
    btnClass: "bg-surface-container-highest text-on-surface rounded-md",
  },
];

export function Pricing() {
  return (
    <section id="pricing" className="bg-background px-8 md:px-16 py-32 lg:py-48">
      <div className="max-w-7xl mx-auto">
        <h2 className="font-headline text-5xl md:text-6xl font-extrabold tracking-tight text-on-background mb-4">
          Simple <span className="text-primary-container">pricing</span>
        </h2>
        <p className="text-secondary mb-20 text-lg">Start free. Scale when you need to.</p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-start">
          {tiers.map((t) => (
            <div key={t.name}
              className={`p-10 rounded-xl flex flex-col justify-between ${
                t.highlight
                  ? "bg-surface-container border-2 border-primary-container scale-105 z-10 relative shadow-[0_12px_40px_rgba(11,15,20,0.08)]"
                  : "bg-surface-container-lowest border border-outline-variant/20 shadow-[0_12px_40px_rgba(11,15,20,0.04)]"
              }`}>
              {t.highlight && (
                <span className="absolute -top-4 left-1/2 -translate-x-1/2 bg-primary-container text-on-primary-container text-[10px] font-bold uppercase tracking-widest px-4 py-1.5 rounded-full">
                  Most popular
                </span>
              )}
              <p className="text-[10px] font-bold tracking-widest uppercase text-secondary mb-6">{t.name}</p>
              <p className="text-4xl font-extrabold font-headline text-on-surface mb-1">
                {t.price}{t.period && <span className="text-lg font-normal text-secondary">{t.period}</span>}
              </p>
              <p className="text-sm text-secondary mb-8">{t.description}</p>
              <ul className="text-sm text-secondary space-y-3 mb-10 flex-1">
                {t.features.map((f) => <li key={f}>· {f}</li>)}
              </ul>
              <a href={t.ctaHref} className={`text-center text-sm font-semibold px-6 py-3 transition-colors block ${t.btnClass}`}>
                {t.cta}
              </a>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
