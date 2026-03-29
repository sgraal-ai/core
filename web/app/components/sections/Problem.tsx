export function Problem() {
  return (
    <section className="bg-surface-container-low px-8 md:px-16 py-32 lg:py-40">
      <div className="max-w-7xl mx-auto flex flex-col lg:flex-row gap-20 items-start">
        <div className="lg:w-1/2">
          <h2 className="font-headline text-4xl md:text-5xl font-bold tracking-tight text-on-background mb-8 leading-tight text-balance">
            One wrong memory. <br /><span className="text-primary-container">One wrong decision.</span>
          </h2>
          <div className="space-y-8">
            <p className="text-lg md:text-xl leading-relaxed text-secondary/80">
              Your AI agent is about to act. It has 47 memories to draw from. One of them is 54 days old, conflicts with two newer sources, and carries a commercial bias from a sponsored article it summarized last month.
            </p>
            <span className="inline-flex items-center gap-2 text-lg font-semibold text-primary">
              Without Sgraal, it acts anyway.
            </span>
            <div className="pt-12 border-t border-outline-variant/10">
              <p className="text-xs font-label uppercase tracking-wider text-secondary/60 max-w-md">
                OWASP Agentic AI Top 10 (2026): memory poisoning is the #1 threat in agentic systems.
              </p>
            </div>
          </div>
        </div>
        <div className="lg:w-1/2 w-full">
          <div className="bg-surface-container-lowest p-8 rounded-xl shadow-[0_12px_40px_rgba(11,15,20,0.04)] border border-outline-variant/5">
            <div className="flex justify-between items-center mb-6">
              <div className="flex gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-error/40" />
                <div className="w-2.5 h-2.5 rounded-full bg-primary-container/40" />
                <div className="w-2.5 h-2.5 rounded-full bg-on-surface-variant/20" />
              </div>
              <span className="text-[10px] font-mono text-secondary/40">MEMORY_INSPECTION_BUFFER</span>
            </div>
            <div className="space-y-4 font-mono text-sm">
              <div className="p-3 bg-surface-container text-on-surface-variant rounded-md border-l-2 border-primary-container">
                <span className="text-secondary opacity-50 block mb-1">ID: mem_8422 // T-minus 54d</span>
                &quot;Apply 15% discount for premium users...&quot;
              </div>
              <div className="p-3 bg-surface-container-high text-on-surface-variant rounded-md">
                <span className="text-secondary opacity-50 block mb-1">ID: mem_9001 // T-minus 2h</span>
                &quot;All legacy discounts are deprecated as of Jan 1...&quot;
              </div>
              <div className="flex justify-center py-4">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ba1a1a" strokeWidth="2" className="animate-pulse"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
              </div>
              <div className="p-3 bg-error/5 text-error rounded-md border border-error/20 flex justify-between items-center">
                <span>CONFLICT_DETECTED</span>
                <span className="text-[10px] px-1.5 py-0.5 bg-error text-white rounded">BLOCK</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
