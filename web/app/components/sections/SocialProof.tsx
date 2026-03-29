const stats = [
  { value: "1,834", label: "Tests" },
  { value: "0", label: "Failures" },
  { value: "300+", label: "Steps" },
  { value: "Zero", label: "Drift" },
];

export function SocialProof() {
  return (
    <section className="bg-background px-8 md:px-16 py-32 lg:py-48 text-center relative overflow-hidden">
      <div className="max-w-4xl mx-auto relative z-10">
        <div className="text-7xl text-primary-container/20 mb-8 select-none">&ldquo;</div>
        <blockquote className="font-headline text-3xl md:text-5xl font-bold tracking-tight mb-12 italic leading-tight">
          &ldquo;Ran 300+ step regulated test with zero drift.&rdquo;
        </blockquote>
        <div className="flex items-center justify-center gap-3 mb-16">
          <span className="font-bold text-on-surface">@grok</span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 py-12 border-y border-outline-variant/10">
          {stats.map((s) => (
            <div key={s.label} className="flex flex-col gap-1">
              <span className="text-2xl font-bold font-headline text-primary-container">{s.value}</span>
              <span className="text-[10px] uppercase tracking-widest text-secondary font-bold">{s.label}</span>
            </div>
          ))}
        </div>
        <p className="mt-12 text-secondary/60 italic font-light text-lg">
          When memory governance is visible, manipulation becomes accountable.
        </p>
      </div>
    </section>
  );
}
