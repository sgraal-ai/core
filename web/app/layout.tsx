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
        <nav className="fixed top-0 left-0 right-0 z-40 bg-background/80 backdrop-blur-md border-b border-surface-light px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <a href="/" className="font-mono text-gold text-lg font-bold">Sgraal</a>
            <div className="hidden sm:flex items-center gap-5 text-sm text-muted">
              <a href="https://api.sgraal.com/docs" className="hover:text-foreground transition">Docs</a>
              <a href="/playground" className="hover:text-foreground transition">Playground</a>
              <a href="/#pricing" className="hover:text-foreground transition">Pricing</a>
              <a href="https://github.com/sgraal-ai/core" target="_blank" rel="noopener noreferrer" className="hover:text-foreground transition">GitHub</a>
              <a href="https://x.com/sgraal_ai" target="_blank" rel="noopener noreferrer" className="hover:text-foreground transition">X</a>
            </div>
          </div>
          <a href="/#pricing" className="bg-gold text-background font-semibold text-sm px-5 py-2 rounded-lg hover:bg-gold-dim transition">
            Get API Key
          </a>
        </nav>
        <div className="pt-14">{children}</div>
      </body>
    </html>
  );
}
