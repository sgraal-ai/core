export function Hero() {
  return (
    <section className="relative overflow-hidden px-8 md:px-16 py-20 lg:py-28 flex flex-col items-center text-center">
      <div className="inline-flex items-center gap-2 px-4 py-1 rounded-full bg-surface-container-high border border-outline-variant/20 text-[10px] uppercase tracking-[0.2em] font-bold text-secondary mb-12">
        <span className="w-1.5 h-1.5 rounded-full bg-primary-container animate-pulse" />
        Memory Governance Protocol
      </div>
      <h1 className="font-headline text-4xl md:text-5xl lg:text-6xl font-extrabold tracking-tighter text-on-background max-w-5xl leading-[1.05] mb-6 text-balance">
        AI agents act on memory. Sgraal decides if that memory is{" "}
        <span className="text-primary-container">safe to act on.</span>
      </h1>
      <p className="text-xl md:text-2xl text-secondary max-w-2xl mb-8 font-light leading-relaxed">
        The memory governance protocol between AI agent memory and AI agent action.
      </p>
      <div className="flex flex-wrap justify-center gap-4 mb-16">
        <a href="/playground" className="gold-gradient-bg px-8 py-4 text-lg font-bold text-white rounded-md">
          Try it now — no signup
        </a>
        <a href="https://docs.sgraal.com" className="px-8 py-4 text-lg font-bold text-on-surface hover:bg-surface-container-high rounded-md transition-colors">
          Read the docs
        </a>
      </div>
      <div className="flex flex-wrap justify-center gap-x-12 text-sm uppercase tracking-widest text-secondary/60">
        <span><span className="text-primary-container">1,834</span> tests</span>
        <span><span className="text-primary-container">0</span> failures</span>
        <span>production ready</span>
      </div>
    </section>
  );
}
