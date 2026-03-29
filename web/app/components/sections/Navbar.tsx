export function Navbar() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-md border-b border-surface-light px-6 py-3 flex items-center justify-between">
      <div className="flex items-center gap-6">
        <a href="/" className="font-mono text-gold text-lg font-bold">Sgraal</a>
        <div className="hidden sm:flex items-center gap-5 text-sm text-muted">
          <a href="https://api.sgraal.com/docs" className="hover:text-foreground transition">Docs</a>
          <a href="/playground" className="hover:text-foreground transition">Playground</a>
          <a href="#pricing" className="hover:text-foreground transition">Pricing</a>
          <a href="https://github.com/sgraal-ai/core" target="_blank" rel="noopener noreferrer" className="hover:text-foreground transition">GitHub</a>
          <a href="https://x.com/sgraal_ai" target="_blank" rel="noopener noreferrer" className="hover:text-foreground transition">X</a>
        </div>
      </div>
      <a href="#pricing" className="bg-gold text-background font-semibold text-sm px-5 py-2 rounded-lg hover:bg-gold-dim transition"
        title="No signup required — demo key works immediately" aria-label="Get API Key — no signup required, demo key works immediately">
        Get API Key
      </a>
    </nav>
  );
}
