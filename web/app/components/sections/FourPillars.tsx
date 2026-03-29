const pillars = [
  {
    label: "DECIDE", title: "What the agent should do.",
    items: ["Risk decision (USE_MEMORY / WARN / ASK_USER / BLOCK)", "Full explanation (Entry Shapley · causal graph)", "Repair plan (heal · closed loop · MTTR)", "Time machine (counterfactual · decision twin)", "AI advertising integrity (commercial intent · sponsorship detection)"],
    href: "/decide",
  },
  {
    label: "PROTECT", title: "Stop threats before they act.",
    items: ["Security signals (poisoning · hallucination · tamper · circuit breaker)", "Write-time protection (write firewall · sleeper detection)", "Legal & cryptographic layer (forensics · black box · ZK validation)", "Testing & visualization (red team · immunity certificate · dashboard)"],
    href: "/protect",
  },
  {
    label: "COMPLY", title: "Meet every regulation. Prove it.",
    items: ["Compliance engine (EU AI Act · HIPAA · MiFID2 · Basel4 · FDA · GDPR)", "Portability (memory passport · cross-LLM · memory DNS)", "Multi-agent coordination (ATC · court · commons)", "Testing & audit trail (immunity certificate · synthetic lab)"],
    href: "/comply",
  },
  {
    label: "SCALE", title: "Learn, adapt, and grow autonomously.",
    items: ["Learning (RL optimization · meta-learning · calibrated thresholds)", "Integrations (6 SDKs · 14 frameworks · MCP · CLI)", "Autonomous intelligence (predictive health · autonomous heal · rollback · pruning)"],
    href: "/scale",
  },
];

export function FourPillars() {
  return (
    <section className="bg-surface-container-low px-8 md:px-16 py-32 lg:py-48">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-24 space-y-4">
          <h2 className="font-headline text-4xl md:text-5xl font-bold tracking-tight">
            One API. 15 capabilities. <span className="text-primary-container">Four pillars</span> of memory governance.
          </h2>
          <p className="text-xl text-secondary">Before every agent action, Sgraal decides, protects, complies, and scales.</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
          {pillars.map((p) => (
            <div key={p.label} className="bg-surface-container-lowest p-8 rounded-xl shadow-[0_12px_40px_rgba(11,15,20,0.04)] border border-outline-variant/10 group hover:-translate-y-1 transition-transform">
              <div className="text-primary-container mb-6 font-bold tracking-widest text-xs">{p.label}</div>
              <h4 className="font-headline text-xl font-bold mb-4">{p.title}</h4>
              <ul className="text-sm text-secondary space-y-3 mb-8">
                {p.items.map((item) => (
                  <li key={item} className="flex items-start gap-2">
                    <span className="text-primary text-sm mt-0.5">✓</span> {item}
                  </li>
                ))}
              </ul>
              <a className="text-primary font-semibold text-sm inline-flex items-center gap-1" href={p.href}>
                Explore {p.label} →
              </a>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
