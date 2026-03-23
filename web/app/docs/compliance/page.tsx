import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Compliance Engine — Sgraal",
  description: "EU AI Act, FDA 510K, and HIPAA compliance profiles for AI agent memory governance.",
};

export default function CompliancePage() {
  return (
    <main className="flex-1 max-w-3xl mx-auto px-6 py-24">
      <h1 className="text-3xl font-bold mb-2">Compliance Engine</h1>
      <p className="text-muted text-sm mb-10">
        Regulatory compliance profiles for the Sgraal preflight API
      </p>

      <div className="space-y-10 text-foreground/80 leading-relaxed">
        <section>
          <h2 className="text-xl font-semibold text-foreground mb-3">How to use</h2>
          <p className="mb-4">
            Add the <code className="text-gold font-mono text-sm">compliance_profile</code> field
            to your <code className="text-gold font-mono text-sm">POST /v1/preflight</code> request:
          </p>
          <pre className="bg-surface border border-surface-light rounded-xl p-5 text-sm overflow-x-auto font-mono text-foreground/80 mb-4">{`{
  "memory_state": [...],
  "action_type": "irreversible",
  "domain": "fintech",
  "compliance_profile": "EU_AI_ACT"
}`}</pre>
          <p>
            The response includes a <code className="text-gold font-mono text-sm">compliance_result</code> object
            with <code className="font-mono text-sm">compliant</code>, <code className="font-mono text-sm">violations</code>,
            <code className="font-mono text-sm">audit_required</code>, and <code className="font-mono text-sm">profile_applied</code>.
            Critical violations automatically override <code className="font-mono text-sm">recommended_action</code> to BLOCK.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-foreground mb-3">Profiles</h2>
          <p className="mb-4">
            Available values: <code className="font-mono text-sm text-gold">GENERAL</code> (default),{" "}
            <code className="font-mono text-sm text-gold">EU_AI_ACT</code>,{" "}
            <code className="font-mono text-sm text-gold">FDA_510K</code>,{" "}
            <code className="font-mono text-sm text-gold">HIPAA</code>.
          </p>
        </section>

        <section className="border border-surface-light bg-surface rounded-xl p-6">
          <h2 className="text-xl font-semibold text-foreground mb-4">EU AI Act</h2>

          <div className="space-y-4">
            <div>
              <h3 className="font-mono text-gold text-sm mb-1">Article 12 — Logging &amp; Irreversible Actions</h3>
              <p className="text-sm">
                When <code className="font-mono">omega_mem_final &gt; 60</code> AND{" "}
                <code className="font-mono">action_type == &quot;irreversible&quot;</code>: non-compliant.
                Audit trail required. Recommended action overridden to BLOCK.
              </p>
            </div>

            <div>
              <h3 className="font-mono text-gold text-sm mb-1">Article 9 — Risk Management (Medical)</h3>
              <p className="text-sm">
                When <code className="font-mono">domain == &quot;medical&quot;</code> AND{" "}
                <code className="font-mono">omega_mem_final &gt; 40</code>: human oversight required.
                Audit required.
              </p>
            </div>

            <div>
              <h3 className="font-mono text-gold text-sm mb-1">Article 13 — Transparency</h3>
              <p className="text-sm">
                Always enforced. Every response includes <code className="font-mono">explainability_note</code> with
                the highest-risk component and recommended action. No additional action needed.
              </p>
            </div>
          </div>
        </section>

        <section className="border border-surface-light bg-surface rounded-xl p-6">
          <h2 className="text-xl font-semibold text-foreground mb-4">FDA 510(k)</h2>

          <div className="space-y-4">
            <div>
              <h3 className="font-mono text-gold text-sm mb-1">Predicate Device Comparison</h3>
              <p className="text-sm">
                When <code className="font-mono">domain == &quot;medical&quot;</code> AND{" "}
                <code className="font-mono">omega_mem_final &gt; 30</code>: non-compliant.
                Requires predicate device comparison. Audit required.
              </p>
            </div>

            <div>
              <h3 className="font-mono text-gold text-sm mb-1">Risk Classification</h3>
              <p className="text-sm">
                When <code className="font-mono">action_type</code> is <code className="font-mono">irreversible</code> or{" "}
                <code className="font-mono">destructive</code> AND <code className="font-mono">omega_mem_final &gt; 50</code>:
                Class III review required. Audit required.
              </p>
            </div>
          </div>
        </section>

        <section className="border border-surface-light bg-surface rounded-xl p-6">
          <h2 className="text-xl font-semibold text-foreground mb-4">HIPAA</h2>

          <div>
            <h3 className="font-mono text-gold text-sm mb-1">PHI Integrity — &sect;164.312</h3>
            <p className="text-sm">
              When <code className="font-mono">domain == &quot;medical&quot;</code> AND{" "}
              <code className="font-mono">assurance_score &lt; 70</code>: non-compliant.
              Protected Health Information integrity cannot be guaranteed. Audit required.
            </p>
          </div>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-foreground mb-3">Healing Policy Matrix</h2>
          <p className="mb-4">
            The compliance profile also affects the healing tier and approval requirements
            for repair actions:
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-light text-left text-muted">
                  <th className="py-2 pr-4">Memory Type</th>
                  <th className="py-2 pr-4">Domain</th>
                  <th className="py-2 pr-4">Profile</th>
                  <th className="py-2 pr-4">Tier</th>
                  <th className="py-2">Approval</th>
                </tr>
              </thead>
              <tbody className="font-mono text-xs">
                <tr className="border-b border-surface-light/50">
                  <td className="py-2 pr-4">tool_state</td><td className="pr-4">medical</td>
                  <td className="pr-4 text-gold">FDA_510K</td><td className="pr-4">3</td><td>Required</td>
                </tr>
                <tr className="border-b border-surface-light/50">
                  <td className="py-2 pr-4">tool_state</td><td className="pr-4">fintech</td>
                  <td className="pr-4 text-gold">EU_AI_ACT</td><td className="pr-4">2</td><td>Required</td>
                </tr>
                <tr className="border-b border-surface-light/50">
                  <td className="py-2 pr-4">semantic</td><td className="pr-4">fintech</td>
                  <td className="pr-4 text-gold">EU_AI_ACT</td><td className="pr-4">2</td><td>No</td>
                </tr>
                <tr className="border-b border-surface-light/50">
                  <td className="py-2 pr-4">tool_state</td><td className="pr-4">general</td>
                  <td className="pr-4 text-gold">GENERAL</td><td className="pr-4">1</td><td>No</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="text-xs text-muted mt-3">Tier 1 = auto-heal, Tier 2 = suggest, Tier 3 = log-only</p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-foreground mb-3">Contact</h2>
          <p>
            For compliance questions, contact us at{" "}
            <a href="mailto:hello@sgraal.com" className="text-gold hover:underline">hello@sgraal.com</a>.
          </p>
        </section>
      </div>
    </main>
  );
}
