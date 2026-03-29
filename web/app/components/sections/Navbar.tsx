"use client";

import { usePathname } from "next/navigation";

const pillars = [
  { label: "DECIDE", href: "/decide" },
  { label: "PROTECT", href: "/protect" },
  { label: "COMPLY", href: "/comply" },
  { label: "SCALE", href: "/scale" },
];

export function Navbar() {
  const path = usePathname();

  return (
    <header className="fixed top-0 w-full z-50 bg-[#faf9f6]/90 backdrop-blur-md shadow-[0_12px_40px_rgba(11,15,20,0.04)]">
      <nav className="flex justify-between items-center px-8 md:px-16 max-w-[1440px] mx-auto h-20">
        <div className="flex items-center gap-12">
          <a className="text-2xl font-bold tracking-tighter text-[#1a1c1a] font-headline" href="/">Sgraal</a>
          <div className="hidden lg:flex items-center gap-8 tracking-tight text-sm font-medium">
            {pillars.map((p) => (
              <a key={p.label} href={p.href}
                className={`hover:text-[#1a1c1a] transition-colors ${path.startsWith(p.href) ? "text-primary-container" : "text-[#6b6b6b]"}`}>
                {p.label}
              </a>
            ))}
            <a className="text-[#6b6b6b] hover:text-[#1a1c1a] transition-colors" href="/#pricing">Pricing</a>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="hidden sm:flex items-center gap-6 mr-4 text-sm font-medium text-secondary">
            <a className="hover:text-on-surface transition-colors" href="https://github.com/sgraal-ai" target="_blank" rel="noopener noreferrer">GitHub</a>
            <a className="hover:text-on-surface transition-colors" href="https://x.com/sgraal_ai" target="_blank" rel="noopener noreferrer">X</a>
          </div>
          <a className="px-5 py-2 text-sm font-medium text-on-surface hover:bg-surface-container-high rounded-md transition-all" href="/playground">Playground</a>
          <a className="gold-gradient-bg px-5 py-2 text-sm font-semibold text-white rounded-md transition-all shadow-sm" href="https://app.sgraal.com">Get API Key</a>
        </div>
      </nav>
    </header>
  );
}
