export function Footer() {
  return (
    <footer className="mt-10" style={{ backgroundColor: "var(--obsidian)" }}>
      <div className="max-w-5xl mx-auto px-6 py-8">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span style={{ fontFamily: "'Manrope', sans-serif", fontWeight: 800, color: "#ffffff", fontSize: "1.125rem" }}>Sgraal</span>
            <span className="text-sm" style={{ color: "rgba(255,255,255,0.5)" }}>· Memory Governance Protocol</span>
          </div>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm" style={{ color: "rgba(255,255,255,0.6)" }}>
            <a href="https://docs.sgraal.com" className="transition hover:text-white">Docs</a>
            <a href="https://docs.sgraal.com/api" className="transition hover:text-white">API Reference</a>
            <a href="https://github.com/sgraal-ai" target="_blank" rel="noopener noreferrer" className="transition hover:text-white">GitHub</a>
            <a href="https://x.com/sgraal_ai" target="_blank" rel="noopener noreferrer" className="transition hover:text-white">X</a>
            <a href="https://app.sgraal.com" className="transition hover:text-white">Dashboard</a>
            <a href="/privacy" className="transition hover:text-white">Privacy</a>
            <a href="/terms" className="transition hover:text-white">Terms</a>
            <a href="/security" className="transition hover:text-white">Security</a>
            <span style={{ color: "rgba(255,255,255,0.4)", fontSize: "0.8rem" }}>© 2026 Apache 2.0</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
