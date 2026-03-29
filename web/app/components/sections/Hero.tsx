export function Hero() {
  return (
    <section className="px-6 pt-16 pb-12 max-w-5xl mx-auto text-center">
      <span className="inline-block mb-4 px-3 py-1 text-xs uppercase tracking-widest rounded-full"
        style={{ backgroundColor: "var(--surface-container-low)", color: "var(--on-surface-variant)", fontFamily: "'Inter', sans-serif", letterSpacing: "0.1em" }}>
        Memory Governance Protocol
      </span>
      <h1 className="mb-6 max-w-4xl mx-auto" style={{ fontFamily: "'Manrope', sans-serif", fontWeight: 800, fontSize: "clamp(2.5rem, 5vw, 3.5rem)", letterSpacing: "-0.02em", color: "var(--on-surface)" }}>
        AI agents act on memory. Sgraal decides if that memory is{" "}
        <span style={{ color: "var(--primary-container)" }}>safe to act on.</span>
      </h1>
      <p className="mb-8 max-w-xl mx-auto" style={{ fontFamily: "'Inter', sans-serif", color: "var(--on-surface-variant)", fontSize: "1.125rem" }}>
        The memory governance protocol between AI agent memory and AI agent action.
      </p>
      <div className="flex flex-wrap justify-center gap-4">
        <a href="/playground" className="px-8 py-3 rounded-md transition text-base"
          style={{ background: "linear-gradient(135deg, #745b1c, #c9a962)", color: "#533d00", fontWeight: 600 }}>
          Try it now — no signup
        </a>
        <a href="https://docs.sgraal.com" className="px-8 py-3 rounded-md transition text-base"
          style={{ color: "var(--on-surface)" }}>
          Read the docs
        </a>
      </div>
      <p className="mt-6 text-sm" style={{ color: "var(--on-surface-variant)" }}>
        1,834 tests · 0 failures · production ready
      </p>
    </section>
  );
}
