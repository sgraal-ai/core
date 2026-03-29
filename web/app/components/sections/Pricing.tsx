const tiers = [
  {
    name: "Free",
    price: "$0",
    period: "",
    description: "10,000 calls/month",
    features: ["All core features", "Demo key \u2014 no credit card", "10 risk components + repair plan"],
    cta: "Start free",
    ctaHref: "/playground",
    border: "border-surface-light",
  },
  {
    name: "Pro",
    price: "$0.001",
    period: " / call",
    description: "After 10,000 free calls",
    features: ["Webhooks + streaming", "Compliance profiles", "Priority support"],
    cta: "Get API Key",
    ctaHref: "#signup",
    border: "border-gold/30",
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "",
    description: "Volume pricing",
    features: ["SLA + dedicated support", "On-prem deployment option", "SIEM export + audit trail"],
    cta: "Contact us",
    ctaHref: "mailto:hello@sgraal.com",
    border: "border-surface-light",
  },
];

export function Pricing() {
  return (
    <section id="pricing" className="px-6 py-20 max-w-5xl mx-auto">
      <h2 className="text-3xl sm:text-4xl font-bold text-center mb-4">
        Simple <span className="text-gold">pricing</span>
      </h2>
      <p className="text-muted text-center max-w-xl mx-auto mb-14">
        Start free. Scale when you need to.
      </p>

      <div className="grid md:grid-cols-3 gap-6">
        {tiers.map((t) => (
          <div key={t.name} className={`border ${t.border} bg-surface rounded-xl p-8 flex flex-col`}>
            <p className="font-mono text-gold text-sm tracking-wider uppercase mb-2">{t.name}</p>
            <p className="text-4xl font-bold mb-1">
              {t.price}
              {t.period && <span className="text-lg text-muted font-normal">{t.period}</span>}
            </p>
            <p className="text-muted text-sm mb-6">{t.description}</p>
            <ul className="text-sm text-muted space-y-2 mb-8 flex-1">
              {t.features.map((f) => (
                <li key={f}>{f}</li>
              ))}
            </ul>
            <a href={t.ctaHref}
              className={`text-center text-sm font-semibold px-6 py-2.5 rounded-lg transition ${
                t.name === "Pro"
                  ? "bg-gold text-background hover:bg-gold-dim"
                  : "border border-surface-light text-foreground hover:bg-surface-light"
              }`}
            >
              {t.cta}
            </a>
          </div>
        ))}
      </div>
    </section>
  );
}
