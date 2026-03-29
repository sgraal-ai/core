const steps = [
  { n: "1", title: "An agent is about to act on memory.", body: "Before execution, it calls Sgraal with its memory state and intended action." },
  { n: "2", title: "Sgraal validates.", body: "108 models evaluate freshness, drift, provenance, conflict, compliance, and intent. Under 10ms." },
  { n: "3", title: "The agent acts safely — or stops.", body: "USE_MEMORY · WARN · ASK_USER · BLOCK. Every decision logged, traced, and explainable." },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" style={{ backgroundColor: '#faf9f6' }}>
      <div className="max-w-7xl mx-auto px-8 md:px-16 py-20">
        <p className="text-lg font-semibold mb-6" style={{ color: '#745b1c' }}>
          Memory poisoning is invisible — <span style={{ color: '#c9a962' }}>until Sgraal.</span>
        </p>
        <h2 className="font-headline text-4xl md:text-5xl font-extrabold tracking-tight mb-16" style={{ color: '#1a1c1a' }}>
          How it works
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-16 relative">
          <div className="hidden md:block absolute top-10 left-0 w-full h-[1px]" style={{ backgroundColor: 'rgba(208,197,180,0.2)' }} />
          {steps.map((s) => (
            <div key={s.n} className="relative">
              <div className="w-14 h-14 rounded-full flex items-center justify-center text-2xl font-bold mb-6 relative z-10"
                style={{ border: '2px solid #c9a962', backgroundColor: '#faf9f6', color: '#745b1c' }}>
                {s.n}
              </div>
              <h3 className="text-2xl font-bold font-headline mb-4" style={{ color: '#1a1c1a' }}>{s.title}</h3>
              <p className="leading-relaxed" style={{ color: '#5e5e5e' }}>{s.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
