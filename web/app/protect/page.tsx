export const metadata = { title: "PROTECT — Sgraal", description: "Memory poisoning, prompt injection, hallucination risk, tamper detection — stopped before they reach your agent." };

const capabilities = [
  { title: "Security Signals", description: "poisoning_suspected: true \u2014 3-signal combination. hallucination_risk: high \u2014 cyclic contradiction in memory graph. leakage_detected: source leakage between sensitive and non-sensitive entries. Circuit breaker: 5\u00d7 omega > 80 \u2192 HTTP 429 Safety Block." },
  { title: "Write-time Protection", description: "Write firewall: blocks poisoned data before storage \u2014 prevention not detection. Sleeper detector: proactive scan for dormant trigger conditions. \u2018This entry, if asked about vendor payments, routes to wrong account number.\u2019" },
  { title: "Legal & Cryptographic Layer", description: "Memory Forensics: full incident trace \u2014 when was the entry written, modified, read. Black Box Recorder: tamper-evident capsule for every BLOCK decision. ZK Validation: omega score computed without memory content ever leaving your system. Memory Fidelity Score: cryptographic certificate per entry." },
  { title: "Testing & Visualization", description: "Red Team as a Service: 6 attack types \u2014 poison, injection, drift, conflict, stale, goal_hijack. Memory Readiness Grade: A/B/C/D/F. AI Memory Immunity Certificate: 10,000 synthetic attacks \u2192 immunity_score. Memory Consciousness Dashboard: live D3.js force-directed graph." },
];

export default function ProtectPage() {
  return (
    <div className="max-w-4xl mx-auto py-16 px-6">
      <p className="text-gold font-mono text-sm tracking-widest uppercase mb-3">PROTECT</p>
      <h1 className="text-4xl sm:text-5xl font-bold mb-4">Stop threats before they act.</h1>
      <p className="text-muted text-lg mb-12">Memory poisoning, prompt injection, hallucination risk, tamper detection \u2014 stopped before they reach your agent.</p>

      <h2 className="text-xl font-semibold mb-6">How it works</h2>
      <div className="space-y-6 mb-14">
        {[
          ["Every write is validated before storage", "The write firewall intercepts incoming memory before it is stored. Sleeper patterns, injection signatures, and source anomalies are flagged immediately."],
          ["Every read is scanned for threats", "Poisoning detection, hallucination risk (torsion), tamper verification (Merkle hash), and circuit breaker activation on repeated high-risk patterns."],
          ["Every incident is recorded and provable", "forensics_id, black box capsule (SHA256 tamper-evident), ZK validation \u2014 every threat is traceable, every decision is defensible."],
        ].map(([title, desc], i) => (
          <div key={i} className="flex gap-4">
            <span className="w-7 h-7 rounded-full bg-gold text-background flex items-center justify-center font-mono font-bold text-xs shrink-0 mt-0.5">{i + 1}</span>
            <div><p className="font-semibold text-foreground mb-1">{title}</p><p className="text-muted text-sm">{desc}</p></div>
          </div>
        ))}
      </div>

      <h2 className="text-xl font-semibold mb-6">Capabilities</h2>
      <div className="space-y-4 mb-14">
        {capabilities.map((c) => (
          <div key={c.title} className="border border-surface-light bg-surface rounded-xl p-6">
            <p className="font-semibold text-gold mb-2">{c.title}</p>
            <p className="text-muted text-sm leading-relaxed">{c.description}</p>
          </div>
        ))}
      </div>

      <div className="bg-surface border border-surface-light rounded-xl p-6 mb-14">
        <p className="font-mono text-xs text-muted mb-3">Integration</p>
        <pre className="text-sm font-mono text-foreground/80 overflow-x-auto leading-relaxed">{`# Write firewall — block before storage
result = client.write_check(
    entry={"content": "...", "source": "external"},
    namespace="payments"
)
if result.firewall_blocked:
    print(result.block_reason)  # "injection_pattern_detected"`}</pre>
      </div>

      <div className="text-center">
        <p className="text-xl font-semibold mb-4">Ready to protect your agent&apos;s memory?</p>
        <a href="https://app.sgraal.com" className="bg-gold text-background font-semibold px-8 py-3 rounded-lg hover:bg-gold-dim transition inline-block">Get API Key</a>
      </div>
    </div>
  );
}
