import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sgraal — Memory Governance for AI Agents",
  description:
    "Before your AI agent acts, Sgraal checks if its memory is still true. One preflight call. Under 10ms. 9 risk components. Full explainability.",
  metadataBase: new URL("https://sgraal.com"),
  openGraph: {
    title: "Sgraal — Memory Governance for AI Agents",
    description:
      "Your AI agent doesn't know it's forgetting. Sgraal catches stale, conflicting, and drifted memory before your agent acts.",
    url: "https://sgraal.com",
    siteName: "Sgraal",
    type: "website",
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: "Sgraal — Memory Governance for AI Agents",
    description:
      "Your AI agent doesn't know it's forgetting. Sgraal catches it in under 10ms.",
  },
  robots: { index: true, follow: true },
  alternates: { canonical: "https://sgraal.com" },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col" style={{ fontFamily: "'Inter', sans-serif" }}>
        <nav className="sticky top-0 z-40 px-6 py-3 flex items-center justify-between"
          style={{ backgroundColor: "rgba(255,255,255,0.85)", backdropFilter: "blur(20px)", boxShadow: "0 1px 0 rgba(208,197,180,0.3)" }}>
          <div className="flex items-center gap-5">
            <a href="/" style={{ fontFamily: "'Manrope', sans-serif", fontWeight: 800, color: "var(--on-surface)", fontSize: "1.125rem" }}>Sgraal</a>
            <div className="hidden md:flex items-center gap-4 text-sm" style={{ color: "var(--on-surface-variant)" }}>
              <a href="/decide" className="transition hover:opacity-100" style={{ fontWeight: 500 }}>DECIDE</a>
              <a href="/protect" className="transition hover:opacity-100" style={{ fontWeight: 500 }}>PROTECT</a>
              <a href="/comply" className="transition hover:opacity-100" style={{ fontWeight: 500 }}>COMPLY</a>
              <a href="/scale" className="transition hover:opacity-100" style={{ fontWeight: 500 }}>SCALE</a>
              <a href="/#pricing" className="transition hover:opacity-100">Pricing</a>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <a href="https://github.com/sgraal-ai" target="_blank" rel="noopener noreferrer" className="transition" style={{ color: "var(--on-surface-variant)" }} title="GitHub">
              <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z"/></svg>
            </a>
            <a href="https://x.com/sgraal_ai" target="_blank" rel="noopener noreferrer" className="transition" style={{ color: "var(--on-surface-variant)" }} title="X">
              <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.746l7.73-8.835L1.254 2.25H8.08l4.253 5.622 5.911-5.622zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
            </a>
            <a href="/playground" className="hidden sm:inline-block text-sm px-4 py-1.5 rounded-md transition"
              style={{ color: "var(--on-surface)" }}>Playground</a>
            <a href="https://app.sgraal.com" className="text-sm px-5 py-1.5 rounded-md transition"
              style={{ background: "linear-gradient(135deg, #745b1c, #c9a962)", color: "#533d00", fontWeight: 600 }}>Get API Key</a>
          </div>
        </nav>
        <div>{children}</div>
      </body>
    </html>
  );
}
