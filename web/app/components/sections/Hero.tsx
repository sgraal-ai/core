export function Hero() {
  return (
    <section className="px-6 pt-16 pb-12 max-w-5xl mx-auto text-center">
      <p className="text-gold font-mono text-sm tracking-widest uppercase mb-3">
        Memory Governance Protocol
      </p>
      <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold leading-tight mb-6 max-w-4xl mx-auto">
        AI agents act on memory. Sgraal decides if that memory is{" "}
        <span className="text-gold">safe to act on.</span>
      </h1>
      <p className="text-muted text-lg sm:text-xl mb-8 max-w-2xl mx-auto">
        The memory governance protocol between AI agent memory and AI agent action.
      </p>
      <div className="flex flex-wrap justify-center gap-4">
        <a href="/playground" className="bg-gold text-background font-semibold px-8 py-3 rounded-lg hover:bg-gold-dim transition text-base">
          Try it now — no signup
        </a>
        <a href="https://docs.sgraal.com" className="border border-foreground/30 text-foreground font-semibold px-8 py-3 rounded-lg hover:bg-foreground/5 transition text-base">
          Read the docs
        </a>
      </div>
      <p className="text-sm text-muted mt-6">
        1,834 tests &middot; 0 failures &middot; production ready
      </p>
    </section>
  );
}
