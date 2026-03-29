export function Problem() {
  return (
    <section className="bg-surface-container-low px-8 md:px-16 py-32 lg:py-40">
      <div className="max-w-7xl mx-auto flex flex-col lg:flex-row gap-20 items-start">
        <div className="lg:w-1/2">
          <h2 className="font-headline text-4xl md:text-5xl font-bold tracking-tight text-on-background mb-8 leading-tight">
            One wrong memory.{" "}
            <span className="text-primary-container">One wrong decision.</span>
          </h2>
          <p className="text-lg md:text-xl leading-relaxed text-secondary/80 mb-8">
            Your AI agent is about to act. It has 47 memories to draw from. One of them is 54 days old,
            conflicts with two newer sources, and carries a commercial bias from a sponsored article it
            summarized last month.
          </p>
          <p className="inline-flex items-center gap-2 text-lg font-semibold text-primary mb-8">
            Without Sgraal, it acts anyway.
          </p>
          <div className="pt-12 border-t border-outline-variant/10">
            <p className="text-xs font-label uppercase tracking-wider text-secondary/60">
              OWASP Agentic AI Top 10 (2026): memory poisoning is the #1 threat in agentic systems.
            </p>
          </div>
        </div>
        <div className="lg:w-1/2">
          <div className="bg-surface-container-lowest p-8 rounded-xl shadow-[0_12px_40px_rgba(11,15,20,0.04)] border border-outline-variant/5">
            <div className="space-y-6 font-mono text-sm">
              <div>
                <p className="text-secondary/50 text-xs mb-1">mem_8422 // T-minus 54d</p>
                <p className="text-on-surface">&quot;Apply 15% discount for premium users...&quot;</p>
              </div>
              <div>
                <p className="text-secondary/50 text-xs mb-1">mem_9001 // T-minus 2h</p>
                <p className="text-on-surface">&quot;All legacy discounts are deprecated as of Jan 1...&quot;</p>
              </div>
              <div className="flex justify-center py-4">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#ba1a1a" strokeWidth="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
              </div>
              <div className="text-center">
                <p className="text-error font-bold text-xs uppercase tracking-widest mb-2">CONFLICT_DETECTED</p>
                <span className="inline-block px-3 py-1 bg-error text-on-error text-xs font-bold rounded-md uppercase">BLOCK</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
