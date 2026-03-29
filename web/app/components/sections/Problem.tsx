const problems = [
  {
    icon: "&#9200;",
    title: "Stale data",
    description: "54-day-old memory triggers a $40K payment.",
    color: "text-red-400",
    border: "border-red-400/30",
  },
  {
    icon: "&#9878;",
    title: "Conflicting sources",
    description: "3 entries contradict each other. Agent picks one at random.",
    color: "text-yellow-400",
    border: "border-yellow-400/30",
  },
  {
    icon: "&#128065;",
    title: "No visibility",
    description: "You only find out after the wrong action.",
    color: "text-orange-400",
    border: "border-orange-400/30",
  },
];

export function Problem() {
  return (
    <section className="px-6 py-20 max-w-5xl mx-auto">
      <h2 className="text-3xl sm:text-4xl font-bold text-center mb-14">
        Your agent is one stale memory away from{" "}
        <span className="text-gold">a wrong decision.</span>
      </h2>
      <div className="grid md:grid-cols-3 gap-6">
        {problems.map((p) => (
          <div key={p.title} className={`border ${p.border} bg-surface rounded-xl p-8`}>
            <p className={`text-2xl mb-3 ${p.color}`} dangerouslySetInnerHTML={{ __html: p.icon }} />
            <p className={`font-semibold mb-2 ${p.color}`}>{p.title}</p>
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
