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

export default function ScalePage() {
  return (
    <div style={{ backgroundColor: "#ffffff" }}>
      <div className="max-w-7xl mx-auto px-8 md:px-16 py-20">
        <p className="font-bold tracking-widest text-xs uppercase mb-4" style={{ color: "#c9a962" }}>SCALE</p>
        <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-black mb-4" style={{ fontFamily: "'Manrope', sans-serif" }}>Learn, adapt, and grow autonomously.</h1>
        <p className="text-lg mb-16 text-gray-500">Self-improving thresholds, autonomous healing, 6 SDKs, 14 frameworks — Sgraal runs itself so your agents can run anything.</p>
      </div>
      <div style={{ backgroundColor: "#f9f9f9" }} className="px-8 py-20">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold text-black mb-10" style={{ fontFamily: "'Manrope', sans-serif" }}>How it works</h2>
          <div className="space-y-8">
            {howSteps.map(([title, desc], i) => (
              <div key={i} className="flex gap-5">
                <span className="w-14 h-14 rounded-full flex items-center justify-center text-2xl font-bold shrink-0" style={{ border: "2px solid #c9a962", color: "#745b1c", backgroundColor: "#f9f9f9" }}>{i + 1}</span>
                <div><p className="font-bold text-black mb-1">{title}</p><p className="text-sm text-gray-500">{desc}</p></div>
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="max-w-7xl mx-auto px-8 md:px-16 py-20">
        <h2 className="text-2xl font-bold text-black mb-10" style={{ fontFamily: "'Manrope', sans-serif" }}>Capabilities</h2>
        <div className="space-y-6">
          {capabilities.map((c) => (
            <div key={c.title} className="p-8 rounded-xl" style={{ backgroundColor: "#ffffff", boxShadow: "0 4px 24px rgba(11,15,20,0.08)", border: "1px solid rgba(208,197,180,0.2)" }}>
              <p className="font-bold mb-2" style={{ color: "#c9a962", fontFamily: "'Manrope', sans-serif" }}>{c.title}</p>
              <p className="text-sm leading-relaxed text-gray-500">{c.description}</p>
            </div>
          ))}
        </div>
      </div>
      <div className="max-w-7xl mx-auto px-8 md:px-16 pb-8">
        <div className="rounded-xl p-8" style={{ backgroundColor: "#0b0f14" }}>
          <p className="text-xs mb-4" style={{ color: "#6b6b6b" }}>Integration</p>
          <pre className="text-sm overflow-x-auto leading-relaxed" style={{ color: "#e2e8f0", backgroundColor: "#0b0f14" }}>{`pip install sgraal
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
      </div>
      <div className="px-8 md:px-16 py-20 text-center" style={{ backgroundColor: "#f9f9f9" }}>
        <p className="text-2xl font-bold text-black mb-6" style={{ fontFamily: "'Manrope', sans-serif" }}>Ready to scale?</p>
        <a href="https://app.sgraal.com" className="px-8 py-4 text-lg font-bold text-white rounded-md inline-block" style={{ background: "linear-gradient(135deg, #745b1c, #c9a962)" }}>Get API Key</a>
      </div>
    </div>
  );
}
