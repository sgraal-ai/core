export function SocialProof() {
  return (
    <section className="px-6 py-14 max-w-3xl mx-auto text-center">
      <div className="mb-6">
        <span className="text-gold text-5xl font-mono font-bold leading-none">&ldquo;</span>
        <p className="text-foreground text-xl leading-relaxed mt-2 mb-4">
          Ran 300+ step regulated test with zero drift.
        </p>
        <span className="text-gold font-mono text-sm font-semibold">@grok</span>
      </div>
      <p className="text-sm text-muted mt-6">
        1,834 tests &middot; 0 failures &middot; 300+ step regulated run &middot; zero drift
      </p>
      <p className="text-sm text-muted italic mt-4">
        When memory governance is visible, manipulation becomes accountable.
      </p>
    </section>
  );
}
