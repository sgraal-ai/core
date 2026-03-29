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
        Three failures. <span className="text-gold">One API call away.</span>
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
    </section>
  );
}
