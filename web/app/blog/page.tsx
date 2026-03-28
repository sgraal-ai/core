import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Blog — Sgraal",
  description: "Articles on AI agent memory governance, RAG quality, compliance, and the Sgraal protocol.",
  openGraph: {
    title: "Blog — Sgraal",
    description: "Articles on AI agent memory governance, RAG quality, and compliance.",
    url: "https://sgraal.com/blog",
  },
  alternates: { canonical: "https://sgraal.com/blog" },
};

const POSTS = [
  {
    slug: "why-ai-agents-forget",
    title: "Why Your AI Agent Is Forgetting — And Why You Don't Know",
    date: "March 24, 2026",
    excerpt: "Your agent stores memories but never checks if they're still true. Here's what happens when stale, conflicting, and poisoned data drives decisions.",
  },
  {
    slug: "rag-memory-governance",
    title: "RAG Is Not Enough: Why Retrieval Quality Needs a Risk Score",
    date: "March 26, 2026",
    excerpt: "Retrieval gets you chunks. But which chunks are fresh? Which sources conflict? Without a quality signal, your RAG pipeline is flying blind.",
  },
  {
    slug: "eu-ai-act-memory",
    title: "EU AI Act 2025: What It Means for Your AI Agent's Memory",
    date: "March 28, 2026",
    excerpt: "Article 12 requires traceability. Article 13 requires transparency. If your agent acts on stale memory, you can't demonstrate compliance.",
  },
];

export default function BlogIndex() {
  return (
    <div className="max-w-3xl mx-auto py-16 px-6">
      <h1 className="text-3xl font-bold mb-2">Blog</h1>
      <p className="text-muted text-lg mb-10">Thinking about AI agent memory, governance, and reliability.</p>

      <div className="space-y-8">
        {POSTS.map((post) => (
          <Link key={post.slug} href={`/blog/${post.slug}`} className="block group">
            <article className="border border-surface-light rounded-lg p-6 hover:border-gold/50 transition">
              <time className="text-muted text-sm font-mono">{post.date}</time>
              <h2 className="text-xl font-semibold text-foreground mt-1 mb-2 group-hover:text-gold transition">
                {post.title}
              </h2>
              <p className="text-foreground/70 text-sm">{post.excerpt}</p>
            </article>
          </Link>
        ))}
      </div>
    </div>
  );
}
