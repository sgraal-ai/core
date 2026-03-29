const stats = [
  { value: "1,834 tests", label: "preflight accuracy \u00b7 drift detection \u00b7 poisoning resistance" },
  { value: "0 blockers", label: "production-ready at launch" },
  { value: "300+ steps", label: "external AI agent run \u00b7 zero memory drift" },
];

export function BattleTested() {
  return (
    <section className="px-6 py-16 max-w-5xl mx-auto">
      <h2 className="text-3xl sm:text-4xl font-bold text-center mb-14">
        Independent <span className="text-gold">validation</span>
      </h2>

      <div className="grid sm:grid-cols-3 gap-6 mb-10">
        {stats.map((s) => (
          <div key={s.value} className="border border-surface-light bg-surface rounded-xl p-6 text-center">
            <p className="text-2xl font-bold text-gold mb-2">{s.value}</p>
            <p className="text-muted text-xs leading-relaxed">{s.label}</p>
          </div>
        ))}
      </div>

      <div className="border border-surface-light bg-surface rounded-xl p-6 mb-8 text-center">
        <p className="text-muted text-sm mb-3 font-mono">58-step regulated run &middot; 97% assurance</p>
        <div className="bg-background border border-dashed border-surface-light rounded-lg flex items-center justify-center" style={{ minHeight: "120px" }}>
          <p className="text-muted text-xs italic">Screenshot coming</p>
        </div>
      </div>

      <div className="border border-gold/30 bg-surface rounded-xl p-8 text-center">
        <p className="text-foreground/90 leading-relaxed mb-3">
          Ran 300+ step regulated test with zero drift.
        </p>
        <span className="text-gold font-mono text-sm font-semibold">@grok</span>
      </div>
      <p className="text-sm text-muted text-center italic mt-4">
        When memory governance is visible, manipulation becomes accountable.
      </p>
    </section>
  );
}
