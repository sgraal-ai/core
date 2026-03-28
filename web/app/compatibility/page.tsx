export const metadata = {
  title: "Compatibility — Sgraal",
  description: "Sgraal works with 14 AI frameworks: LangChain, LlamaIndex, CrewAI, AutoGen, OpenAI, Mem0, Haystack, and more.",
};

const FRAMEWORKS = [
  { name: "LangChain", pkg: "sgraal", install: "pip install sgraal", status: "stable", type: "Python SDK" },
  { name: "LangGraph", pkg: "sgraal", install: "pip install sgraal", status: "stable", type: "Python SDK" },
  { name: "LlamaIndex", pkg: "sgraal", install: "pip install sgraal", status: "stable", type: "Python SDK" },
  { name: "CrewAI", pkg: "sgraal", install: "pip install sgraal", status: "stable", type: "Python SDK" },
  { name: "AutoGen", pkg: "sgraal", install: "pip install sgraal", status: "stable", type: "Python SDK" },
  { name: "OpenAI Agents SDK", pkg: "sgraal", install: "pip install sgraal", status: "stable", type: "Python SDK" },
  { name: "Mem0", pkg: "mem0-sgraal", install: "pip install mem0-sgraal", status: "stable", type: "Bridge" },
  { name: "Haystack", pkg: "sgraal", install: "pip install sgraal", status: "stable", type: "Python SDK" },
  { name: "Semantic Kernel", pkg: "sgraal", install: "pip install sgraal", status: "stable", type: "Python SDK" },
  { name: "Claude MCP", pkg: "@sgraal/mcp", install: "npm install @sgraal/mcp", status: "stable", type: "MCP Server" },
  { name: "Vercel AI SDK", pkg: "@sgraal/mcp", install: "npm install @sgraal/mcp", status: "stable", type: "Node.js" },
  { name: "n8n", pkg: "REST API", install: "curl -X POST https://api.sgraal.com/v1/preflight", status: "stable", type: "HTTP Node" },
  { name: "Dify", pkg: "REST API", install: "curl -X POST https://api.sgraal.com/v1/preflight", status: "stable", type: "HTTP Request" },
  { name: "Zapier", pkg: "REST API", install: "Use Webhooks by Zapier → POST to /v1/preflight", status: "beta", type: "Webhook" },
];

export default function CompatibilityPage() {
  return (
    <div className="max-w-4xl mx-auto py-16 px-6">
      <p className="text-gold font-mono text-sm tracking-widest uppercase mb-4">Compatibility</p>
      <h1 className="text-3xl sm:text-4xl font-bold mb-4">Works with your stack</h1>
      <p className="text-muted text-lg mb-10">
        Sgraal integrates with 14 AI frameworks via Python SDK, Node.js MCP server, or plain REST API.
        No vendor lock-in.
      </p>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-surface-light text-muted text-left">
              <th className="py-3 pr-4">Framework</th>
              <th className="py-3 pr-4">Status</th>
              <th className="py-3 pr-4">Type</th>
              <th className="py-3 pr-4">Package</th>
              <th className="py-3">Install</th>
            </tr>
          </thead>
          <tbody>
            {FRAMEWORKS.map((f) => (
              <tr key={f.name} className="border-b border-surface-light/50">
                <td className="py-3 pr-4 font-medium text-foreground">{f.name}</td>
                <td className="py-3 pr-4">
                  <span className={`text-xs px-2 py-0.5 rounded ${f.status === "stable" ? "bg-green-900 text-green-300" : "bg-yellow-900 text-yellow-300"}`}>
                    {f.status}
                  </span>
                </td>
                <td className="py-3 pr-4 text-muted">{f.type}</td>
                <td className="py-3 pr-4 font-mono text-gold text-xs">{f.pkg}</td>
                <td className="py-3 font-mono text-xs text-foreground/70">{f.install}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-10 border border-surface-light rounded-lg p-6">
        <h2 className="font-semibold text-foreground mb-2">Missing your framework?</h2>
        <p className="text-muted text-sm mb-3">
          Sgraal works with any system that can make an HTTP POST. The REST API is the universal integration path.
        </p>
        <pre className="bg-background border border-surface-light rounded p-3 text-sm font-mono text-foreground/80 overflow-x-auto">
{`curl -X POST https://api.sgraal.com/v1/preflight \\
  -H "Authorization: Bearer sg_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{"memory_state": [...]}'`}
        </pre>
      </div>
    </div>
  );
}
