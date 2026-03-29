export function Problem() {
  return (
    <section className="px-6 py-16 max-w-5xl mx-auto">
      <h2 className="text-3xl sm:text-4xl font-bold text-center mb-12">
        One wrong memory. <span className="text-gold">One wrong decision.</span>
      </h2>
      <div className="max-w-[680px] mx-auto text-center">
        <p className="text-foreground text-lg sm:text-xl leading-relaxed mb-6">
          Your AI agent is about to act. It has 47 memories to draw from. One of them is 54 days old,
          conflicts with two newer sources, and carries a commercial bias from a sponsored article it
          summarized last month.
        </p>
        <p className="text-gold text-xl font-semibold mb-4">
          Without Sgraal, it acts anyway.
        </p>
        <p className="text-muted text-base">
          OWASP Agentic AI Top 10 (2026): memory poisoning is the #1 threat in agentic systems.
        </p>
      </div>
    </section>
  );
}
