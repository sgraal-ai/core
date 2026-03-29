export const metadata = { title: "PROTECT — Sgraal", description: "Memory poisoning, prompt injection, hallucination risk, tamper detection — stopped before they reach your agent." };

const capabilities = [
  { title: "Security Signals", description: "poisoning_suspected: true — 3-signal combination. hallucination_risk: high — cyclic contradiction in memory graph. Circuit breaker: 5× omega > 80 → HTTP 429 Safety Block." },
  { title: "Write-time Protection", description: "Write firewall: blocks poisoned data before storage — prevention not detection. Sleeper detector: proactive scan for dormant trigger conditions." },
  { title: "Legal & Cryptographic Layer", description: "Memory Forensics: full incident trace. Black Box Recorder: tamper-evident capsule for every BLOCK. ZK Validation: omega score computed without content leaving your system." },
  { title: "Testing & Visualization", description: "Red Team as a Service: 6 attack types. Memory Readiness Grade: A/B/C/D/F. Immunity Certificate: 10,000 synthetic attacks → immunity_score." },
];

const howSteps = [
  ["Every write is validated before storage", "The write firewall intercepts incoming memory. Sleeper patterns, injection signatures, and source anomalies are flagged immediately."],
  ["Every read is scanned for threats", "Poisoning detection, hallucination risk, tamper verification (Merkle hash), and circuit breaker on repeated high-risk patterns."],
  ["Every incident is recorded and provable", "forensics_id, black box capsule (SHA256), ZK validation — every threat is traceable, every decision is defensible."],
];

const S = {
  label: { fontFamily: "'Inter', sans-serif" as const, color: "var(--primary-container)", letterSpacing: "0.1em" } as const,
  h1: { fontFamily: "'Manrope', sans-serif" as const, fontWeight: 800 as const, color: "var(--on-surface)" } as const,
  desc: { color: "var(--on-surface-variant)" } as const,
  h2: { fontFamily: "'Manrope', sans-serif" as const, fontWeight: 700 as const, color: "var(--on-surface)" } as const,
  stepTitle: { fontWeight: 600 as const, color: "var(--on-surface)" } as const,
  card: { backgroundColor: "var(--surface-container-lowest)", boxShadow: "0 2px 12px rgba(11,15,20,0.06)" } as const,
  cardTitle: { fontFamily: "'Manrope', sans-serif" as const, fontWeight: 700 as const, color: "var(--primary-container)" } as const,
  code: { backgroundColor: "var(--obsidian)" } as const,
  codeText: { fontFamily: "'JetBrains Mono', monospace" as const, color: "#e2e8f0" } as const,
  cta: { background: "linear-gradient(135deg, #745b1c, #c9a962)", color: "#533d00", fontWeight: 600 as const } as const,
  step: { backgroundColor: "var(--primary-container)", color: "var(--on-primary-container)", fontFamily: "'Manrope', sans-serif" as const, fontWeight: 700 as const } as const,
};

export default function ProtectPage() {
  return (
    <div className="max-w-4xl mx-auto py-16 px-6">
      <p className="text-xs uppercase tracking-widest mb-3" style={S.label}>PROTECT</p>
      <h1 className="text-4xl sm:text-5xl mb-4" style={S.h1}>Stop threats before they act.</h1>
      <p className="text-lg mb-12" style={S.desc}>Memory poisoning, prompt injection, hallucination risk, tamper detection — stopped before they reach your agent.</p>
      <div className="py-10 px-6 -mx-6 mb-14 rounded-lg" style={{ backgroundColor: "var(--surface-container-low)" }}>
        <h2 className="text-xl mb-6" style={S.h2}>How it works</h2>
        <div className="space-y-6">
          {howSteps.map(([title, desc], i) => (
            <div key={i} className="flex gap-4">
              <span className="w-7 h-7 rounded-full flex items-center justify-center text-xs shrink-0 mt-0.5" style={S.step}>{i + 1}</span>
              <div><p className="mb-1" style={S.stepTitle}>{title}</p><p className="text-sm" style={S.desc}>{desc}</p></div>
            </div>
          ))}
        </div>
      </div>
      <h2 className="text-xl mb-6" style={S.h2}>Capabilities</h2>
      <div className="space-y-4 mb-14">
        {capabilities.map((c) => (
          <div key={c.title} className="rounded-lg p-6" style={S.card}>
            <p className="mb-2" style={S.cardTitle}>{c.title}</p>
            <p className="text-sm leading-relaxed" style={S.desc}>{c.description}</p>
          </div>
        ))}
      </div>
      <div className="rounded-lg p-6 mb-14" style={S.code}>
        <p className="text-xs mb-3" style={{ color: "rgba(255,255,255,0.5)" }}>Integration</p>
        <pre className="text-sm overflow-x-auto leading-relaxed" style={S.codeText}>{`# Write firewall — block before storage
result = client.write_check(
    entry={"content": "...", "source": "external"},
    namespace="payments"
)
if result.firewall_blocked:
    print(result.block_reason)`}</pre>
      </div>
      <div className="text-center">
        <p className="text-xl mb-4" style={S.h2}>Ready to protect your agent&apos;s memory?</p>
        <a href="https://app.sgraal.com" className="px-8 py-3 rounded-md transition inline-block" style={S.cta}>Get API Key</a>
      </div>
    </div>
  );
}
