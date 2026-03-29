const moments = [
  {
    title: "Preflight decision gate",
    description: "One API call before any memory-based action. Your agent asks permission before it acts.",
  },
  {
    title: "Compliance engine",
    description: "EU AI Act \u00b7 HIPAA \u00b7 MiFID2 \u00b7 Basel4 built in. One field in the request.",
  },
  {
    title: "Weibull decay",
    description: "Probabilistic freshness, not a simple timestamp cutoff. Tool state decays in hours. Identity persists for years.",
  },
  {
    title: "Action checkpoint",
    description: "Same memory, different risk. Read: 1.0\u00d7. Irreversible: 1.8\u00d7. Destructive: 2.5\u00d7.",
  },
  {
    title: "Entry Shapley",
    description: "Pinpoints the exact memory entry causing the block. Not just \u201chigh risk\u201d \u2014 which entry and why.",
  },
  {
    title: "Zero-friction entry",
    description: "pip install sgraal. 3 lines of code. No signup. Demo key works immediately.",
  },
];

export function AhaMoments() {
  return (
    <section className="px-6 py-20 max-w-5xl mx-auto">
      <h2 className="text-3xl sm:text-4xl font-bold text-center mb-14">
        Six reasons teams <span className="text-gold">switch</span>
      </h2>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {moments.map((m) => (
          <div key={m.title} className="border border-surface-light bg-surface rounded-xl p-6">
            <p className="font-semibold text-foreground mb-2">{m.title}</p>
            <p className="text-muted text-sm leading-relaxed">{m.description}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
