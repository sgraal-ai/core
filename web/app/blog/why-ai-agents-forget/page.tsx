import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Why Your AI Agent Is Forgetting — And Why You Don't Know | Sgraal Blog",
  description: "Your agent stores memories but never checks if they're still true. Here's what happens when stale, conflicting, and poisoned data drives decisions.",
  openGraph: {
    title: "Why Your AI Agent Is Forgetting — And Why You Don't Know",
    description: "Your agent stores memories but never checks if they're still true.",
    url: "https://sgraal.com/blog/why-ai-agents-forget",
    type: "article",
  },
  alternates: { canonical: "https://sgraal.com/blog/why-ai-agents-forget" },
};

export default function Post() {
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: "Why Your AI Agent Is Forgetting — And Why You Don't Know",
    datePublished: "2026-03-24",
    author: { "@type": "Organization", name: "Sgraal" },
    url: "https://sgraal.com/blog/why-ai-agents-forget",
  };

  return (
    <div className="max-w-2xl mx-auto py-16 px-6">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <a href="/blog" className="text-muted text-sm hover:text-gold transition">&larr; Blog</a>
      <time className="block text-muted text-sm font-mono mt-4">March 24, 2026</time>
      <h1 className="text-3xl font-bold mt-2 mb-8">Why Your AI Agent Is Forgetting — And Why You Don&apos;t Know</h1>

      <div className="prose prose-invert max-w-none text-foreground/85 leading-relaxed space-y-5 text-[15px]">
        <p>Every AI agent with persistent memory has the same hidden problem: it stores information but never checks whether that information is still true.</p>

        <p>Think about what happens in practice. A user tells your agent they prefer metric units. Six months later, they switch to imperial — but the old preference is still in memory, ranked by recency, not by reliability. Your agent confidently converts everything to kilometers. The user is confused. You get a support ticket. Nobody connects it to a stale memory entry.</p>

        <h2 className="text-xl font-semibold text-foreground mt-8 mb-3">Three failure modes nobody talks about</h2>

        <p><strong className="text-gold">Stale data.</strong> Memory entries decay at different rates. A tool_state entry (like an API response) goes stale in hours. A policy entry (like a compliance rule) stays valid for months. But every memory system today treats them the same — store it, retrieve it, use it. No freshness signal.</p>

        <p><strong className="text-gold">Conflicting sources.</strong> Two trusted sources say different things about the same entity. Your agent has no way to detect this. It picks whichever one ranks higher in similarity search and presents a confident answer built on a contradiction.</p>

        <p><strong className="text-gold">Poisoned data.</strong> An API endpoint starts returning bad data. Your agent ingests it as a new memory. Now every decision downstream is contaminated. There is no trust score, no provenance check, no way to detect that the source degraded.</p>

        <h2 className="text-xl font-semibold text-foreground mt-8 mb-3">The missing layer</h2>

        <p>These are not retrieval problems. RAG solves which chunks to find. The missing layer is: which of those chunks are safe to act on?</p>

        <p>This is what Sgraal does. Before your agent acts on a memory, Sgraal scores it across 10 risk components — freshness, source trust, conflict, propagation risk, drift — and returns one of four actions: USE_MEMORY, WARN, ASK_USER, or BLOCK.</p>

        <p>One API call. Under 10ms. The agent gets a quality signal before it makes a decision.</p>

        <h2 className="text-xl font-semibold text-foreground mt-8 mb-3">What you can do right now</h2>

        <p>Run your existing agent memories through a Sgraal preflight check. The retrospective audit will tell you exactly how many of your memories are stale, conflicting, or from degraded sources. Most teams find that 30-40% of their memory entries have reliability issues they did not know about.</p>

        <div className="mt-8 pt-6 border-t border-surface-light">
          <a href="/playground" className="bg-gold text-background font-semibold px-6 py-2.5 rounded-lg hover:bg-gold-dim transition inline-block text-sm">
            Check your agent&apos;s memory health →
          </a>
        </div>
      </div>
    </div>
  );
}
