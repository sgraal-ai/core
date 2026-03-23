import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

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
  robots: {
    index: true,
    follow: true,
  },
  alternates: {
    canonical: "https://sgraal.com",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <nav className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-md border-b border-surface-light px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <a href="/" className="font-mono text-gold text-lg font-bold">Sgraal</a>
            <div className="hidden sm:flex items-center gap-5 text-sm text-muted">
              <a href="#how-it-works" className="hover:text-foreground transition">How it works</a>
              <a href="#quickstart" className="hover:text-foreground transition">Quickstart</a>
              <a href="#pricing" className="hover:text-foreground transition">Pricing</a>
              <a href="/docs/compliance" className="hover:text-foreground transition">Compliance</a>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <a href="https://sgraal-dashboard.vercel.app" className="text-sm text-gold hover:text-gold-dim transition font-semibold">
              Open Dashboard &rarr;
            </a>
            <a href="https://github.com/sgraal-ai/core" target="_blank" rel="noopener noreferrer" className="text-muted hover:text-foreground transition" title="GitHub">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/></svg>
            </a>
            <a href="https://x.com/sgraal_ai" target="_blank" rel="noopener noreferrer" className="text-muted hover:text-foreground transition" title="X (Twitter)">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
            </a>
          </div>
        </nav>
        <div className="pt-14">{children}</div>
      </body>
    </html>
  );
}
