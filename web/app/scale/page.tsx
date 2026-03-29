export const metadata = { title: "SCALE — Sgraal", description: "Self-improving thresholds, autonomous healing, 6 SDKs, 14 frameworks — Sgraal runs itself." };

const capabilities = [
  { title: "Learning & Calibration", description: "RL Q-table: every decision outcome improves thresholds. Meta-learning: cross-agent patterns. Calibrated thresholds per domain, action type, memory type. Weight export/import." },
  { title: "Autonomous Intelligence", description: "Predictive Health: first_block_day forecast 30 days ahead. Autonomous Immune: auto-heal after 3+ BLOCKs. Autonomous Rollback: wrong email → revoke. Autonomous Pruning: Shapley-weighted removal." },
  { title: "Integrations & SDKs", description: "Python SDK: async + sync, Pydantic v2. LangChain: pip install langchain-sgraal. MCP Server: npm install @sgraal/mcp — Claude Desktop, Cursor, Windsurf. Also: CrewAI · AutoGen · LlamaIndex · mem0 · CLI." },
];

const howSteps = [
  ["Every decision outcome trains the system", "Reinforcement learning records every outcome. Calibrated thresholds improve automatically."],
  ["The system heals itself", "Predictive health forecasts 30 days ahead. Autonomous heal triggers before problems surface."],
  ["Works inside any stack", "pip install sgraal · langchain-sgraal · @sgraal/mcp. Zero-config. 14 framework integrations."],
];

const S = {
  label: { fontFamily: "'Inter', sans-serif" as const, color: "var(--primary-container)", letterSpacing: "0.1em" } as const,
  h1: { fontFamily: "'Manrope', sans-serif" as const, fontWeight: 800 as const, color: "var(--on-surface)" } as const,
  desc: { color: "var(--on-surface-variant)" } as const,
  h2: { fontFamily: "'Manrope', sans-serif" as const, fontWeight: 700 as const, color: "var(--on-surface)" } as const,
  stepTitle: { fontWeight: 600 as const, color: "var(--on-surface)" } as const,
  card: { backgroundColor: "var(--surface-container-lowest)", boxShadow: "0 2px 12px rgba(11,15,20,0.06)" } as const,
  cardTitle: { fontFamily: "'Manrope', sans-serif" as const, fontWeight: 700 as const, color: "var(--primary-container)" } as const,
  code: { backgroundColor: "var(--obsidian)" } as const,
  codeText: { fontFamily: "'JetBrains Mono', monospace" as const, color: "#e2e8f0" } as const,
  cta: { background: "linear-gradient(135deg, #745b1c, #c9a962)", color: "#533d00", fontWeight: 600 as const } as const,
  step: { backgroundColor: "var(--primary-container)", color: "var(--on-primary-container)", fontFamily: "'Manrope', sans-serif" as const, fontWeight: 700 as const } as const,
};

export default function ScalePage() {
  return (
    <div className="max-w-4xl mx-auto py-16 px-6">
      <p className="text-xs uppercase tracking-widest mb-3" style={S.label}>SCALE</p>
      <h1 className="text-4xl sm:text-5xl mb-4" style={S.h1}>Learn, adapt, and grow autonomously.</h1>
      <p className="text-lg mb-12" style={S.desc}>Self-improving thresholds, autonomous healing, 6 SDKs, 14 frameworks — Sgraal runs itself so your agents can run anything.</p>
      <div className="py-10 px-6 -mx-6 mb-14 rounded-lg" style={{ backgroundColor: "var(--surface-container-low)" }}>
        <h2 className="text-xl mb-6" style={S.h2}>How it works</h2>
        <div className="space-y-6">
          {howSteps.map(([title, desc], i) => (
            <div key={i} className="flex gap-4">
              <span className="w-7 h-7 rounded-full flex items-center justify-center text-xs shrink-0 mt-0.5" style={S.step}>{i + 1}</span>
              <div><p className="mb-1" style={S.stepTitle}>{title}</p><p className="text-sm" style={S.desc}>{desc}</p></div>
            </div>
          ))}
        </div>
      </div>
      <h2 className="text-xl mb-6" style={S.h2}>Capabilities</h2>
      <div className="space-y-4 mb-14">
        {capabilities.map((c) => (
          <div key={c.title} className="rounded-lg p-6" style={S.card}>
            <p className="mb-2" style={S.cardTitle}>{c.title}</p>
            <p className="text-sm leading-relaxed" style={S.desc}>{c.description}</p>
          </div>
        ))}
      </div>
      <div className="rounded-lg p-6 mb-14" style={S.code}>
        <p className="text-xs mb-3" style={{ color: "rgba(255,255,255,0.5)" }}>Integration</p>
        <pre className="text-sm overflow-x-auto leading-relaxed" style={S.codeText}>{`pip install sgraal
pip install langchain-sgraal
npm install @sgraal/mcp

from sgraal import SgraalClient
client = SgraalClient(api_key="demo")
client.heal.autonomous(agent_id="agent_001")
client.truth.subscribe(
    source_url="https://api.fda.gov/drug/label.json",
    check_interval_hours=24
)`}</pre>
      </div>
      <div className="text-center">
        <p className="text-xl mb-4" style={S.h2}>Ready to scale?</p>
        <a href="https://app.sgraal.com" className="px-8 py-3 rounded-md transition inline-block" style={S.cta}>Get API Key</a>
      </div>
    </div>
  );
}
