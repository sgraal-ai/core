export const metadata = { title: "SCALE — Sgraal", description: "Self-improving thresholds, autonomous healing, 6 SDKs, 14 frameworks — Sgraal runs itself so your agents can run anything." };

const capabilities = [
  { title: "Learning & Calibration", description: "RL Q-table: every decision outcome improves future thresholds. Meta-learning: cross-agent pattern recognition. Calibrated thresholds: per domain, per action type, per memory type. Weight export/import for reproducibility." },
  { title: "Autonomous Intelligence", description: "Predictive Memory Health Score: ‘first_block_day in 18 days — 73% probability.’ Autonomous Immune System: auto-heal triggered after 3+ BLOCKs in one hour. Autonomous Rollback: wrong email → revoke, wrong trade → compensation workflow. Autonomous Pruning: Shapley-weighted removal of low-relevance entries." },
  { title: "Integrations & SDKs", description: "Python SDK (sgraal-py): async + sync, Pydantic v2, MemoryBuilder helper. LangChain: pip install langchain-sgraal — SgraalMemoryValidator middleware. MCP Server: npm install @sgraal/mcp — Claude Desktop, Cursor, Windsurf compatible. Also: CrewAI · AutoGen · LlamaIndex · mem0 · CLI · Zero-config embed · Universal adapter." },
];

export default function ScalePage() {
  return (
    <div className="max-w-4xl mx-auto py-16 px-6">
      <p className="text-gold font-mono text-sm tracking-widest uppercase mb-3">SCALE</p>
      <h1 className="text-4xl sm:text-5xl font-bold mb-4">Learn, adapt, and grow autonomously.</h1>
      <p className="text-muted text-lg mb-12">Self-improving thresholds, autonomous healing, 6 SDKs, 14 frameworks — Sgraal runs itself so your agents can run anything.</p>

      <h2 className="text-xl font-semibold mb-6">How it works</h2>
      <div className="space-y-6 mb-14">
        {[
          ["Every decision outcome trains the system", "Reinforcement learning records every preflight outcome. Calibrated thresholds improve automatically. The system gets more accurate with every call."],
          ["The system heals itself", "Predictive health forecasts first_block_day 30 days ahead. Autonomous heal triggers before problems surface. Truth Subscription invalidates stale memory when authoritative sources change."],
          ["Works inside any stack", "pip install sgraal · pip install langchain-sgraal · npm install @sgraal/mcp. Zero-config embed. Universal adapter. 14 framework integrations."],
        ].map(([title, desc], i) => (
          <div key={i} className="flex gap-4">
            <span className="w-7 h-7 rounded-full bg-gold text-background flex items-center justify-center font-mono font-bold text-xs shrink-0 mt-0.5">{i + 1}</span>
            <div><p className="font-semibold text-foreground mb-1">{title}</p><p className="text-muted text-sm">{desc}</p></div>
          </div>
        ))}
      </div>

      <h2 className="text-xl font-semibold mb-6">Capabilities</h2>
      <div className="space-y-4 mb-14">
        {capabilities.map((c) => (
          <div key={c.title} className="border border-surface-light bg-surface rounded-xl p-6">
            <p className="font-semibold text-gold mb-2">{c.title}</p>
            <p className="text-muted text-sm leading-relaxed">{c.description}</p>
          </div>
        ))}
      </div>

      <div className="bg-surface border border-surface-light rounded-xl p-6 mb-14">
        <p className="font-mono text-xs text-muted mb-3">Integration</p>
        <pre className="text-sm font-mono text-foreground/80 overflow-x-auto leading-relaxed">{`pip install sgraal
pip install langchain-sgraal
npm install @sgraal/mcp`}</pre>
        <pre className="text-sm font-mono text-foreground/80 overflow-x-auto leading-relaxed mt-4">{`# Full autonomous setup
from sgraal import SgraalClient

client = SgraalClient(api_key="demo")

# Enable autonomous healing
client.heal.autonomous(
    agent_id="agent_001",
    strategy="conservative"
)

# Subscribe to truth source
client.truth.subscribe(
    source_url="https://api.fda.gov/drug/label.json",
    affected_namespace="healthcare",
    check_interval_hours=24
)`}</pre>
      </div>

      <div className="text-center">
        <p className="text-xl font-semibold mb-4">Ready to scale?</p>
        <a href="https://app.sgraal.com" className="bg-gold text-background font-semibold px-8 py-3 rounded-lg hover:bg-gold-dim transition inline-block">Get API Key</a>
      </div>
    </div>
  );
}
