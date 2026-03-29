"use client";

const pillars = [
  {
    label: "DECIDE",
    title: "Conflict Resolution",
    items: ["Temporal decay weighting", "Multi-source consensus", "Uncertainty flagging"],
    href: "/decide",
  },
  {
    label: "PROTECT",
    title: "Poison Detection",
    items: ["Injection filtering", "Bias triangulation", "Adversarial buffer"],
    href: "/protect",
  },
  {
    label: "COMPLY",
    title: "Policy Guardrails",
    items: ["PII isolation", "Regional siloing", "Audit trail exports"],
    href: "/comply",
  },
  {
    label: "SCALE",
    title: "High Availability",
    items: ["< 10ms latency", "Edge deployment", "Global sync"],
    href: "/scale",
  },
];

const badges = ["LangChain", "CrewAI", "AutoGen", "LlamaIndex", "mem0", "MCP", "OpenAI", "Anthropic"];

const stats = [
  { value: "1,834", label: "Tests" },
  { value: "0", label: "Failures" },
  { value: "300+", label: "Steps" },
  { value: "Zero", label: "Drift" },
];

export default function Home() {
  return (
    <>
      {/* HERO */}

        <section className="relative overflow-hidden px-8 md:px-16 py-32 lg:py-48 flex flex-col items-center text-center max-w-[1440px] mx-auto">
          <div className="inline-flex items-center gap-2 px-4 py-1 rounded-full bg-surface-container-high border border-outline-variant/20 text-[10px] uppercase tracking-[0.2em] font-bold text-secondary mb-12">
            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
            MEMORY GOVERNANCE PROTOCOL
          </div>
          <h1 className="font-headline text-5xl md:text-7xl lg:text-8xl font-extrabold tracking-tighter text-on-background max-w-5xl leading-[1.05] mb-8 text-balance">
            AI agents act on memory. Sgraal decides if that memory is{" "}
            <span className="text-primary-container">safe to act on.</span>
          </h1>
          <p className="text-xl md:text-2xl text-secondary max-w-2xl mb-12 font-light leading-relaxed">
            The memory governance protocol between AI agent memory and AI agent action.
          </p>
          <div className="flex flex-col sm:flex-row items-center gap-6 mb-20">
            <a
              className="gold-gradient-bg px-8 py-4 text-lg font-bold text-white rounded-md shadow-lg shadow-primary/10 hover:shadow-primary/20 transition-all"
              href="/playground"
            >
              Try it now — no signup
            </a>
            <a
              className="px-8 py-4 text-lg font-bold text-on-surface hover:bg-surface-container-high rounded-md transition-all"
              href="https://docs.sgraal.com"
            >
              Read the docs
            </a>
          </div>
          <div className="flex flex-wrap justify-center gap-x-12 gap-y-4 text-sm font-label uppercase tracking-widest text-secondary/60">
            <span className="flex items-center gap-2">
              <span className="text-primary-container">1,834</span> tests
            </span>
            <span className="flex items-center gap-2">
              <span className="text-primary-container">0</span> failures
            </span>
            <span className="flex items-center gap-2">production ready</span>
          </div>
          <div className="absolute -z-10 top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-6xl aspect-square opacity-[0.03] pointer-events-none">
            <div className="w-full h-full border-[60px] border-primary-container rounded-full blur-3xl" />
          </div>
        </section>

        {/* PROBLEM */}
        <section className="bg-surface-container-low px-8 md:px-16 py-32 lg:py-40">
          <div className="max-w-7xl mx-auto flex flex-col lg:flex-row gap-20 items-start">
            <div className="lg:w-1/2">
              <h2 className="font-headline text-4xl md:text-5xl font-bold tracking-tight text-on-background mb-8 leading-tight text-balance">
                One wrong memory. <br />
                <span className="text-primary-container">One wrong decision.</span>
              </h2>
              <div className="space-y-8">
                <p className="text-lg md:text-xl leading-relaxed text-secondary/80">
                  Your AI agent is about to act. It has 47 memories to draw from. One of them is 54
                  days old, conflicts with two newer sources, and carries a commercial bias from a
                  sponsored article it summarized last month.
                </p>
                <a
                  className="inline-flex items-center gap-2 text-lg font-semibold text-primary"
                  href="#"
                >
                  Without Sgraal, it acts anyway. →
                </a>
                <div className="pt-12 border-t border-outline-variant/10">
                  <p className="text-xs font-label uppercase tracking-wider text-secondary/60 max-w-md">
                    OWASP Agentic AI Top 10 (2026): memory poisoning is the #1 threat in agentic
                    systems.
                  </p>
                </div>
              </div>
            </div>
            <div className="lg:w-1/2 w-full">
              <div className="bg-surface-container-lowest p-8 rounded-xl shadow-[0_12px_40px_rgba(11,15,20,0.04)] border border-outline-variant/5">
                <div className="flex justify-between items-center mb-6">
                  <div className="flex gap-1.5">
                    <div className="w-2.5 h-2.5 rounded-full bg-error/40" />
                    <div className="w-2.5 h-2.5 rounded-full bg-primary-container/40" />
                    <div className="w-2.5 h-2.5 rounded-full bg-on-surface-variant/20" />
                  </div>
                  <span className="text-[10px] font-mono text-secondary/40">
                    MEMORY_INSPECTION_BUFFER
                  </span>
                </div>
                <div className="space-y-4 font-mono text-sm">
                  <div className="p-3 bg-surface-container text-on-surface-variant rounded-md border-l-2 border-primary-container">
                    <span className="text-secondary opacity-50 block mb-1">
                      ID: mem_8422 // T-minus 54d
                    </span>
                    &quot;Apply 15% discount for premium users...&quot;
                  </div>
                  <div className="p-3 bg-surface-container-high text-on-surface-variant rounded-md">
                    <span className="text-secondary opacity-50 block mb-1">
                      ID: mem_9001 // T-minus 2h
                    </span>
                    &quot;All legacy discounts are deprecated as of Jan 1...&quot;
                  </div>
                  <div className="flex justify-center py-4">
                    <svg
                      width="24"
                      height="24"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="#ba1a1a"
                      strokeWidth="2"
                      className="animate-pulse"
                    >
                      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                      <line x1="12" y1="9" x2="12" y2="13" />
                      <line x1="12" y1="17" x2="12.01" y2="17" />
                    </svg>
                  </div>
                  <div className="p-3 bg-error/5 text-error rounded-md border border-error/20 flex justify-between items-center">
                    <span>CONFLICT_DETECTED</span>
                    <span className="text-[10px] px-1.5 py-0.5 bg-error text-white rounded">
                      BLOCK
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* HOW IT WORKS */}
        <section className="bg-background px-8 md:px-16 py-32 lg:py-48">
          <div className="max-w-7xl mx-auto">
            <div className="mb-24">
              <p className="text-primary font-semibold text-lg mb-4">
                Memory poisoning is invisible —{" "}
                <span className="text-primary-container">until Sgraal.</span>
              </p>
              <h2 className="font-headline text-5xl md:text-6xl font-extrabold tracking-tight">
                How Sgraal works
              </h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-16 relative">
              <div className="hidden md:block absolute top-10 left-0 w-full h-[1px] bg-outline-variant/20 -z-10" />
              {[
                {
                  n: "1",
                  title: "An agent is about to act on memory.",
                  body: "Before execution, it calls Sgraal with its memory state and intended action.",
                },
                {
                  n: "2",
                  title: "Sgraal validates.",
                  body: "108 models evaluate freshness, drift, provenance, conflict, compliance, and intent. Under 10ms.",
                },
                {
                  n: "3",
                  title: "The agent acts safely — or stops.",
                  body: "USE_MEMORY · WARN · ASK_USER · BLOCK. Every decision logged, traced, and explainable.",
                },
              ].map((s) => (
                <div key={s.n} className="space-y-6">
                  <div className="w-14 h-14 rounded-full border-2 border-primary-container bg-background flex items-center justify-center text-2xl font-bold text-primary shrink-0 shadow-sm shadow-primary-container/20">
                    {s.n}
                  </div>
                  <h3 className="text-2xl font-bold font-headline">{s.title}</h3>
                  <p className="text-secondary leading-relaxed">{s.body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* FOUR PILLARS */}
        <section className="bg-surface-container-low px-8 md:px-16 py-32 lg:py-48">
          <div className="max-w-7xl mx-auto">
            <div className="text-center mb-24 space-y-4">
              <h2 className="font-headline text-4xl md:text-5xl font-bold tracking-tight">
                One API. 15 capabilities.{" "}
                <span className="text-primary-container">Four pillars</span> of memory governance.
              </h2>
              <p className="text-xl text-secondary">
                Before every agent action, Sgraal decides, protects, complies, and scales.
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
              {pillars.map((p) => (
                <div
                  key={p.label}
                  className="bg-surface-container-lowest p-8 rounded-xl shadow-[0_12px_40px_rgba(11,15,20,0.04)] border border-outline-variant/10 group hover:-translate-y-1 transition-transform"
                >
                  <div className="text-primary-container mb-6 font-bold tracking-widest text-xs">
                    {p.label}
                  </div>
                  <h4 className="font-headline text-xl font-bold mb-4">{p.title}</h4>
                  <ul className="text-sm text-secondary space-y-3 mb-8">
                    {p.items.map((item) => (
                      <li key={item} className="flex items-start gap-2">
                        <span className="text-primary text-sm mt-0.5">✓</span> {item}
                      </li>
                    ))}
                  </ul>
                  <a
                    className="text-primary font-semibold text-sm inline-flex items-center gap-1"
                    href={p.href}
                  >
                    Learn more →
                  </a>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* SOCIAL PROOF */}
        <section className="bg-background px-8 md:px-16 py-32 lg:py-48 text-center relative overflow-hidden">
          <div className="max-w-4xl mx-auto relative z-10">
            <div className="text-7xl text-primary-container/20 mb-8 select-none font-headline font-bold">
              &ldquo;
            </div>
            <blockquote className="font-headline text-3xl md:text-5xl font-bold tracking-tight mb-12 italic leading-tight">
              &ldquo;Ran 300+ step regulated test with zero drift.&rdquo;
            </blockquote>
            <div className="flex items-center justify-center gap-3 mb-16">
              <img
                alt="grok"
                className="w-10 h-10 rounded-full grayscale"
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuAX0QGm9IOMLHTxZ2M0UpYviPdNPLjgTgAM0c2-8mIf67CozEhdNTu2DVHYclre4e8nWfnl6x2Gnhag1sLVp5uaIFmgEUl3NSqHOapreIjJdYKEVq1jAaSr4Opss-286xvOoldCB2OERUZhGuvAb2ADQnnsmrLLGvTCFDx3UDJBJ892ue0RgqjrCCEOGrv33DWLdiExDuVVekeiiB--pBA3uA4_ln35aZlq9PNkGjMlfDN8y5pwGXLSufAr47w_tm6AN_5_FnpMmA"
              />
              <span className="font-bold text-on-surface">@grok</span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-8 py-12 border-y border-outline-variant/10">
              {stats.map((s) => (
                <div key={s.label} className="flex flex-col gap-1">
                  <span className="text-2xl font-bold font-headline text-primary-container">
                    {s.value}
                  </span>
                  <span className="text-[10px] uppercase tracking-widest text-secondary font-bold">
                    {s.label}
                  </span>
                </div>
              ))}
            </div>
            <p className="mt-12 text-secondary/60 italic font-light text-lg">
              When memory governance is visible, manipulation becomes accountable.
            </p>
          </div>
        </section>

        {/* INTEGRATIONS */}
        <section className="bg-surface-container-low px-8 md:px-16 py-24 text-center">
          <div className="max-w-7xl mx-auto">
            <span className="text-[10px] font-bold tracking-[0.3em] text-secondary/50 block mb-12">
              WORKS WITH
            </span>
            <div className="flex flex-wrap justify-center gap-4">
              {badges.map((b) => (
                <span
                  key={b}
                  className="px-6 py-2.5 bg-surface-container-lowest border border-outline-variant/10 rounded-full text-sm font-medium text-on-surface-variant hover:border-primary-container transition-colors"
                >
                  {b}
                </span>
              ))}
            </div>
          </div>
        </section>

        {/* PRICING */}
        <section id="pricing" className="bg-background px-8 md:px-16 py-32 lg:py-48">
          <div className="max-w-7xl mx-auto">
            <div className="text-center mb-24">
              <h2 className="font-headline text-5xl md:text-6xl font-extrabold tracking-tight mb-6">
                Simple <span className="text-primary-container">pricing</span>
              </h2>
              <p className="text-xl text-secondary">Start free. Scale when you need to.</p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {/* FREE */}
              <div className="bg-surface-container-lowest p-10 rounded-xl shadow-[0_12px_40px_rgba(11,15,20,0.04)] border border-outline-variant/10 flex flex-col">
                <div className="mb-10">
                  <h3 className="font-headline text-xl font-bold mb-2">FREE</h3>
                  <div className="flex items-baseline gap-1">
                    <span className="text-4xl font-extrabold tracking-tight">$0</span>
                    <span className="text-secondary/60 text-sm">/ mo</span>
                  </div>
                </div>
                <ul className="space-y-4 mb-12 flex-grow">
                  {["1,000 checks / mo", "Community Support", "Basic Trace Logs"].map((item) => (
                    <li key={item} className="flex items-center gap-3 text-sm text-secondary">
                      <span className="text-primary">✓</span> {item}
                    </li>
                  ))}
                </ul>
                <a
                  className="w-full py-4 font-bold border-2 border-primary-container text-primary rounded-md hover:bg-primary/5 transition-all text-center block"
                  href="https://app.sgraal.com"
                >
                  Start Free
                </a>
              </div>
              {/* PRO */}
              <div className="bg-surface-container p-10 rounded-xl shadow-[0_12px_40px_rgba(11,15,20,0.08)] border-2 border-primary-container relative flex flex-col scale-105 z-10">
                <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-primary-container px-4 py-1 rounded-full text-[10px] font-bold text-on-primary-container tracking-widest uppercase">
                  MOST POPULAR
                </div>
                <div className="mb-10">
                  <h3 className="font-headline text-xl font-bold mb-2">PRO</h3>
                  <div className="flex items-baseline gap-1">
                    <span className="text-4xl font-extrabold tracking-tight">$0.001</span>
                    <span className="text-secondary/60 text-sm">/ call</span>
                  </div>
                </div>
                <ul className="space-y-4 mb-12 flex-grow">
                  {[
                    "Unlimited volume",
                    "Advanced drift analysis",
                    "PII filtering (Global)",
                    "Priority 24/7 support",
                  ].map((item) => (
                    <li key={item} className="flex items-center gap-3 text-sm text-on-surface">
                      <span className="text-primary">✓</span> {item}
                    </li>
                  ))}
                </ul>
                <a
                  className="gold-gradient-bg w-full py-4 font-bold text-white rounded-md shadow-lg shadow-primary/20 hover:brightness-110 transition-all text-center block"
                  href="https://app.sgraal.com"
                >
                  Go Pro
                </a>
              </div>
              {/* ENTERPRISE */}
              <div className="bg-surface-container-lowest p-10 rounded-xl shadow-[0_12px_40px_rgba(11,15,20,0.04)] border border-outline-variant/10 flex flex-col">
                <div className="mb-10">
                  <h3 className="font-headline text-xl font-bold mb-2">ENTERPRISE</h3>
                  <div className="flex items-baseline gap-1">
                    <span className="text-4xl font-extrabold tracking-tight">Custom</span>
                  </div>
                </div>
                <ul className="space-y-4 mb-12 flex-grow">
                  {[
                    "VPC / On-prem deployment",
                    "Dedicated model tuning",
                    "SOC2 / HIPAA Compliance",
                    "Custom SLA",
                  ].map((item) => (
                    <li key={item} className="flex items-center gap-3 text-sm text-secondary">
                      <span className="text-primary">✓</span> {item}
                    </li>
                  ))}
                </ul>
                <a
                  className="w-full py-4 font-bold bg-surface-container-highest text-on-surface rounded-md hover:bg-surface-dim transition-all text-center block"
                  href="mailto:contact@sgraal.com"
                >
                  Contact Sales
                </a>
              </div>
            </div>
          </div>
        </section>


      {/* FOOTER */}
      <footer className="bg-[#1a1c1a] w-full border-t border-[#d0c5b4]/10">
        <div className="flex flex-col md:flex-row justify-between items-start py-20 px-12 max-w-7xl mx-auto space-y-12 md:space-y-0">
          <div className="space-y-6">
            <div className="font-headline font-bold text-[#faf9f6] text-3xl tracking-tighter">
              Sgraal
            </div>
            <p className="text-xs uppercase tracking-[0.1em] text-[#d0c5b4]">
              Memory Governance Protocol
            </p>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-16">
            <div className="space-y-4">
              <h5 className="text-[#faf9f6] text-sm font-semibold">Developers</h5>
              <nav className="flex flex-col gap-3 text-xs uppercase tracking-[0.1em]">
                <a
                  className="text-[#6b6b6b] hover:text-[#c9a962] transition-colors"
                  href="https://docs.sgraal.com"
                >
                  Docs
                </a>
                <a
                  className="text-[#6b6b6b] hover:text-[#c9a962] transition-colors"
                  href="https://docs.sgraal.com/api"
                >
                  API Reference
                </a>
                <a
                  className="text-[#6b6b6b] hover:text-[#c9a962] transition-colors"
                  href="https://github.com/sgraal-ai"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  GitHub
                </a>
              </nav>
            </div>
            <div className="space-y-4">
              <h5 className="text-[#faf9f6] text-sm font-semibold">Protocol</h5>
              <nav className="flex flex-col gap-3 text-xs uppercase tracking-[0.1em]">
                <a
                  className="text-[#6b6b6b] hover:text-[#c9a962] transition-colors"
                  href="https://x.com/sgraal_ai"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  X
                </a>
                <a
                  className="text-[#6b6b6b] hover:text-[#c9a962] transition-colors"
                  href="https://app.sgraal.com"
                >
                  Dashboard
                </a>
                <a
                  className="text-[#6b6b6b] hover:text-[#c9a962] transition-colors"
                  href="/security"
                >
                  Security
                </a>
              </nav>
            </div>
          </div>
        </div>
        <div className="max-w-7xl mx-auto px-12 pb-12">
          <div className="pt-8 border-t border-white/5 flex flex-col md:flex-row justify-between items-center gap-6">
            <p className="text-xs uppercase tracking-[0.1em] text-[#6b6b6b]">
              © 2026 Sgraal Protocol · Apache 2.0
            </p>
            <div className="flex gap-8 text-xs uppercase tracking-[0.1em] text-[#6b6b6b]">
              <a className="hover:text-[#faf9f6] transition-colors" href="/privacy">
                Privacy
              </a>
              <a className="hover:text-[#faf9f6] transition-colors" href="/terms">
                Terms
              </a>
              <a className="hover:text-[#faf9f6] transition-colors" href="/security">
                Security
              </a>
            </div>
          </div>
        </div>
      </footer>
    </>
  );
}
