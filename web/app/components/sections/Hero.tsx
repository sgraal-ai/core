export function Hero() {
  return (
    <section className="relative overflow-hidden py-20 lg:py-28 flex flex-col items-center text-center">
      <div className="max-w-7xl mx-auto px-8 md:px-16 flex flex-col items-center">
        <div className="inline-flex items-center gap-2 px-4 py-1 rounded-full text-[10px] uppercase tracking-[0.2em] font-bold mb-12"
          style={{ backgroundColor: '#e9e8e5', border: '1px solid rgba(208,197,180,0.2)', color: '#5e5e5e' }}>
          <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ backgroundColor: '#c9a962' }} />
          Memory Governance Protocol
        </div>
        <h1 className="font-headline text-4xl md:text-5xl lg:text-6xl font-extrabold tracking-tighter max-w-5xl leading-[1.05] mb-6 text-balance"
          style={{ color: '#1a1c1a' }}>
          AI agents act on memory. Sgraal decides if that memory is{" "}
          <span style={{ color: '#c9a962' }}>safe to act on.</span>
        </h1>
        <p className="text-xl md:text-2xl max-w-2xl mx-auto mb-8 font-light leading-relaxed text-center"
          style={{ color: '#5e5e5e' }}>
          The memory governance protocol between AI agent memory and AI agent action.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-8">
          <a href="/playground" className="gold-gradient-bg px-8 py-4 text-lg font-bold text-white rounded-md">
            Try it now — no signup
          </a>
          <a href="https://docs.sgraal.com" className="px-8 py-4 text-lg font-bold rounded-md transition-colors"
            style={{ color: '#1a1c1a' }}>
            Read the docs
          </a>
        </div>
        <div className="flex flex-wrap justify-center gap-x-8 gap-y-2 text-sm uppercase tracking-widest"
          style={{ color: 'rgba(94,94,94,0.6)' }}>
          <span><span style={{ color: '#c9a962' }}>1,834</span> tests</span>
          <span><span style={{ color: '#c9a962' }}>0</span> failures</span>
          <span>production ready</span>
        </div>
      </div>
    </section>
  );
}
