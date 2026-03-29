export function Footer() {
  return (
    <footer className="border-t border-surface-light mt-10">
      <div className="max-w-5xl mx-auto px-6 py-10">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6 mb-8">
          <div>
            <p className="font-mono text-gold text-lg font-bold mb-1">Sgraal</p>
            <p className="text-muted text-sm">Memory Governance Protocol</p>
          </div>
          <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-muted">
            <a href="https://api.sgraal.com/docs" className="hover:text-foreground transition">Docs</a>
            <a href="https://api.sgraal.com/docs" className="hover:text-foreground transition">API Reference</a>
            <a href="https://github.com/sgraal-ai/core" target="_blank" rel="noopener noreferrer" className="hover:text-foreground transition">GitHub</a>
            <a href="https://x.com/sgraal_ai" target="_blank" rel="noopener noreferrer" className="hover:text-foreground transition">X</a>
            <a href="https://api.sgraal.com/health" className="hover:text-foreground transition">Status</a>
          </div>
        </div>

        <div className="border-t border-surface-light pt-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-muted">
          <p>&copy; 2026 Sgraal &middot; Apache 2.0</p>
          <div className="flex gap-4">
            <a href="/privacy" className="hover:text-foreground transition">Privacy</a>
            <a href="/terms" className="hover:text-foreground transition">Terms</a>
            <a href="/security" className="hover:text-foreground transition">Security</a>
          </div>
        </div>
      </div>
    </footer>
  );
}
