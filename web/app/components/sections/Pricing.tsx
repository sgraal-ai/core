export function Pricing() {
  return (
    <section id="pricing" className="bg-background px-8 md:px-16 py-32 lg:py-48">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-24">
          <h2 className="font-headline text-5xl md:text-6xl font-extrabold tracking-tight mb-6">Simple <span className="text-primary-container">pricing</span></h2>
          <p className="text-xl text-secondary">Start free. Scale when you need to.</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* FREE */}
          <div className="bg-surface-container-lowest p-10 rounded-xl shadow-[0_12px_40px_rgba(11,15,20,0.04)] border border-outline-variant/10 flex flex-col">
            <div className="mb-10">
              <h3 className="font-headline text-xl font-bold mb-2">FREE</h3>
              <div className="flex items-baseline gap-1">
                <span className="text-4xl font-extrabold tracking-tight">$0</span>
                <span className="text-secondary/60 text-sm">/ mo</span>
              </div>
            </div>
            <ul className="space-y-4 mb-12 flex-grow">
              <li className="flex items-center gap-3 text-sm text-secondary"><span className="text-primary">✓</span> 10,000 calls / month</li>
              <li className="flex items-center gap-3 text-sm text-secondary"><span className="text-primary">✓</span> All core features</li>
              <li className="flex items-center gap-3 text-sm text-secondary"><span className="text-primary">✓</span> Demo key — no credit card</li>
            </ul>
            <a className="w-full py-4 font-bold border-2 border-primary-container text-primary rounded-md hover:bg-primary/5 transition-all text-center block" href="/playground">Start Free</a>
          </div>
          {/* PRO */}
          <div className="bg-surface-container p-10 rounded-xl shadow-[0_12px_40px_rgba(11,15,20,0.08)] border-2 border-primary-container relative flex flex-col scale-105 z-10">
            <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-primary-container px-4 py-1 rounded-full text-[10px] font-bold text-on-primary-container tracking-widest uppercase">MOST POPULAR</div>
            <div className="mb-10">
              <h3 className="font-headline text-xl font-bold mb-2">PRO</h3>
              <div className="flex items-baseline gap-1">
                <span className="text-4xl font-extrabold tracking-tight">$0.001</span>
                <span className="text-secondary/60 text-sm">/ call</span>
              </div>
            </div>
            <ul className="space-y-4 mb-12 flex-grow">
              <li className="flex items-center gap-3 text-sm text-on-surface"><span className="text-primary">✓</span> Webhooks + streaming</li>
              <li className="flex items-center gap-3 text-sm text-on-surface"><span className="text-primary">✓</span> Compliance profiles</li>
              <li className="flex items-center gap-3 text-sm text-on-surface"><span className="text-primary">✓</span> Priority support</li>
              <li className="flex items-center gap-3 text-sm text-on-surface"><span className="text-primary">✓</span> Full Shapley attribution</li>
            </ul>
            <a className="gold-gradient-bg w-full py-4 font-bold text-white rounded-md shadow-lg shadow-primary/20 hover:brightness-110 transition-all text-center block" href="https://app.sgraal.com">Get API Key</a>
          </div>
          {/* ENTERPRISE */}
          <div className="bg-surface-container-lowest p-10 rounded-xl shadow-[0_12px_40px_rgba(11,15,20,0.04)] border border-outline-variant/10 flex flex-col">
            <div className="mb-10">
              <h3 className="font-headline text-xl font-bold mb-2">ENTERPRISE</h3>
              <div className="flex items-baseline gap-1">
                <span className="text-4xl font-extrabold tracking-tight">Custom</span>
              </div>
            </div>
            <ul className="space-y-4 mb-12 flex-grow">
              <li className="flex items-center gap-3 text-sm text-secondary"><span className="text-primary">✓</span> ZK mode — content never leaves your system</li>
              <li className="flex items-center gap-3 text-sm text-secondary"><span className="text-primary">✓</span> SIEM export (Splunk / Datadog / Elastic)</li>
              <li className="flex items-center gap-3 text-sm text-secondary"><span className="text-primary">✓</span> On-prem deployment option</li>
              <li className="flex items-center gap-3 text-sm text-secondary"><span className="text-primary">✓</span> EU AI Act conformity declaration</li>
              <li className="flex items-center gap-3 text-sm text-secondary"><span className="text-primary">✓</span> Dedicated SLA + support</li>
            </ul>
            <a className="w-full py-4 font-bold bg-surface-container-highest text-on-surface rounded-md hover:bg-surface-dim transition-all text-center block" href="mailto:hello@sgraal.com">Contact Sales</a>
          </div>
        </div>
      </div>
    </section>
  );
}
