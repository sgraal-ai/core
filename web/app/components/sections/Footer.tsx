export function Footer() {
  return (
    <footer className="bg-[#1a1c1a] w-full border-t border-[#d0c5b4]/10">
      <div className="flex flex-col md:flex-row justify-between items-start py-20 px-12 max-w-7xl mx-auto space-y-12 md:space-y-0">
        <div className="space-y-6">
          <div className="font-headline font-bold text-[#faf9f6] text-3xl tracking-tighter">Sgraal</div>
          <p className="font-body text-xs uppercase tracking-[0.1em] text-[#d0c5b4]">Memory Governance Protocol</p>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-16">
          <div className="space-y-4">
            <h5 className="text-[#faf9f6] text-sm font-semibold">Developers</h5>
            <nav className="flex flex-col gap-3 font-body text-xs uppercase tracking-[0.1em]">
              <a className="text-[#6b6b6b] hover:text-[#c9a962] transition-colors" href="https://docs.sgraal.com">Docs</a>
              <a className="text-[#6b6b6b] hover:text-[#c9a962] transition-colors" href="https://docs.sgraal.com/api">API Reference</a>
              <a className="text-[#6b6b6b] hover:text-[#c9a962] transition-colors" href="https://github.com/sgraal-ai" target="_blank" rel="noopener noreferrer">GitHub</a>
            </nav>
          </div>
          <div className="space-y-4">
            <h5 className="text-[#faf9f6] text-sm font-semibold">Protocol</h5>
            <nav className="flex flex-col gap-3 font-body text-xs uppercase tracking-[0.1em]">
              <a className="text-[#6b6b6b] hover:text-[#c9a962] transition-colors" href="https://x.com/sgraal_ai" target="_blank" rel="noopener noreferrer">X</a>
              <a className="text-[#6b6b6b] hover:text-[#c9a962] transition-colors" href="https://app.sgraal.com">Dashboard</a>
              <a className="text-[#6b6b6b] hover:text-[#c9a962] transition-colors" href="/security">Security</a>
            </nav>
          </div>
        </div>
      </div>
      <div className="max-w-7xl mx-auto px-12 pb-12">
        <div className="pt-8 border-t border-white/5 flex flex-col md:flex-row justify-between items-center gap-6">
          <p className="font-body text-xs uppercase tracking-[0.1em] text-[#6b6b6b]">© 2026 Sgraal Protocol · Apache 2.0</p>
          <div className="flex gap-8 font-body text-xs uppercase tracking-[0.1em] text-[#6b6b6b]">
            <a className="hover:text-[#faf9f6] transition-colors" href="/privacy">Privacy</a>
            <a className="hover:text-[#faf9f6] transition-colors" href="/terms">Terms</a>
            <a className="hover:text-[#faf9f6] transition-colors" href="/security">Security</a>
          </div>
        </div>
      </div>
    </footer>
  );
}
