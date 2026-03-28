import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "EU AI Act 2025: What It Means for Your AI Agent's Memory | Sgraal Blog",
  description: "Article 12 requires traceability. Article 13 requires transparency. If your agent acts on stale memory, you can't demonstrate compliance.",
  openGraph: {
    title: "EU AI Act 2025: What It Means for Your AI Agent's Memory",
    description: "If your agent acts on stale memory, you can't demonstrate compliance.",
    url: "https://sgraal.com/blog/eu-ai-act-memory",
    type: "article",
  },
  alternates: { canonical: "https://sgraal.com/blog/eu-ai-act-memory" },
};

export default function Post() {
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: "EU AI Act 2025: What It Means for Your AI Agent's Memory",
    datePublished: "2026-03-28",
    author: { "@type": "Organization", name: "Sgraal" },
    url: "https://sgraal.com/blog/eu-ai-act-memory",
  };

  return (
    <div className="max-w-2xl mx-auto py-16 px-6">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <a href="/blog" className="text-muted text-sm hover:text-gold transition">&larr; Blog</a>
      <time className="block text-muted text-sm font-mono mt-4">March 28, 2026</time>
      <h1 className="text-3xl font-bold mt-2 mb-8">EU AI Act 2025: What It Means for Your AI Agent&apos;s Memory</h1>

      <div className="prose prose-invert max-w-none text-foreground/85 leading-relaxed space-y-5 text-[15px]">
        <p>The EU AI Act entered enforcement in 2025. If your AI agent makes decisions in the EU — especially in finance, healthcare, or legal — three articles directly affect how you manage agent memory.</p>

        <h2 className="text-xl font-semibold text-foreground mt-8 mb-3">Article 12: Logging and traceability</h2>

        <p>High-risk AI systems must maintain logs that enable traceability of decisions. For agents with persistent memory, this means: when your agent acts on a memory, you must be able to show what that memory contained, how old it was, how trustworthy the source was, and whether any conflicts existed.</p>

        <p>Most agent memory systems today are append-only stores with no metadata. They can tell you what was retrieved, but not whether it was reliable at decision time. Article 12 requires the reliability assessment, not just the retrieval log.</p>

        <p>Sgraal&apos;s preflight response includes every field Article 12 requires: <code className="text-gold">omega_mem_final</code>, <code className="text-gold">component_breakdown</code>, <code className="text-gold">shapley_values</code>, <code className="text-gold">request_id</code>, and <code className="text-gold">action_override_chain</code>. Every decision is traceable to the exact memory state and risk assessment.</p>

        <h2 className="text-xl font-semibold text-foreground mt-8 mb-3">Article 9: Risk management for medical AI</h2>

        <p>AI systems in healthcare require human oversight when risk exceeds acceptable thresholds. Sgraal&apos;s HIPAA and FDA 510(k) compliance profiles enforce this automatically: when <code className="text-gold">domain=medical</code> and <code className="text-gold">omega &gt; 40</code>, the system flags the decision for human review.</p>

        <p>This is not just a recommendation — it is an override. The compliance engine can escalate <code className="text-gold">recommended_action</code> to BLOCK when Article 9 conditions are met, preventing the agent from acting on unreliable memory in medical contexts.</p>

        <h2 className="text-xl font-semibold text-foreground mt-8 mb-3">Article 13: Transparency</h2>

        <p>Users and operators must be able to understand how the AI system works. Every Sgraal response includes an <code className="text-gold">explainability_note</code> identifying the highest-risk component and explaining why the system recommended a specific action.</p>

        <p>The <code className="text-gold">/v1/explain</code> endpoint generates human-readable explanations in English, German, and French — at developer, compliance, and executive reading levels. Shapley attribution shows exactly how much each risk component contributed to the final score.</p>

        <h2 className="text-xl font-semibold text-foreground mt-8 mb-3">What to do now</h2>

        <p>If your AI agent operates in the EU, add <code className="text-gold">compliance_profile: &quot;EU_AI_ACT&quot;</code> to your preflight requests. Sgraal will automatically enforce Articles 9, 12, and 13 on every decision. Critical violations override the recommended action to BLOCK before your agent can act on non-compliant memory.</p>

        <pre className="bg-surface border border-surface-light rounded-lg p-4 text-sm font-mono text-foreground/80 overflow-x-auto">
{`{
  "memory_state": [...],
  "action_type": "irreversible",
  "domain": "fintech",
  "compliance_profile": "EU_AI_ACT"
}`}
        </pre>

        <p>One field. Full Article 12 + 13 compliance. Automatic Article 9 escalation for medical domains.</p>

        <div className="mt-8 pt-6 border-t border-surface-light">
          <a href="/docs/compliance" className="bg-gold text-background font-semibold px-6 py-2.5 rounded-lg hover:bg-gold-dim transition inline-block text-sm">
            See compliance profiles →
          </a>
        </div>
      </div>
    </div>
  );
}
