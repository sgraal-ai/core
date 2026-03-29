export function Problem() {
  return (
    <section className="px-6 py-14" style={{ backgroundColor: "var(--surface-container-low)" }}>
      <div className="max-w-5xl mx-auto">
        <h2 className="text-3xl sm:text-4xl text-center mb-12" style={{ fontFamily: "'Manrope', sans-serif", fontWeight: 800, color: "var(--on-surface)" }}>
          One wrong memory. <span style={{ color: "var(--primary-container)" }}>One wrong decision.</span>
        </h2>
        <div className="max-w-[680px] mx-auto text-center">
          <p className="text-lg sm:text-xl leading-relaxed mb-6" style={{ fontFamily: "'Inter', sans-serif", color: "var(--on-surface-variant)" }}>
            Your AI agent is about to act. It has 47 memories to draw from. One of them is 54 days old,
            conflicts with two newer sources, and carries a commercial bias from a sponsored article it
            summarized last month.
          </p>
          <p className="text-xl mb-4" style={{ color: "var(--primary-container)", fontWeight: 600 }}>
            Without Sgraal, it acts anyway.
          </p>
          <p className="text-sm" style={{ color: "var(--on-surface-variant)" }}>
            OWASP Agentic AI Top 10 (2026): memory poisoning is the #1 threat in agentic systems.
          </p>
        </div>
      </div>
    </section>
  );
}
