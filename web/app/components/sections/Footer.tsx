export function Footer() {
  return (
    <footer style={{ backgroundColor: '#1a1c1a', borderTop: '1px solid rgba(208,197,180,0.1)' }}>
      <div className="flex flex-col md:flex-row justify-between items-start py-16 px-8 md:px-16 max-w-7xl mx-auto gap-12">
        <div>
          <p className="text-2xl font-bold text-white font-headline tracking-tighter">Sgraal</p>
          <p className="text-xs mt-2" style={{ color: 'rgba(255,255,255,0.5)' }}>Memory Governance Protocol</p>
        </div>
        <div className="grid grid-cols-2 gap-16">
          <div>
            <p className="text-xs uppercase tracking-widest mb-4" style={{ color: 'rgba(255,255,255,0.7)' }}>Developers</p>
            <div className="space-y-3">
              <a href="https://docs.sgraal.com" className="block text-xs uppercase tracking-widest transition-colors" style={{ color: 'rgba(255,255,255,0.4)' }}>Docs</a>
              <a href="https://docs.sgraal.com/api" className="block text-xs uppercase tracking-widest transition-colors" style={{ color: 'rgba(255,255,255,0.4)' }}>API Reference</a>
              <a href="https://github.com/sgraal-ai" target="_blank" rel="noopener noreferrer" className="block text-xs uppercase tracking-widest transition-colors" style={{ color: 'rgba(255,255,255,0.4)' }}>GitHub</a>
            </div>
          </div>
          <div>
            <p className="text-xs uppercase tracking-widest mb-4" style={{ color: 'rgba(255,255,255,0.7)' }}>Protocol</p>
            <div className="space-y-3">
              <a href="https://x.com/sgraal_ai" target="_blank" rel="noopener noreferrer" className="block text-xs uppercase tracking-widest transition-colors" style={{ color: 'rgba(255,255,255,0.4)' }}>X</a>
              <a href="https://app.sgraal.com" className="block text-xs uppercase tracking-widest transition-colors" style={{ color: 'rgba(255,255,255,0.4)' }}>Dashboard</a>
              <a href="/security" className="block text-xs uppercase tracking-widest transition-colors" style={{ color: 'rgba(255,255,255,0.4)' }}>Security</a>
            </div>
          </div>
        </div>
      </div>
      <div className="max-w-7xl mx-auto px-8 md:px-16 pb-8 pt-6 flex flex-col md:flex-row justify-between items-center gap-4"
        style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
        <p className="text-xs uppercase tracking-widest" style={{ color: 'rgba(255,255,255,0.4)' }}>© 2026 Sgraal Protocol · Apache 2.0</p>
        <div className="flex gap-6">
          <a href="/privacy" className="text-xs uppercase tracking-widest transition-colors" style={{ color: 'rgba(255,255,255,0.4)' }}>Privacy</a>
          <a href="/terms" className="text-xs uppercase tracking-widest transition-colors" style={{ color: 'rgba(255,255,255,0.4)' }}>Terms</a>
          <a href="/security" className="text-xs uppercase tracking-widest transition-colors" style={{ color: 'rgba(255,255,255,0.4)' }}>Security</a>
        </div>
      </div>
    </footer>
  );
}
