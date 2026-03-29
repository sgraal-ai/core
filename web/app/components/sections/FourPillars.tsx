const pillars = [
  {
    title: "DECIDE", subtitle: "What the agent should do.",
    capabilities: ["Risk decision (USE_MEMORY / WARN / ASK_USER / BLOCK)", "Full explanation (Entry Shapley · causal graph)", "Repair plan (heal · closed loop · MTTR)", "Time machine (counterfactual · decision twin)", "AI advertising integrity (commercial intent · sponsorship detection)"],
    href: "/decide",
  },
  {
    title: "PROTECT", subtitle: "Stop threats before they act.",
    capabilities: ["Security signals (poisoning · hallucination · tamper · circuit breaker)", "Write-time protection (write firewall · sleeper detection)", "Legal & cryptographic layer (forensics · black box · ZK validation)", "Testing & visualization (red team · immunity certificate · dashboard)"],
    href: "/protect",
  },
  {
    title: "COMPLY", subtitle: "Meet every regulation. Prove it.",
    capabilities: ["Compliance engine (EU AI Act · HIPAA · MiFID2 · Basel4 · FDA · GDPR)", "Portability (memory passport · cross-LLM · memory DNS)", "Multi-agent coordination (ATC · court · commons)", "Testing & audit trail (immunity certificate · synthetic lab)"],
    href: "/comply",
  },
  {
    title: "SCALE", subtitle: "Learn, adapt, and grow autonomously.",
    capabilities: ["Learning (RL optimization · meta-learning · calibrated thresholds)", "Integrations (6 SDKs · 14 frameworks · MCP · CLI)", "Autonomous intelligence (predictive health · autonomous heal · rollback · pruning)"],
    href: "/scale",
  },
];

export function FourPillars() {
  return (
    <section style={{ backgroundColor: '#f4f3f0' }}>
      <div className="max-w-7xl mx-auto px-8 md:px-16 py-24">
        <h2 className="font-headline text-3xl md:text-4xl font-bold tracking-tight text-center mb-4" style={{ color: '#1a1c1a' }}>
          One API. 15 capabilities. <span style={{ color: '#c9a962' }}>Four pillars</span> of memory governance.
        </h2>
        <p className="text-center max-w-2xl mx-auto mb-16" style={{ color: '#5e5e5e' }}>
          Before every agent action, Sgraal decides, protects, complies, and scales.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
          {pillars.map((p) => (
            <a key={p.title} href={p.href}
              className="p-8 rounded-xl hover:-translate-y-1 transition-transform flex flex-col group"
              style={{ backgroundColor: '#ffffff', boxShadow: '0 4px 24px rgba(11,15,20,0.08)', border: '1px solid rgba(208,197,180,0.2)' }}>
              <p className="font-bold tracking-widest text-xs mb-4 block" style={{ color: '#c9a962' }}>{p.title}</p>
              <p className="font-headline text-lg font-bold mb-4" style={{ color: '#1a1c1a' }}>{p.subtitle}</p>
              <ul className="text-sm leading-relaxed space-y-3 mb-8 flex-1" style={{ color: '#5e5e5e' }}>
                {p.capabilities.map((c) => <li key={c}>· {c}</li>)}
              </ul>
              <span className="font-semibold text-sm mt-6 block" style={{ color: '#745b1c' }}>Explore {p.title} →</span>
            </a>
          ))}
        </div>
      </div>
    </section>
  );
}
