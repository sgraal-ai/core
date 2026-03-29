const steps = [
  { n: "1", title: "An agent is about to act on memory.", body: "Before execution, it calls Sgraal with its memory state and intended action." },
  { n: "2", title: "Sgraal validates.", body: "108 models evaluate freshness, drift, provenance, conflict, compliance, and intent. Under 10ms." },
  { n: "3", title: "The agent acts safely — or stops.", body: "USE_MEMORY · WARN · ASK_USER · BLOCK. Every decision logged, traced, and explainable." },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="bg-background px-8 md:px-16 py-32 lg:py-48">
      <div className="max-w-7xl mx-auto">
        <p className="text-primary font-semibold text-lg mb-4 pt-4">
          Memory poisoning is invisible — <span className="text-primary-container">until Sgraal.</span>
        </p>
        <h2 className="font-headline text-5xl md:text-6xl font-extrabold tracking-tight text-on-background mb-24">
          How it works
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-16 relative">
          <div className="hidden md:block absolute top-10 left-0 w-full h-[1px] bg-outline-variant/20" />
          {steps.map((s) => (
            <div key={s.n} className="relative">
              <div className="w-14 h-14 rounded-full border-2 border-primary-container bg-background flex items-center justify-center text-2xl font-bold text-primary mb-6 relative z-10">
                {s.n}
              </div>
              <h3 className="text-2xl font-bold font-headline text-on-surface mb-4">{s.title}</h3>
              <p className="text-secondary leading-relaxed">{s.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
