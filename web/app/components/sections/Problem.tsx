export function Problem() {
  return (
    <section style={{ backgroundColor: '#f4f3f0' }}>
      <div className="max-w-7xl mx-auto px-8 md:px-16 py-24 flex flex-col lg:flex-row gap-16 items-start">
        <div className="lg:w-1/2">
          <h2 className="font-headline text-4xl md:text-5xl font-bold tracking-tight leading-tight mb-8"
            style={{ color: '#1a1c1a' }}>
            One wrong memory.{" "}
            <span style={{ color: '#c9a962' }}>One wrong decision.</span>
          </h2>
          <p className="text-lg md:text-xl leading-relaxed mb-8" style={{ color: 'rgba(94,94,94,0.8)' }}>
            Your AI agent is about to act. It has 47 memories to draw from. One of them is 54 days old,
            conflicts with two newer sources, and carries a commercial bias from a sponsored article it
            summarized last month.
          </p>
          <p className="inline-flex items-center gap-2 text-lg font-semibold mb-8" style={{ color: '#745b1c' }}>
            Without Sgraal, it acts anyway.
          </p>
          <div className="pt-12" style={{ borderTop: '1px solid rgba(208,197,180,0.1)' }}>
            <p className="text-xs uppercase tracking-wider" style={{ color: 'rgba(94,94,94,0.6)' }}>
              OWASP Agentic AI Top 10 (2026): memory poisoning is the #1 threat in agentic systems.
            </p>
          </div>
        </div>
        <div className="lg:w-1/2">
          <div className="p-8 rounded-xl" style={{ backgroundColor: '#ffffff', boxShadow: '0 12px 40px rgba(11,15,20,0.04)', border: '1px solid rgba(208,197,180,0.05)' }}>
            <div className="space-y-6 font-mono text-sm">
              <div>
                <p className="text-xs mb-1" style={{ color: 'rgba(94,94,94,0.5)' }}>mem_8422 // T-minus 54d</p>
                <p style={{ color: '#1a1c1a' }}>&quot;Apply 15% discount for premium users...&quot;</p>
              </div>
              <div>
                <p className="text-xs mb-1" style={{ color: 'rgba(94,94,94,0.5)' }}>mem_9001 // T-minus 2h</p>
                <p style={{ color: '#1a1c1a' }}>&quot;All legacy discounts are deprecated as of Jan 1...&quot;</p>
              </div>
              <div className="flex justify-center py-4">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#ba1a1a" strokeWidth="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
              </div>
              <div className="text-center">
                <p className="font-bold text-xs uppercase tracking-widest mb-2" style={{ color: '#ba1a1a' }}>CONFLICT_DETECTED</p>
                <span className="inline-block px-3 py-1 text-xs font-bold rounded-md uppercase text-white" style={{ backgroundColor: '#ba1a1a' }}>BLOCK</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
