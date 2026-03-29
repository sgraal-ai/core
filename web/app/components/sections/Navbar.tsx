"use client";

import { usePathname } from "next/navigation";

export function Navbar() {
  const path = usePathname();

  const pillars = [
    { label: "DECIDE", href: "/decide" },
    { label: "PROTECT", href: "/protect" },
    { label: "COMPLY", href: "/comply" },
    { label: "SCALE", href: "/scale" },
  ];

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-md border-b border-surface-light px-6 py-3 flex items-center justify-between">
      <div className="flex items-center gap-5">
        <a href="/" className="font-mono text-gold text-lg font-bold mr-2">Sgraal</a>
        <div className="hidden md:flex items-center gap-4 text-sm">
          {pillars.map((p) => (
            <a key={p.label} href={p.href}
              className={`transition font-medium ${path.startsWith(p.href) ? "text-gold" : "text-muted hover:text-foreground"}`}>
              {p.label}
            </a>
          ))}
          <a href="/#pricing" className="text-muted hover:text-foreground transition">Pricing</a>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <a href="https://github.com/sgraal-ai" target="_blank" rel="noopener noreferrer" className="text-muted hover:text-foreground transition" title="GitHub">
          <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z"/></svg>
        </a>
        <a href="https://x.com/sgraal_ai" target="_blank" rel="noopener noreferrer" className="text-muted hover:text-foreground transition" title="X">
          <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.746l7.73-8.835L1.254 2.25H8.08l4.253 5.622 5.911-5.622zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
        </a>
        <a href="/playground" className="hidden sm:inline-block border border-surface-light text-foreground text-sm px-4 py-1.5 rounded-lg hover:bg-surface transition">
          Playground
        </a>
        <a href="https://app.sgraal.com" className="bg-gold text-background font-semibold text-sm px-5 py-1.5 rounded-lg hover:bg-gold-dim transition">
          Get API Key
        </a>
      </div>
    </nav>
  );
}
