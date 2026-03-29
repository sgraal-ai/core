export function Footer() {
  return (
    <footer className="bg-[#1a1c1a] border-t border-[#d0c5b4]/10">
      <div className="max-w-7xl mx-auto px-12">
        <div className="flex flex-col md:flex-row justify-between items-start py-16 gap-16">
          <div>
            <p className="text-2xl font-bold text-white font-headline tracking-tighter">Sgraal</p>
            <p className="text-xs text-white/50 mt-2">Memory Governance Protocol</p>
          </div>
          <div className="grid grid-cols-2 gap-16">
            <div>
              <p className="text-white/70 text-xs uppercase tracking-widest mb-4">Developers</p>
              <div className="space-y-3">
                <a href="https://docs.sgraal.com" className="block text-white/40 hover:text-[#c9a962] transition-colors text-xs uppercase tracking-widest">Docs</a>
                <a href="https://docs.sgraal.com/api" className="block text-white/40 hover:text-[#c9a962] transition-colors text-xs uppercase tracking-widest">API Reference</a>
                <a href="https://github.com/sgraal-ai" target="_blank" rel="noopener noreferrer" className="block text-white/40 hover:text-[#c9a962] transition-colors text-xs uppercase tracking-widest">GitHub</a>
              </div>
            </div>
            <div>
              <p className="text-white/70 text-xs uppercase tracking-widest mb-4">Protocol</p>
              <div className="space-y-3">
                <a href="https://x.com/sgraal_ai" target="_blank" rel="noopener noreferrer" className="block text-white/40 hover:text-[#c9a962] transition-colors text-xs uppercase tracking-widest">X</a>
                <a href="https://app.sgraal.com" className="block text-white/40 hover:text-[#c9a962] transition-colors text-xs uppercase tracking-widest">Dashboard</a>
                <a href="/security" className="block text-white/40 hover:text-[#c9a962] transition-colors text-xs uppercase tracking-widest">Security</a>
              </div>
            </div>
          </div>
        </div>
        <div className="border-t border-white/5 pt-8 pb-12 flex flex-col sm:flex-row justify-between gap-4">
          <p className="text-white/40 text-xs uppercase tracking-widest">© 2026 Sgraal Protocol · Apache 2.0</p>
          <div className="flex gap-6">
            <a href="/privacy" className="text-white/40 hover:text-[#c9a962] transition-colors text-xs uppercase tracking-widest">Privacy</a>
            <a href="/terms" className="text-white/40 hover:text-[#c9a962] transition-colors text-xs uppercase tracking-widest">Terms</a>
            <a href="/security" className="text-white/40 hover:text-[#c9a962] transition-colors text-xs uppercase tracking-widest">Security</a>
          </div>
        </div>
      </div>
    </footer>
  );
}
