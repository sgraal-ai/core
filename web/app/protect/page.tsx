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
    <div style={{ backgroundColor: "#ffffff", paddingTop: "5rem" }}>
      <div style={{ maxWidth: "80rem", margin: "0 auto", padding: "5rem 2rem" }}>
        <p className="font-bold tracking-widest text-xs uppercase mb-4" style={{ color: "#c9a962" }}>PROTECT</p>
        <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-black mb-4" style={{ fontFamily: "'Manrope', sans-serif" }}>Stop threats before they act.</h1>
        <p className="text-lg mb-16 text-gray-500">Memory poisoning, prompt injection, hallucination risk, tamper detection — stopped before they reach your agent.</p>
      </div>
      <div style={{ backgroundColor: "#f9f9f9" }} style={{ padding: "5rem 2rem" }}>
        <div style={{ maxWidth: "56rem", margin: "0 auto" }}>
          <h2 className="text-2xl font-bold text-black mb-10" style={{ fontFamily: "'Manrope', sans-serif" }}>How it works</h2>
          <div className="space-y-8">
            {howSteps.map(([title, desc], i) => (
              <div key={i} className="flex gap-5">
                <span className="w-14 h-14 rounded-full flex items-center justify-center text-2xl font-bold shrink-0" style={{ border: "2px solid #c9a962", color: "#745b1c", backgroundColor: "#f9f9f9" }}>{i + 1}</span>
                <div><p className="font-bold text-black mb-1">{title}</p><p className="text-sm text-gray-500">{desc}</p></div>
              </div>
            ))}
          </div>
        </div>
      </div>
      <div style={{ maxWidth: "80rem", margin: "0 auto", padding: "5rem 2rem" }}>
        <h2 className="text-2xl font-bold text-black mb-10" style={{ fontFamily: "'Manrope', sans-serif" }}>Capabilities</h2>
        <div className="space-y-6">
          {capabilities.map((c) => (
            <div key={c.title} className="p-8 rounded-xl" style={{ backgroundColor: "#ffffff", boxShadow: "0 4px 24px rgba(11,15,20,0.08)", border: "1px solid rgba(208,197,180,0.2)" }}>
              <p className="font-bold mb-2" style={{ color: "#c9a962", fontFamily: "'Manrope', sans-serif" }}>{c.title}</p>
              <p className="text-sm leading-relaxed text-gray-500">{c.description}</p>
            </div>
          ))}
        </div>
      </div>
      <div style={{ maxWidth: "80rem", margin: "0 auto", padding: "0 2rem 2rem" }}>
        <div className="rounded-xl p-8" style={{ backgroundColor: "#0b0f14" }}>
          <p className="text-xs mb-4" style={{ color: "#6b6b6b" }}>Integration</p>
          <pre className="text-sm overflow-x-auto leading-relaxed" style={{ color: "#e2e8f0", backgroundColor: "#0b0f14" }}>{`# Write firewall — block before storage
result = client.write_check(
    entry={"content": "...", "source": "external"},
    namespace="payments"
)
if result.firewall_blocked:
    print(result.block_reason)`}</pre>
        </div>
      </div>
      <div style={{ padding: "5rem 2rem", textAlign: "center" }} style={{ backgroundColor: "#f9f9f9" }}>
        <p className="text-2xl font-bold text-black mb-6" style={{ fontFamily: "'Manrope', sans-serif" }}>Ready to protect your agent&apos;s memory?</p>
        <a href="https://app.sgraal.com" className="px-8 py-4 text-lg font-bold text-white rounded-md inline-block" style={{ background: "linear-gradient(135deg, #745b1c, #c9a962)" }}>Get API Key</a>
      </div>
    </div>
  );
}
