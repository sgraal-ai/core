const steps = [
  {
    step: "1",
    title: "Send your memory state",
    description: "Agent calls /v1/preflight before acting.",
    detail: "POST with memory entries, action type, and domain.",
  },
  {
    step: "2",
    title: "108 models evaluate",
    description: "Freshness decay \u00b7 drift detection \u00b7 provenance \u00b7 conflict \u00b7 causal graph.",
    detail: "Weibull decay per memory type. Sheaf cohomology for conflicts. Under 10ms.",
  },
  {
    step: "3",
    title: "Get a decision",
    description: "USE_MEMORY / WARN / ASK_USER / BLOCK",
    detail: "Omega score + repair plan + entry-level Shapley attribution.",
  },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="px-6 py-20 max-w-5xl mx-auto">
      <h2 className="text-3xl sm:text-4xl font-bold text-center mb-14">
        How it <span className="text-gold">works</span>
      </h2>
      <div className="grid md:grid-cols-3 gap-8">
        {steps.map((s) => (
          <div key={s.step} className="relative">
            <div className="flex items-center gap-3 mb-4">
              <span className="w-8 h-8 rounded-full bg-gold text-background flex items-center justify-center font-mono font-bold text-sm shrink-0">
                {s.step}
              </span>
              <h3 className="font-semibold text-foreground">{s.title}</h3>
            </div>
            <p className="text-foreground/90 text-sm mb-2">{s.description}</p>
            <p className="text-muted text-xs">{s.detail}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
