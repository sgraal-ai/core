import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sgraal — Memory Governance for AI Agents",
  description: "Before your AI agent acts, Sgraal checks if its memory is still true. One preflight call. Under 10ms.",
  metadataBase: new URL("https://sgraal.com"),
  openGraph: {
    title: "Sgraal — Memory Governance for AI Agents",
    description: "Your AI agent doesn't know it's forgetting. Sgraal catches stale, conflicting, and drifted memory before your agent acts.",
    url: "https://sgraal.com", siteName: "Sgraal", type: "website", locale: "en_US",
  },
  twitter: { card: "summary_large_image", title: "Sgraal — Memory Governance for AI Agents", description: "Your AI agent doesn't know it's forgetting. Sgraal catches it in under 10ms." },
  robots: { index: true, follow: true },
  alternates: { canonical: "https://sgraal.com" },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-white text-black" style={{ fontFamily: "'Inter', sans-serif" }}>
        <header className="fixed top-0 w-full z-50 bg-[#faf9f6]/90 backdrop-blur-md shadow-[0_12px_40px_rgba(11,15,20,0.04)]">
          <nav className="flex justify-between items-center px-8 md:px-16 max-w-[1440px] mx-auto h-20">
            <div className="flex items-center gap-12">
              <a className="text-2xl font-bold tracking-tighter text-[#1a1c1a]" style={{ fontFamily: "'Manrope', sans-serif" }} href="/">Sgraal</a>
              <div className="hidden lg:flex items-center gap-8 tracking-tight text-sm font-medium">
                <a className="text-[#6b6b6b] hover:text-[#1a1c1a] transition-colors" href="/decide">DECIDE</a>
                <a className="text-[#6b6b6b] hover:text-[#1a1c1a] transition-colors" href="/protect">PROTECT</a>
                <a className="text-[#6b6b6b] hover:text-[#1a1c1a] transition-colors" href="/comply">COMPLY</a>
                <a className="text-[#6b6b6b] hover:text-[#1a1c1a] transition-colors" href="/scale">SCALE</a>
                <a className="text-[#6b6b6b] hover:text-[#1a1c1a] transition-colors" href="/#pricing">Pricing</a>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="hidden sm:flex items-center gap-4 mr-4 text-gray-500">
                <a className="hover:text-black transition-colors" href="https://github.com/sgraal-ai" target="_blank" rel="noopener noreferrer"><svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z"/></svg></a>
                <a className="hover:text-black transition-colors" href="https://x.com/sgraal_ai" target="_blank" rel="noopener noreferrer"><svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.746l7.73-8.835L1.254 2.25H8.08l4.253 5.622 5.911-5.622zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg></a>
              </div>
              <a className="px-5 py-2 text-sm font-medium text-black hover:bg-gray-100 rounded-md transition-all" href="/playground">Playground</a>
              <a className="px-5 py-2 text-sm font-semibold text-white rounded-md transition-all shadow-sm" style={{ background: "linear-gradient(135deg, #745b1c, #c9a962)" }} href="https://app.sgraal.com">Get API Key</a>
            </div>
          </nav>
        </header>
        <main className="pt-20">{children}</main>
      </body>
    </html>
  );
}
