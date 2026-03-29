const pillars = [
  {
    icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" width="28" height="28"><path d="M12 2a7 7 0 0 1 7 7c0 2.5-1.5 4.5-3 6l-1 2H9l-1-2c-1.5-1.5-3-3.5-3-6a7 7 0 0 1 7-7z"/><path d="M9 21h6"/></svg>,
    title: "DECIDE",
    subtitle: "What the agent should do.",
    capabilities: [
      "Risk decision (USE_MEMORY / WARN / ASK_USER / BLOCK)",
      "Full explanation (Entry Shapley · causal graph)",
      "Repair plan (heal · closed loop · MTTR)",
      "Time machine (counterfactual · decision twin)",
      "AI advertising integrity (commercial intent · sponsorship detection)",
    ],
    href: "/decide",
  },
  {
    icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" width="28" height="28"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>,
    title: "PROTECT",
    subtitle: "Stop threats before they act.",
    capabilities: [
      "Security signals (poisoning · hallucination · tamper · circuit breaker)",
      "Write-time protection (write firewall · sleeper detection)",
      "Legal & cryptographic layer (forensics · black box · ZK validation)",
      "Testing & visualization (red team · immunity certificate · dashboard)",
    ],
    href: "/protect",
  },
  {
    icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" width="28" height="28"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M9 15l2 2 4-4"/></svg>,
    title: "COMPLY",
    subtitle: "Meet every regulation. Prove it.",
    capabilities: [
      "Compliance engine (EU AI Act · HIPAA · MiFID2 · Basel4 · FDA · GDPR)",
      "Portability (memory passport · cross-LLM · memory DNS)",
      "Multi-agent coordination (ATC · court · commons)",
      "Testing & audit trail (immunity certificate · synthetic lab)",
    ],
    href: "/comply",
  },
  {
    icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" width="28" height="28"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>,
    title: "SCALE",
    subtitle: "Learn, adapt, and grow autonomously.",
    capabilities: [
      "Learning (RL optimization · meta-learning · calibrated thresholds)",
      "Integrations (6 SDKs · 14 frameworks · MCP · CLI)",
      "Autonomous intelligence (predictive health · autonomous heal · rollback · pruning)",
    ],
    href: "/scale",
  },
];

export function FourPillars() {
  return (
    <section className="px-6 py-14 max-w-6xl mx-auto">
      <h2 className="text-3xl sm:text-4xl font-bold text-center mb-3">
        One API. 15 capabilities. <span className="text-gold">Four pillars</span> of memory governance.
      </h2>
      <p className="text-muted text-center max-w-2xl mx-auto mb-14">
        Before every agent action, Sgraal decides, protects, complies, and scales.
      </p>
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {pillars.map((p) => (
          <a key={p.title} href={p.href}
            className="border border-surface-light bg-surface rounded-xl p-6 hover:border-gold/50 transition group flex flex-col">
            <div className="text-gold mb-3">{p.icon}</div>
            <p className="font-mono text-gold text-sm font-bold tracking-wider mb-1">{p.title}</p>
            <p className="text-foreground text-sm font-medium mb-4">{p.subtitle}</p>
            <ul className="text-muted text-xs space-y-1.5 flex-1 mb-4">
              {p.capabilities.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
            <span className="text-gold text-xs font-semibold group-hover:underline">
              Explore {p.title} &rarr;
            </span>
          </a>
        ))}
      </div>
    </section>
  );
}
