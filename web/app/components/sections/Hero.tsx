export function Hero() {
  const responseCode = `{
  "omega_mem_final": 78.4,
  "recommended_action": "BLOCK",
  "repair_plan": [{
    "action": "REFETCH",
    "entry_id": "mem_payment_history",
    "reason": "Memory is stale (freshness=89/100)"
  }]
}`;

  return (
    <section className="px-6 pt-16 pb-12 max-w-5xl mx-auto text-center">
      <p className="text-gold font-mono text-sm tracking-widest uppercase mb-3">
        Memory Governance Protocol
      </p>
      <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold leading-tight mb-6 max-w-4xl mx-auto">
        AI agents act on memory. Sgraal decides if that memory is{" "}
        <span className="text-gold">safe to act on.</span>
      </h1>
      <p className="text-muted text-lg sm:text-xl mb-8 max-w-2xl mx-auto">
        The memory governance protocol between AI agent memory and AI agent action.
      </p>
      <div className="flex flex-wrap justify-center gap-4 mb-12">
        <a href="/playground" className="bg-gold text-background font-semibold px-8 py-3 rounded-lg hover:bg-gold-dim transition text-base">
          Try it now — no signup
        </a>
        <a href="https://api.sgraal.com/docs" className="border border-foreground/30 text-foreground font-semibold px-8 py-3 rounded-lg hover:bg-foreground/5 transition text-base">
          Read the docs
        </a>
      </div>

      <div className="max-w-[720px] mx-auto text-left">
        <div className="bg-surface border border-surface-light rounded-xl overflow-hidden">
          <div className="px-4 py-2 border-b border-surface-light flex items-center gap-2">
            <span className="font-mono text-xs text-muted">POST /v1/preflight</span>
          </div>
          <pre className="p-4 text-sm font-mono text-foreground/80 overflow-x-auto leading-relaxed">{`{
  "memory_state": [{
    "id": "mem_payment_history",
    "type": "tool_state",
    "timestamp_age_days": 54,
    "source_trust": 0.6,
    "source_conflict": 0.4
  }],
  "action_type": "irreversible",
  "domain": "fintech"
}`}</pre>
        </div>
        <div className="mt-3 bg-surface border border-red-400/30 rounded-xl overflow-hidden">
          <div className="px-4 py-2 border-b border-surface-light flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-red-400" />
            <span className="font-mono text-xs text-red-400">BLOCK</span>
          </div>
          <pre className="p-4 text-sm font-mono text-foreground/80 overflow-x-auto leading-relaxed">{responseCode}</pre>
        </div>
      </div>
    </section>
  );
}
