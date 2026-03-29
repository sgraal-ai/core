"use client";

const pillars = [
  { label: "DECIDE", title: "Conflict Resolution", items: ["Temporal decay weighting", "Multi-source consensus", "Uncertainty flagging"], href: "/decide" },
  { label: "PROTECT", title: "Poison Detection", items: ["Injection filtering", "Bias triangulation", "Adversarial buffer"], href: "/protect" },
  { label: "COMPLY", title: "Policy Guardrails", items: ["PII isolation", "Regional siloing", "Audit trail exports"], href: "/comply" },
  { label: "SCALE", title: "High Availability", items: ["< 10ms latency", "Edge deployment", "Global sync"], href: "/scale" },
];

const badges = ["LangChain", "CrewAI", "AutoGen", "LlamaIndex", "mem0", "MCP", "OpenAI", "Anthropic"];
const GOLD = "#c9a962";
const GOLD_GRADIENT = "linear-gradient(135deg, #745b1c, #c9a962)";
const HEADLINE = { fontFamily: "'Manrope', sans-serif" } as const;

export default function Home() {
  return (
    <>
      {/* HERO */}
      <section style={{ background: "#ffffff", padding: "8rem 2rem 6rem", textAlign: "center" }}>
        <div style={{ maxWidth: "56rem", margin: "0 auto" }}>
          <div style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem", padding: "0.25rem 1rem", borderRadius: "9999px", border: "1px solid #e5e7eb", fontSize: "0.625rem", textTransform: "uppercase" as const, letterSpacing: "0.2em", fontWeight: 700, color: "#9ca3af", marginBottom: "3rem" }}>
            <span style={{ width: "0.375rem", height: "0.375rem", borderRadius: "9999px", background: GOLD, display: "inline-block" }} />
            MEMORY GOVERNANCE PROTOCOL
          </div>
          <h1 style={{ fontSize: "clamp(2rem, 5vw, 4rem)", fontWeight: 800, letterSpacing: "-0.03em", lineHeight: 1.05, color: "#000000", marginBottom: "2rem", ...HEADLINE }}>
            AI agents act on memory. Sgraal decides if that memory is{" "}
            <span style={{ color: GOLD }}>safe to act on.</span>
          </h1>
          <p style={{ fontSize: "1.25rem", color: "#6b7280", maxWidth: "36rem", margin: "0 auto 3rem", fontWeight: 300, lineHeight: 1.7 }}>
            The memory governance protocol between AI agent memory and AI agent action.
          </p>
          <div style={{ display: "flex", flexWrap: "wrap" as const, justifyContent: "center", gap: "1.5rem", marginBottom: "5rem" }}>
            <a href="/playground" style={{ background: GOLD_GRADIENT, padding: "1rem 2rem", fontSize: "1.125rem", fontWeight: 700, color: "#ffffff", borderRadius: "0.375rem", textDecoration: "none" }}>
              Try it now — no signup
            </a>
            <a href="https://docs.sgraal.com" style={{ padding: "1rem 2rem", fontSize: "1.125rem", fontWeight: 700, color: "#000000", borderRadius: "0.375rem", textDecoration: "none" }}>
              Read the docs
            </a>
          </div>
          <div style={{ display: "flex", flexWrap: "wrap" as const, justifyContent: "center", gap: "3rem", fontSize: "0.875rem", textTransform: "uppercase" as const, letterSpacing: "0.1em", color: "#9ca3af" }}>
            <span><span style={{ color: GOLD, fontWeight: 700 }}>1,834</span> tests</span>
            <span><span style={{ color: GOLD, fontWeight: 700 }}>0</span> failures</span>
            <span>production ready</span>
          </div>
        </div>
      </section>

      {/* PROBLEM */}
      <section style={{ background: "#f9f9f9", padding: "6rem 2rem" }}>
        <div style={{ maxWidth: "80rem", margin: "0 auto", display: "flex", flexWrap: "wrap" as const, gap: "5rem", alignItems: "flex-start" }}>
          <div style={{ flex: "1 1 400px" }}>
            <h2 style={{ fontSize: "clamp(1.75rem, 4vw, 3rem)", fontWeight: 700, letterSpacing: "-0.02em", lineHeight: 1.1, color: "#000000", marginBottom: "2rem", ...HEADLINE }}>
              One wrong memory.<br />
              <span style={{ color: GOLD }}>One wrong decision.</span>
            </h2>
            <p style={{ fontSize: "1.125rem", lineHeight: 1.7, color: "#4b5563", marginBottom: "2rem" }}>
              Your AI agent is about to act. It has 47 memories to draw from. One of them is 54 days old, conflicts with two newer sources, and carries a commercial bias from a sponsored article it summarized last month.
            </p>
            <a href="#" style={{ fontSize: "1.125rem", fontWeight: 600, color: GOLD, textDecoration: "none", display: "inline-block", marginBottom: "2rem" }}>
              Without Sgraal, it acts anyway. →
            </a>
            <div style={{ borderTop: "1px solid #e5e7eb", paddingTop: "2rem" }}>
              <p style={{ fontSize: "0.75rem", textTransform: "uppercase" as const, letterSpacing: "0.05em", color: "#9ca3af" }}>
                OWASP Agentic AI Top 10 (2026): memory poisoning is the #1 threat in agentic systems.
              </p>
            </div>
          </div>
          <div style={{ flex: "1 1 400px" }}>
            <div style={{ background: "#ffffff", padding: "2rem", borderRadius: "0.75rem", border: "1px solid #f3f4f6", boxShadow: "0 4px 24px rgba(0,0,0,0.06)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
                <div style={{ display: "flex", gap: "0.375rem" }}>
                  <div style={{ width: "0.625rem", height: "0.625rem", borderRadius: "9999px", background: "#fca5a5" }} />
                  <div style={{ width: "0.625rem", height: "0.625rem", borderRadius: "9999px", background: "#fde68a" }} />
                  <div style={{ width: "0.625rem", height: "0.625rem", borderRadius: "9999px", background: "#e5e7eb" }} />
                </div>
                <span style={{ fontSize: "0.625rem", fontFamily: "monospace", color: "#d1d5db" }}>MEMORY_INSPECTION_BUFFER</span>
              </div>
              <div style={{ display: "flex", flexDirection: "column" as const, gap: "1rem", fontFamily: "monospace", fontSize: "0.875rem" }}>
                <div style={{ padding: "0.75rem", background: "#f9fafb", color: "#4b5563", borderRadius: "0.375rem", borderLeft: `2px solid ${GOLD}` }}>
                  <span style={{ color: "#9ca3af", display: "block", marginBottom: "0.25rem" }}>ID: mem_8422 // T-minus 54d</span>
                  &quot;Apply 15% discount for premium users...&quot;
                </div>
                <div style={{ padding: "0.75rem", background: "#f3f4f6", color: "#4b5563", borderRadius: "0.375rem" }}>
                  <span style={{ color: "#9ca3af", display: "block", marginBottom: "0.25rem" }}>ID: mem_9001 // T-minus 2h</span>
                  &quot;All legacy discounts are deprecated as of Jan 1...&quot;
                </div>
                <div style={{ display: "flex", justifyContent: "center", padding: "1rem 0" }}>
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2">
                    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                    <line x1="12" y1="9" x2="12" y2="13" />
                    <line x1="12" y1="17" x2="12.01" y2="17" />
                  </svg>
                </div>
                <div style={{ padding: "0.75rem", background: "#fef2f2", color: "#dc2626", borderRadius: "0.375rem", border: "1px solid #fecaca", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span>CONFLICT_DETECTED</span>
                  <span style={{ fontSize: "0.625rem", padding: "0.125rem 0.375rem", background: "#ef4444", color: "#ffffff", borderRadius: "0.25rem" }}>BLOCK</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section style={{ background: "#ffffff", padding: "6rem 2rem" }}>
        <div style={{ maxWidth: "80rem", margin: "0 auto" }}>
          <div style={{ marginBottom: "5rem" }}>
            <p style={{ fontSize: "1.125rem", fontWeight: 600, color: GOLD, marginBottom: "1rem" }}>
              Memory poisoning is invisible — until Sgraal.
            </p>
            <h2 style={{ fontSize: "clamp(2rem, 4vw, 3.5rem)", fontWeight: 800, letterSpacing: "-0.03em", color: "#000000", ...HEADLINE }}>
              How Sgraal works
            </h2>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "4rem" }}>
            {[
              { n: "1", title: "An agent is about to act on memory.", body: "Before execution, it calls Sgraal with its memory state and intended action." },
              { n: "2", title: "Sgraal validates.", body: "108 models evaluate freshness, drift, provenance, conflict, compliance, and intent. Under 10ms." },
              { n: "3", title: "The agent acts safely — or stops.", body: "USE_MEMORY · WARN · ASK_USER · BLOCK. Every decision logged, traced, and explainable." },
            ].map((s) => (
              <div key={s.n}>
                <div style={{ width: "3.5rem", height: "3.5rem", borderRadius: "9999px", border: `2px solid ${GOLD}`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: "1.5rem", fontWeight: 700, color: GOLD, marginBottom: "1.5rem" }}>
                  {s.n}
                </div>
                <h3 style={{ fontSize: "1.25rem", fontWeight: 700, color: "#000000", marginBottom: "1rem", ...HEADLINE }}>{s.title}</h3>
                <p style={{ color: "#6b7280", lineHeight: 1.7 }}>{s.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FOUR PILLARS */}
      <section style={{ background: "#f9f9f9", padding: "6rem 2rem" }}>
        <div style={{ maxWidth: "80rem", margin: "0 auto" }}>
          <div style={{ textAlign: "center", marginBottom: "5rem" }}>
            <h2 style={{ fontSize: "clamp(1.5rem, 3vw, 2.5rem)", fontWeight: 700, letterSpacing: "-0.02em", color: "#000000", marginBottom: "1rem", ...HEADLINE }}>
              One API. 15 capabilities. <span style={{ color: GOLD }}>Four pillars</span> of memory governance.
            </h2>
            <p style={{ fontSize: "1.125rem", color: "#6b7280" }}>Before every agent action, Sgraal decides, protects, complies, and scales.</p>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "2rem" }}>
            {pillars.map((p) => (
              <div key={p.label} style={{ background: "#ffffff", padding: "2rem", borderRadius: "0.75rem", border: "1px solid #f3f4f6", boxShadow: "0 2px 12px rgba(0,0,0,0.04)" }}>
                <div style={{ fontSize: "0.75rem", fontWeight: 700, letterSpacing: "0.15em", color: GOLD, marginBottom: "1.5rem" }}>{p.label}</div>
                <h4 style={{ fontSize: "1.125rem", fontWeight: 700, color: "#000000", marginBottom: "1rem", ...HEADLINE }}>{p.title}</h4>
                <ul style={{ listStyle: "none", marginBottom: "2rem" }}>
                  {p.items.map((item) => (
                    <li key={item} style={{ display: "flex", gap: "0.5rem", fontSize: "0.875rem", color: "#6b7280", marginBottom: "0.75rem" }}>
                      <span style={{ color: GOLD }}>✓</span> {item}
                    </li>
                  ))}
                </ul>
                <a href={p.href} style={{ fontSize: "0.875rem", fontWeight: 600, color: GOLD, textDecoration: "none" }}>Learn more →</a>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* SOCIAL PROOF */}
      <section style={{ background: "#ffffff", padding: "6rem 2rem", textAlign: "center" }}>
        <div style={{ maxWidth: "48rem", margin: "0 auto" }}>
          <div style={{ fontSize: "5rem", fontWeight: 700, color: GOLD, opacity: 0.2, lineHeight: 1, marginBottom: "2rem", ...HEADLINE }}>&ldquo;</div>
          <blockquote style={{ fontSize: "clamp(1.5rem, 3vw, 2.5rem)", fontWeight: 700, letterSpacing: "-0.02em", color: "#000000", marginBottom: "3rem", fontStyle: "italic", lineHeight: 1.2, ...HEADLINE }}>
            &ldquo;Ran 300+ step regulated test with zero drift.&rdquo;
          </blockquote>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "0.75rem", marginBottom: "4rem" }}>
            <img alt="grok" style={{ width: "2.5rem", height: "2.5rem", borderRadius: "9999px", filter: "grayscale(1)" }} src="https://lh3.googleusercontent.com/aida-public/AB6AXuAX0QGm9IOMLHTxZ2M0UpYviPdNPLjgTgAM0c2-8mIf67CozEhdNTu2DVHYclre4e8nWfnl6x2Gnhag1sLVp5uaIFmgEUl3NSqHOapreIjJdYKEVq1jAaSr4Opss-286xvOoldCB2OERUZhGuvAb2ADQnnsmrLLGvTCFDx3UDJBJ892ue0RgqjrCCEOGrv33DWLdiExDuVVekeiiB--pBA3uA4_ln35aZlq9PNkGjMlfDN8y5pwGXLSufAr47w_tm6AN_5_FnpMmA" />
            <span style={{ fontWeight: 700, color: "#000000" }}>@grok</span>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "2rem", padding: "3rem 0", borderTop: "1px solid #f3f4f6", borderBottom: "1px solid #f3f4f6", marginBottom: "3rem" }}>
            {[{ value: "1,834", label: "Tests" }, { value: "0", label: "Failures" }, { value: "300+", label: "Steps" }, { value: "Zero", label: "Drift" }].map((s) => (
              <div key={s.label}>
                <div style={{ fontSize: "1.5rem", fontWeight: 700, color: GOLD, ...HEADLINE }}>{s.value}</div>
                <div style={{ fontSize: "0.625rem", textTransform: "uppercase" as const, letterSpacing: "0.1em", color: "#9ca3af", fontWeight: 700 }}>{s.label}</div>
              </div>
            ))}
          </div>
          <p style={{ color: "#9ca3af", fontStyle: "italic", fontSize: "1.125rem" }}>When memory governance is visible, manipulation becomes accountable.</p>
        </div>
      </section>

      {/* INTEGRATIONS */}
      <section style={{ background: "#f9f9f9", padding: "5rem 2rem", textAlign: "center" }}>
        <div style={{ maxWidth: "80rem", margin: "0 auto" }}>
          <span style={{ fontSize: "0.625rem", fontWeight: 700, letterSpacing: "0.3em", color: "#9ca3af", display: "block", marginBottom: "3rem" }}>WORKS WITH</span>
          <div style={{ display: "flex", flexWrap: "wrap" as const, justifyContent: "center", gap: "1rem" }}>
            {badges.map((b) => (
              <span key={b} style={{ padding: "0.625rem 1.5rem", background: "#ffffff", border: "1px solid #e5e7eb", borderRadius: "9999px", fontSize: "0.875rem", fontWeight: 500, color: "#4b5563" }}>{b}</span>
            ))}
          </div>
        </div>
      </section>

      {/* PRICING */}
      <section style={{ background: "#ffffff", padding: "6rem 2rem" }} id="pricing">
        <div style={{ maxWidth: "80rem", margin: "0 auto" }}>
          <div style={{ textAlign: "center", marginBottom: "5rem" }}>
            <h2 style={{ fontSize: "clamp(2rem, 4vw, 3.5rem)", fontWeight: 800, letterSpacing: "-0.03em", color: "#000000", marginBottom: "1rem", ...HEADLINE }}>
              Simple <span style={{ color: GOLD }}>pricing</span>
            </h2>
            <p style={{ fontSize: "1.125rem", color: "#6b7280" }}>Start free. Scale when you need to.</p>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "2rem", alignItems: "start" }}>
            <div style={{ background: "#ffffff", padding: "2.5rem", borderRadius: "0.75rem", border: "1px solid #e5e7eb", display: "flex", flexDirection: "column" as const }}>
              <h3 style={{ fontSize: "1.25rem", fontWeight: 700, color: "#000000", marginBottom: "0.5rem", ...HEADLINE }}>FREE</h3>
              <div style={{ display: "flex", alignItems: "baseline", gap: "0.25rem", marginBottom: "2.5rem" }}>
                <span style={{ fontSize: "2.5rem", fontWeight: 800, color: "#000000" }}>$0</span>
                <span style={{ color: "#9ca3af", fontSize: "0.875rem" }}>/ mo</span>
              </div>
              <ul style={{ listStyle: "none", marginBottom: "3rem", flexGrow: 1 }}>
                {["1,000 checks / mo", "Community Support", "Basic Trace Logs"].map((item) => (
                  <li key={item} style={{ display: "flex", gap: "0.75rem", fontSize: "0.875rem", color: "#6b7280", marginBottom: "1rem" }}>
                    <span style={{ color: GOLD }}>✓</span> {item}
                  </li>
                ))}
              </ul>
              <a href="https://app.sgraal.com" style={{ display: "block", textAlign: "center", padding: "1rem", fontWeight: 700, border: `2px solid ${GOLD}`, color: GOLD, borderRadius: "0.375rem", textDecoration: "none" }}>Start Free</a>
            </div>
            <div style={{ background: "#fffdf7", padding: "2.5rem", borderRadius: "0.75rem", border: `2px solid ${GOLD}`, display: "flex", flexDirection: "column" as const, position: "relative" as const }}>
              <div style={{ position: "absolute" as const, top: "-1rem", left: "50%", transform: "translateX(-50%)", background: GOLD, padding: "0.25rem 1rem", borderRadius: "9999px", fontSize: "0.625rem", fontWeight: 700, letterSpacing: "0.1em", color: "#ffffff", whiteSpace: "nowrap" as const }}>MOST POPULAR</div>
              <h3 style={{ fontSize: "1.25rem", fontWeight: 700, color: "#000000", marginBottom: "0.5rem", ...HEADLINE }}>PRO</h3>
              <div style={{ display: "flex", alignItems: "baseline", gap: "0.25rem", marginBottom: "2.5rem" }}>
                <span style={{ fontSize: "2.5rem", fontWeight: 800, color: "#000000" }}>$0.001</span>
                <span style={{ color: "#9ca3af", fontSize: "0.875rem" }}>/ call</span>
              </div>
              <ul style={{ listStyle: "none", marginBottom: "3rem", flexGrow: 1 }}>
                {["Unlimited volume", "Advanced drift analysis", "PII filtering (Global)", "Priority 24/7 support"].map((item) => (
                  <li key={item} style={{ display: "flex", gap: "0.75rem", fontSize: "0.875rem", color: "#000000", marginBottom: "1rem" }}>
                    <span style={{ color: GOLD }}>✓</span> {item}
                  </li>
                ))}
              </ul>
              <a href="https://app.sgraal.com" style={{ display: "block", textAlign: "center", padding: "1rem", fontWeight: 700, background: GOLD_GRADIENT, color: "#ffffff", borderRadius: "0.375rem", textDecoration: "none" }}>Go Pro</a>
            </div>
            <div style={{ background: "#ffffff", padding: "2.5rem", borderRadius: "0.75rem", border: "1px solid #e5e7eb", display: "flex", flexDirection: "column" as const }}>
              <h3 style={{ fontSize: "1.25rem", fontWeight: 700, color: "#000000", marginBottom: "0.5rem", ...HEADLINE }}>ENTERPRISE</h3>
              <div style={{ marginBottom: "2.5rem" }}>
                <span style={{ fontSize: "2.5rem", fontWeight: 800, color: "#000000" }}>Custom</span>
              </div>
              <ul style={{ listStyle: "none", marginBottom: "3rem", flexGrow: 1 }}>
                {["VPC / On-prem deployment", "Dedicated model tuning", "SOC2 / HIPAA Compliance", "Custom SLA"].map((item) => (
                  <li key={item} style={{ display: "flex", gap: "0.75rem", fontSize: "0.875rem", color: "#6b7280", marginBottom: "1rem" }}>
                    <span style={{ color: GOLD }}>✓</span> {item}
                  </li>
                ))}
              </ul>
              <a href="mailto:contact@sgraal.com" style={{ display: "block", textAlign: "center", padding: "1rem", fontWeight: 700, background: "#f3f4f6", color: "#000000", borderRadius: "0.375rem", textDecoration: "none" }}>Contact Sales</a>
            </div>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer style={{ background: "#1a1c1a", borderTop: "1px solid rgba(208,197,180,0.1)" }}>
        <div style={{ maxWidth: "80rem", margin: "0 auto", padding: "5rem 3rem 3rem", display: "flex", flexWrap: "wrap" as const, justifyContent: "space-between", gap: "3rem" }}>
          <div>
            <div style={{ fontWeight: 700, color: "#faf9f6", fontSize: "1.875rem", letterSpacing: "-0.05em", marginBottom: "1rem", ...HEADLINE }}>Sgraal</div>
            <p style={{ fontSize: "0.75rem", textTransform: "uppercase" as const, letterSpacing: "0.1em", color: "#d0c5b4" }}>Memory Governance Protocol</p>
          </div>
          <div style={{ display: "flex", gap: "4rem", flexWrap: "wrap" as const }}>
            <div>
              <h5 style={{ color: "#faf9f6", fontSize: "0.875rem", fontWeight: 600, marginBottom: "1rem" }}>Developers</h5>
              <nav style={{ display: "flex", flexDirection: "column" as const, gap: "0.75rem" }}>
                {[["Docs", "https://docs.sgraal.com"], ["API Reference", "https://docs.sgraal.com/api"], ["GitHub", "https://github.com/sgraal-ai"]].map(([label, href]) => (
                  <a key={label} href={href} style={{ fontSize: "0.75rem", textTransform: "uppercase" as const, letterSpacing: "0.1em", color: "#6b6b6b", textDecoration: "none" }}>{label}</a>
                ))}
              </nav>
            </div>
            <div>
              <h5 style={{ color: "#faf9f6", fontSize: "0.875rem", fontWeight: 600, marginBottom: "1rem" }}>Protocol</h5>
              <nav style={{ display: "flex", flexDirection: "column" as const, gap: "0.75rem" }}>
                {[["X", "https://x.com/sgraal_ai"], ["Dashboard", "https://app.sgraal.com"], ["Security", "/security"]].map(([label, href]) => (
                  <a key={label} href={href} style={{ fontSize: "0.75rem", textTransform: "uppercase" as const, letterSpacing: "0.1em", color: "#6b6b6b", textDecoration: "none" }}>{label}</a>
                ))}
              </nav>
            </div>
          </div>
        </div>
        <div style={{ maxWidth: "80rem", margin: "0 auto", padding: "2rem 3rem 3rem", borderTop: "1px solid rgba(255,255,255,0.05)", display: "flex", flexWrap: "wrap" as const, justifyContent: "space-between", gap: "1rem" }}>
          <p style={{ fontSize: "0.75rem", textTransform: "uppercase" as const, letterSpacing: "0.1em", color: "#6b6b6b" }}>© 2026 Sgraal Protocol · Apache 2.0</p>
          <div style={{ display: "flex", gap: "2rem" }}>
            {[["Privacy", "/privacy"], ["Terms", "/terms"], ["Security", "/security"]].map(([label, href]) => (
              <a key={label} href={href} style={{ fontSize: "0.75rem", textTransform: "uppercase" as const, letterSpacing: "0.1em", color: "#6b6b6b", textDecoration: "none" }}>{label}</a>
            ))}
          </div>
        </div>
      </footer>
    </>
  );
}
