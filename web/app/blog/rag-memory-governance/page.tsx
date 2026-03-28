import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "RAG Is Not Enough: Why Retrieval Quality Needs a Risk Score | Sgraal Blog",
  description: "Retrieval gets you chunks. But which chunks are fresh? Which sources conflict? Without a quality signal, your RAG pipeline is flying blind.",
  openGraph: {
    title: "RAG Is Not Enough: Why Retrieval Quality Needs a Risk Score",
    description: "Without a quality signal, your RAG pipeline is flying blind.",
    url: "https://sgraal.com/blog/rag-memory-governance",
    type: "article",
  },
  alternates: { canonical: "https://sgraal.com/blog/rag-memory-governance" },
};

export default function Post() {
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: "RAG Is Not Enough: Why Retrieval Quality Needs a Risk Score",
    datePublished: "2026-03-26",
    author: { "@type": "Organization", name: "Sgraal" },
    url: "https://sgraal.com/blog/rag-memory-governance",
  };

  return (
    <div className="max-w-2xl mx-auto py-16 px-6">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <a href="/blog" className="text-muted text-sm hover:text-gold transition">&larr; Blog</a>
      <time className="block text-muted text-sm font-mono mt-4">March 26, 2026</time>
      <h1 className="text-3xl font-bold mt-2 mb-8">RAG Is Not Enough: Why Retrieval Quality Needs a Risk Score</h1>

      <div className="prose prose-invert max-w-none text-foreground/85 leading-relaxed space-y-5 text-[15px]">
        <p>Retrieval-Augmented Generation solved one problem: giving LLMs access to external knowledge. But it created a new one that nobody is addressing: every retrieved chunk is treated as equally trustworthy.</p>

        <p>Your vector database returns the 20 most relevant chunks. Some are from yesterday. Some are from 2022. Some contradict each other. The LLM has no way to know. It synthesizes a confident answer from a mix of fresh facts and stale data.</p>

        <h2 className="text-xl font-semibold text-foreground mt-8 mb-3">The before: retrieval without governance</h2>

        <p>A fintech agent retrieves 15 chunks about EUR/USD trading patterns. Three of them reference Q3 2024 data. Two reference conflicting Fed policy interpretations. The agent builds a recommendation from all 15, weighted by semantic similarity — not by reliability. The recommendation goes to a trader.</p>

        <p>Nobody checks whether the chunks are current. Nobody detects the contradiction. The retrieval worked perfectly. The quality was terrible.</p>

        <h2 className="text-xl font-semibold text-foreground mt-8 mb-3">The after: retrieval with a quality gate</h2>

        <p>The same 15 chunks go through <code className="text-gold">/v1/rag/filter</code> before reaching the LLM. Sgraal scores each chunk for freshness (Weibull decay by content type), source trust, and conflict. The 3 stale chunks get filtered. The contradicting pair triggers a WARN. The agent receives 10 clean chunks and a confidence signal.</p>

        <p>The result: the LLM sees better input. Hallucination rate drops — not because the model improved, but because the input quality improved.</p>

        <h2 className="text-xl font-semibold text-foreground mt-8 mb-3">What chunk freshness actually means</h2>

        <p>Not all information decays at the same rate. A tool_state chunk (API response, price data) goes stale in hours. A semantic chunk (general knowledge) stays valid for months. A policy chunk (compliance rules) is near-permanent.</p>

        <p>Sgraal uses Weibull decay curves calibrated per memory type. A 30-day-old tool_state entry scores 89/100 risk. A 30-day-old policy entry scores 4/100. Same age, radically different reliability. Your RAG pipeline doesn&apos;t know this. Sgraal does.</p>

        <h2 className="text-xl font-semibold text-foreground mt-8 mb-3">Adding it to your pipeline</h2>

        <p>Two lines of code. After retrieval, before the LLM:</p>

        <pre className="bg-surface border border-surface-light rounded-lg p-4 text-sm font-mono text-foreground/80 overflow-x-auto">
{`from sgraal.rag_filter import SgraalRAGFilter

f = SgraalRAGFilter(api_key="sg_live_...", max_omega=60)
safe_chunks = f.filter(retrieved_chunks)`}
        </pre>

        <p>Chunks with omega above your threshold get filtered. The rest pass through with a <code className="text-gold">sgraal_omega</code> score attached. Your LLM context is now quality-gated.</p>

        <div className="mt-8 pt-6 border-t border-surface-light">
          <a href="https://api.sgraal.com/docs" className="bg-gold text-background font-semibold px-6 py-2.5 rounded-lg hover:bg-gold-dim transition inline-block text-sm">
            Try /v1/rag/filter free →
          </a>
        </div>
      </div>
    </div>
  );
}
