export function Hero() {
  return (
    <section className="relative overflow-hidden px-8 md:px-16 py-32 lg:py-48 flex flex-col items-center text-center max-w-[1440px] mx-auto">
      <div className="inline-flex items-center gap-2 px-4 py-1 rounded-full bg-surface-container-high border border-outline-variant/20 text-[10px] uppercase tracking-[0.2em] font-bold text-secondary mb-12">
        <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
        MEMORY GOVERNANCE PROTOCOL
      </div>
      <h1 className="font-headline text-5xl md:text-7xl lg:text-8xl font-extrabold tracking-tighter text-on-background max-w-5xl leading-[1.05] mb-8 text-balance">
        AI agents act on memory. Sgraal decides if that memory is{" "}
        <span className="text-primary-container">safe to act on.</span>
      </h1>
      <p className="text-xl md:text-2xl text-secondary max-w-2xl mb-12 font-light leading-relaxed">
        The memory governance protocol between AI agent memory and AI agent action.
      </p>
      <div className="flex flex-col sm:flex-row items-center gap-6 mb-20">
        <a className="gold-gradient-bg px-8 py-4 text-lg font-bold text-white rounded-md shadow-lg shadow-primary/10 hover:shadow-primary/20 transition-all" href="/playground">
          Try it now — no signup
        </a>
        <a className="px-8 py-4 text-lg font-bold text-on-surface hover:bg-surface-container-high rounded-md transition-all" href="https://docs.sgraal.com">
          Read the docs
        </a>
      </div>
      <div className="flex flex-wrap justify-center gap-x-12 gap-y-4 text-sm font-label uppercase tracking-widest text-secondary/60">
        <span className="flex items-center gap-2"><span className="text-primary-container">1,834</span> tests</span>
        <span className="flex items-center gap-2"><span className="text-primary-container">0</span> failures</span>
        <span className="flex items-center gap-2">production ready</span>
      </div>
      <div className="absolute -z-10 top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-6xl aspect-square opacity-[0.03] pointer-events-none">
        <div className="w-full h-full border-[60px] border-primary-container rounded-full blur-3xl" />
      </div>
    </section>
  );
}
