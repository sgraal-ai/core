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
    <section className="bg-surface-container-low px-8 md:px-16 py-24 lg:py-32">
      <div className="max-w-7xl mx-auto">
        <h2 className="font-headline text-3xl md:text-4xl font-bold tracking-tight text-center text-on-background mb-4">
          One API. 15 capabilities. <span className="text-primary-container">Four pillars</span> of memory governance.
        </h2>
        <p className="text-center text-secondary max-w-2xl mx-auto mb-24">
          Before every agent action, Sgraal decides, protects, complies, and scales.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
          {pillars.map((p) => (
            <a key={p.title} href={p.href}
              className="bg-surface-container-lowest p-8 rounded-xl shadow-[0_12px_40px_rgba(11,15,20,0.04)] border border-outline-variant/10 group hover:-translate-y-1 transition-transform flex flex-col">
              <p className="text-primary-container font-bold tracking-widest text-xs mb-4 block">{p.title}</p>
              <p className="font-headline text-lg font-bold text-on-surface mb-4">{p.subtitle}</p>
              <ul className="text-sm text-secondary leading-relaxed space-y-3 mb-8 flex-1">
                {p.capabilities.map((c) => <li key={c}>· {c}</li>)}
              </ul>
              <span className="text-primary font-semibold text-sm mt-6 block">Explore {p.title} →</span>
            </a>
          ))}
        </div>
      </div>
    </section>
  );
}
