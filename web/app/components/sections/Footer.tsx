export function Footer() {
  return (
    <footer className="border-t border-surface-light mt-10">
      <div className="max-w-5xl mx-auto px-6 py-8">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-2">
            <span className="font-mono text-gold text-lg font-bold">Sgraal</span>
            <span className="text-muted text-sm">&middot; Memory Governance Protocol</span>
          </div>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-muted">
            <a href="https://docs.sgraal.com" className="hover:text-foreground transition">Docs</a>
            <a href="https://docs.sgraal.com/api" className="hover:text-foreground transition">API Reference</a>
            <a href="https://github.com/sgraal-ai" target="_blank" rel="noopener noreferrer" className="hover:text-foreground transition">GitHub</a>
            <a href="https://x.com/sgraal_ai" target="_blank" rel="noopener noreferrer" className="hover:text-foreground transition">X</a>
            <a href="https://app.sgraal.com" className="hover:text-foreground transition">Dashboard</a>
            <a href="/privacy" className="hover:text-foreground transition">Privacy</a>
            <a href="/terms" className="hover:text-foreground transition">Terms</a>
            <a href="/security" className="hover:text-foreground transition">Security</a>
            <span>&copy; 2026 Apache 2.0</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
