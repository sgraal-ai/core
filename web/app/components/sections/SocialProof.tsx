const stats = [
  { value: "1,834", label: "Tests passed" },
  { value: "0", label: "Blockers" },
  { value: "300+", label: "Agent steps" },
  { value: "Zero", label: "Memory drift" },
];

export function SocialProof() {
  return (
    <section className="bg-background px-8 md:px-16 py-32 lg:py-48 text-center">
      <div className="max-w-5xl mx-auto">
        <p className="text-7xl text-primary-container/20 leading-none mb-4">&ldquo;</p>
        <blockquote className="font-headline text-3xl md:text-5xl font-bold tracking-tight mb-12 italic text-on-background">
          Ran 300+ step regulated test with zero drift.
        </blockquote>
        <p className="text-primary-container font-bold mb-16">@grok</p>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 py-12 border-y border-outline-variant/10 mb-12">
          {stats.map((s) => (
            <div key={s.label}>
              <p className="text-2xl font-bold text-primary-container mb-1">{s.value}</p>
              <p className="text-[10px] uppercase tracking-widest text-secondary font-bold">{s.label}</p>
            </div>
          ))}
        </div>

        <p className="text-secondary/60 italic font-light text-lg">
          When memory governance is visible, manipulation becomes accountable.
        </p>
      </div>
    </section>
  );
}
