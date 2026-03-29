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

export default function ProtectPage() {
  return (
    <div style={{ backgroundColor: "#faf9f6" }}>
      <div className="max-w-7xl mx-auto px-8 md:px-16 py-20">
        <p className="text-primary-container font-bold tracking-widest text-xs uppercase mb-4">PROTECT</p>
        <h1 className="font-headline text-4xl md:text-5xl font-extrabold tracking-tighter text-on-background mb-4">Stop threats before they act.</h1>
        <p className="text-secondary text-lg mb-16">Memory poisoning, prompt injection, hallucination risk, tamper detection — stopped before they reach your agent.</p>
      </div>
      <div className="bg-surface-container-low px-8 py-20">
        <div className="max-w-4xl mx-auto">
          <h2 className="font-headline text-2xl font-bold text-on-background mb-10">How it works</h2>
          <div className="space-y-8">
            {howSteps.map(([title, desc], i) => (
              <div key={i} className="flex gap-5">
                <span className="w-14 h-14 rounded-full border-2 border-primary-container bg-surface-container-low flex items-center justify-center text-2xl font-bold text-primary shrink-0">{i + 1}</span>
                <div><p className="font-headline font-bold text-on-surface mb-1">{title}</p><p className="text-secondary text-sm">{desc}</p></div>
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="max-w-7xl mx-auto px-8 md:px-16 py-20">
        <h2 className="font-headline text-2xl font-bold text-on-background mb-10">Capabilities</h2>
        <div className="space-y-6">
          {capabilities.map((c) => (
            <div key={c.title} className="p-8 rounded-xl flex flex-col" style={{ backgroundColor: "#ffffff", boxShadow: "0 4px 24px rgba(11,15,20,0.08)", border: "1px solid rgba(208,197,180,0.2)" }}>
              <p className="text-primary-container font-bold font-headline mb-2">{c.title}</p>
              <p className="text-secondary text-sm leading-relaxed">{c.description}</p>
            </div>
          ))}
        </div>
      </div>
      <div className="max-w-7xl mx-auto px-8 md:px-16 pb-8">
        <div className="bg-[#0b0f14] rounded-xl p-8">
          <p className="text-[#6b6b6b] text-xs mb-4">Integration</p>
          <pre className="text-sm overflow-x-auto leading-relaxed text-[#e2e8f0]">{`# Write firewall — block before storage
result = client.write_check(
    entry={"content": "...", "source": "external"},
    namespace="payments"
)
if result.firewall_blocked:
    print(result.block_reason)`}</pre>
        </div>
      </div>
      <div className="px-8 md:px-16 py-20 text-center" style={{ backgroundColor: "#f4f3f0" }}>
        <p className="font-headline text-2xl font-bold text-on-background mb-6">Ready to protect your agent&apos;s memory?</p>
        <a href="https://app.sgraal.com" className="gold-gradient-bg px-8 py-4 text-lg font-bold text-white rounded-md inline-block">Get API Key</a>
      </div>
    </div>
  );
}
