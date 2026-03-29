export function UseCases() {
  return (
    <section className="px-6 py-16 max-w-5xl mx-auto">
      <h2 className="text-3xl sm:text-4xl font-bold text-center mb-14">
        Who uses <span className="text-gold">Sgraal</span>
      </h2>
      <div className="grid md:grid-cols-3 gap-6">
        <div className="border border-surface-light border-t-2 border-t-gold bg-surface rounded-xl p-8">
          <p className="font-mono text-gold text-sm font-semibold mb-4">Building an AI agent?</p>
          <p className="text-foreground/90 text-sm">
            Know if your agent&apos;s memory is safe to act on. Before it acts.
          </p>
        </div>

        <div className="border border-surface-light border-t-2 border-t-gold bg-surface rounded-xl p-8">
          <p className="font-mono text-gold text-sm font-semibold mb-4">Need compliance documentation?</p>
          <p className="text-foreground/90 text-sm">
            EU AI Act. HIPAA. MiFID2. Every decision logged, traced, and provable.
          </p>
        </div>

        <div className="border border-surface-light border-t-2 border-t-gold bg-surface rounded-xl p-8">
          <p className="font-mono text-gold text-sm font-semibold mb-4">Agent made a wrong decision?</p>
          <p className="text-foreground/90 text-sm">
            Your agent stopped itself. Logged. Explainable. No human had to intervene.
          </p>
        </div>
      </div>
    </section>
  );
}
