export function Footer() {
  return (
    <footer className="bg-[#1a1c1a] border-t border-[#d0c5b4]/10">
      <div className="max-w-7xl mx-auto px-12">
        <div className="flex flex-col md:flex-row justify-between py-20 gap-16">
          <div>
            <p className="text-3xl font-bold text-[#faf9f6] tracking-tighter font-headline mb-2">Sgraal</p>
            <p className="text-xs uppercase tracking-[0.1em] text-[#d0c5b4]">Memory Governance Protocol</p>
          </div>
          <div className="grid grid-cols-2 gap-x-20 gap-y-4">
            <div className="space-y-3">
              <p className="text-[10px] font-bold tracking-widest uppercase text-[#6b6b6b] mb-2">Developers</p>
              <a href="https://docs.sgraal.com" className="block text-[#6b6b6b] hover:text-[#c9a962] transition-colors text-xs uppercase tracking-[0.1em]">Docs</a>
              <a href="https://docs.sgraal.com/api" className="block text-[#6b6b6b] hover:text-[#c9a962] transition-colors text-xs uppercase tracking-[0.1em]">API Reference</a>
              <a href="https://github.com/sgraal-ai" target="_blank" rel="noopener noreferrer" className="block text-[#6b6b6b] hover:text-[#c9a962] transition-colors text-xs uppercase tracking-[0.1em]">GitHub</a>
            </div>
            <div className="space-y-3">
              <p className="text-[10px] font-bold tracking-widest uppercase text-[#6b6b6b] mb-2">Protocol</p>
              <a href="https://x.com/sgraal_ai" target="_blank" rel="noopener noreferrer" className="block text-[#6b6b6b] hover:text-[#c9a962] transition-colors text-xs uppercase tracking-[0.1em]">X</a>
              <a href="https://app.sgraal.com" className="block text-[#6b6b6b] hover:text-[#c9a962] transition-colors text-xs uppercase tracking-[0.1em]">Dashboard</a>
              <a href="/security" className="block text-[#6b6b6b] hover:text-[#c9a962] transition-colors text-xs uppercase tracking-[0.1em]">Security</a>
            </div>
          </div>
        </div>
        <div className="border-t border-white/5 pt-8 pb-12 flex flex-col sm:flex-row justify-between gap-4">
          <p className="text-[#6b6b6b] text-xs uppercase tracking-[0.1em]">© 2026 Sgraal Protocol · Apache 2.0</p>
          <div className="flex gap-6">
            <a href="/privacy" className="text-[#6b6b6b] hover:text-[#c9a962] transition-colors text-xs uppercase tracking-[0.1em]">Privacy</a>
            <a href="/terms" className="text-[#6b6b6b] hover:text-[#c9a962] transition-colors text-xs uppercase tracking-[0.1em]">Terms</a>
            <a href="/security" className="text-[#6b6b6b] hover:text-[#c9a962] transition-colors text-xs uppercase tracking-[0.1em]">Security</a>
          </div>
        </div>
      </div>
    </footer>
  );
}
