const steps = [
  { step: "1", title: "An agent is about to act on memory.", description: "Before execution, it calls Sgraal with its memory state and intended action." },
  { step: "2", title: "Sgraal validates.", description: "108 models evaluate freshness, drift, provenance, conflict, compliance, and intent. Under 10ms." },
  { step: "3", title: "The agent acts safely — or stops.", description: "USE_MEMORY · WARN · ASK_USER · BLOCK. Every decision logged, traced, and explainable." },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="px-6 py-14 max-w-5xl mx-auto">
      <h2 className="text-3xl sm:text-4xl text-center mb-4" style={{ fontFamily: "'Manrope', sans-serif", fontWeight: 800, color: "var(--on-surface)" }}>
        How Sgraal <span style={{ color: "var(--primary-container)" }}>works</span>
      </h2>
      <p className="text-xl text-center mb-12 max-w-3xl mx-auto" style={{ fontFamily: "'Inter', sans-serif" }}>
        <span style={{ color: "var(--on-surface)" }}>Memory poisoning is invisible — </span>
        <span style={{ color: "var(--primary-container)" }}>until Sgraal.</span>
      </p>
      <div className="grid md:grid-cols-3 gap-8 relative">
        <div className="hidden md:block absolute top-4 left-[16.67%] right-[16.67%] h-px" style={{ backgroundColor: "var(--outline-variant)", opacity: 0.4 }} />
        {steps.map((s) => (
          <div key={s.step} className="relative">
            <div className="flex items-center gap-3 mb-4">
              <span className="w-8 h-8 rounded-full flex items-center justify-center text-sm shrink-0 relative z-10"
                style={{ backgroundColor: "var(--primary-container)", color: "var(--on-primary-container)", fontFamily: "'Manrope', sans-serif", fontWeight: 700 }}>
                {s.step}
              </span>
              <h3 className="text-lg" style={{ fontFamily: "'Manrope', sans-serif", fontWeight: 700, color: "var(--on-surface)" }}>{s.title}</h3>
            </div>
            <p className="text-sm" style={{ fontFamily: "'Inter', sans-serif", color: "var(--on-surface-variant)" }}>{s.description}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
