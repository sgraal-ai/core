const problems = [
  {
    title: "Stale data",
    description: "54-day-old memory triggers a $40K payment.",
  },
  {
    title: "Conflicting sources",
    description: "3 entries contradict each other. Agent picks one at random.",
  },
  {
    title: "No visibility",
    description: "You only find out after the wrong action.",
  },
];

export function Problem() {
  return (
    <section className="px-6 py-16 max-w-5xl mx-auto">
      <h2 className="text-3xl sm:text-4xl font-bold text-center mb-14">
        Your agent is one stale memory away from{" "}
        <span className="text-gold">a wrong decision.</span>
      </h2>
      <div className="grid md:grid-cols-3 gap-6">
        {problems.map((p) => (
          <div key={p.title} className="border border-surface-light border-l-2 border-l-gold bg-surface rounded-xl p-8">
            <p className="font-semibold mb-2 text-gold">{p.title}</p>
            <p className="text-muted text-sm">{p.description}</p>
          </div>
        ))}
      </div>
      <p className="text-center text-muted text-xs mt-8">
        OWASP Agentic AI Top 10 (2026): memory poisoning is the #1 threat.
      </p>
      <div className="mt-12 pt-10 border-t border-gold/20 text-center">
        <p className="text-2xl sm:text-3xl font-bold">
          Memory poisoning is invisible — <span className="text-gold">until Sgraal.</span>
        </p>
        <p className="text-lg sm:text-xl text-muted mt-3">
          Every injection leaves a trace. Every decision is provable.
        </p>
      </div>
    </section>
  );
}
