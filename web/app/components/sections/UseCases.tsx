export function UseCases() {
  return (
    <section className="px-6 py-16 max-w-5xl mx-auto">
      <h2 className="text-3xl sm:text-4xl font-bold text-center mb-14">
        Who uses <span className="text-gold">Sgraal</span>
      </h2>
      <div className="grid md:grid-cols-3 gap-6">
        <div className="border border-surface-light border-t-2 border-t-gold bg-surface rounded-xl p-8">
          <p className="font-mono text-gold text-sm font-semibold mb-4">Building an AI agent?</p>
          <p className="text-foreground/90 text-sm mb-4">
            pip install sgraal. One preflight call. Know before you act.
          </p>
          <div className="overflow-x-auto">
            <pre className="bg-background border border-surface-light rounded-lg p-3 text-xs font-mono text-foreground/80 whitespace-pre">{`from sgraal import SgraalClient
result = client.preflight(memory)
if result.action == "BLOCK": stop()`}</pre>
          </div>
        </div>

        <div className="border border-surface-light border-t-2 border-t-gold bg-surface rounded-xl p-8">
          <p className="font-mono text-gold text-sm font-semibold mb-4">Need compliance documentation?</p>
          <p className="text-foreground/90 text-sm mb-4">
            EU AI Act Article 12. HIPAA &sect;164.312. MiFID2. Full audit trail. Compliance in one API.
          </p>
          <div className="overflow-x-auto">
            <pre className="bg-background border border-surface-light rounded-lg p-3 text-xs font-mono text-foreground/80 whitespace-pre">{`"compliance_profile": "EU_AI_ACT"
// Article 12 logging automatic
// Article 13 transparency built in`}</pre>
          </div>
        </div>

        <div className="border border-surface-light border-t-2 border-t-gold bg-surface rounded-xl p-8">
          <p className="font-mono text-gold text-sm font-semibold mb-4">Agent made a wrong decision?</p>
          <p className="text-foreground/90 text-sm">
            Your agent stopped itself before sending a wrong payment. Logged. Explainable. Auditable. No human had to intervene.
          </p>
        </div>
      </div>
    </section>
  );
}
