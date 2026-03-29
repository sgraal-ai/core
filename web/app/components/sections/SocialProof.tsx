export function SocialProof() {
  return (
    <section className="px-6 py-14 max-w-3xl mx-auto text-center">
      <div className="mb-6">
        <span className="text-5xl leading-none" style={{ fontFamily: "'Manrope', sans-serif", color: "var(--primary-container)" }}>&ldquo;</span>
        <p className="text-xl leading-relaxed mt-2 mb-4" style={{ fontFamily: "'Manrope', sans-serif", fontWeight: 600, color: "var(--on-surface)" }}>
          Ran 300+ step regulated test with zero drift.
        </p>
        <span className="text-sm" style={{ fontFamily: "'Inter', sans-serif", color: "var(--primary-container)", fontWeight: 500 }}>@grok</span>
      </div>
      <p className="text-sm mt-6" style={{ color: "var(--on-surface-variant)" }}>
        1,834 tests · 0 failures · 300+ step regulated run · zero drift
      </p>
      <p className="text-sm italic mt-4" style={{ color: "var(--on-surface-variant)" }}>
        When memory governance is visible, manipulation becomes accountable.
      </p>
    </section>
  );
}
