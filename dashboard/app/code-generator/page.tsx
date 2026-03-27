"use client";
import { useState, useMemo } from "react";

const FRAMEWORKS = ["Python (requests)", "Python (sgraal)", "Node.js", "LangChain", "LangGraph", "CrewAI", "AutoGen", "Vercel AI", "Claude MCP", "Vanilla JS"] as const;
type Framework = typeof FRAMEWORKS[number];

const DOMAINS = ["general", "fintech", "medical", "legal"] as const;
const ACTIONS = ["reversible", "irreversible", "destructive"] as const;

function generateEntry(i: number) {
  return `  {"id": "mem_${String(i).padStart(3, "0")}", "content": "Memory entry ${i}", "type": "semantic", "timestamp_age_days": ${i * 5}, "source_trust": 0.9, "source_conflict": 0.1, "downstream_count": ${i}}`;
}

function gen(fw: Framework, domain: string, action: string, entries: number, heal: boolean, _batch: boolean): string {
  const e = Array.from({ length: entries }, (_, i) => generateEntry(i + 1)).join(",\n");
  const comment = "# Keep your API key secret — never commit it to source control";

  if (fw === "Python (requests)") {
    let code = `${comment}\nimport requests\n\nAPI_KEY = "sg_live_..."  # Replace with your key\n\nresp = requests.post(\n  "https://api.sgraal.com/v1/preflight",\n  headers={"Authorization": f"Bearer {API_KEY}"},\n  json={\n    "memory_state": [\n${e}\n    ],\n    "domain": "${domain}",\n    "action_type": "${action}"\n  }\n)\nresult = resp.json()\nprint(f"Action: {result['recommended_action']}, Omega: {result['omega_mem_final']}")`;
    if (heal) code += `\n\n# Heal a blocked entry\nif result["recommended_action"] == "BLOCK":\n    for repair in result["repair_plan"]:\n        requests.post("https://api.sgraal.com/v1/heal",\n            headers={"Authorization": f"Bearer {API_KEY}"},\n            json={"entry_id": repair["entry_id"], "action": repair["action"]})`;
    return code;
  }
  if (fw === "Python (sgraal)") {
    return `${comment}\nfrom sgraal import SgraalClient\n\nclient = SgraalClient(api_key="sg_live_...")\nresult = client.preflight([\n${e}\n], domain="${domain}", action_type="${action}")\nprint(result.recommended_action, result.omega_mem_final)`;
  }
  if (fw === "Node.js") {
    return `// Keep your API key secret\nconst resp = await fetch("https://api.sgraal.com/v1/preflight", {\n  method: "POST",\n  headers: { Authorization: "Bearer sg_live_...", "Content-Type": "application/json" },\n  body: JSON.stringify({\n    memory_state: [\n${e}\n    ],\n    domain: "${domain}", action_type: "${action}"\n  })\n});\nconst result = await resp.json();\nconsole.log(result.recommended_action, result.omega_mem_final);`;
  }
  if (fw === "LangChain") {
    return `${comment}\nfrom langchain_sgraal import SgraalMemoryGuard\n\nguard = SgraalMemoryGuard(api_key="sg_live_...")\nresult = guard.invoke({"memory_state": [\n${e}\n], "domain": "${domain}"})`;
  }
  if (fw === "Claude MCP") {
    return `// claude_desktop_config.json\n{\n  "mcpServers": {\n    "sgraal": {\n      "command": "npx",\n      "args": ["@sgraal/mcp"],\n      "env": { "SGRAAL_API_KEY": "sg_live_..." }\n    }\n  }\n}`;
  }
  if (fw === "Vanilla JS") {
    return `<!-- Keep your API key secret -->\n<script src="https://sgraal.com/sgraal.auto.js" data-api-key="sg_live_..."></script>\n<script>\n  const result = await sgraal.preflight([\n${e}\n  ], { domain: "${domain}", actionType: "${action}" });\n  console.log(result.recommended_action);\n</script>`;
  }
  return `// ${fw} integration — see docs at sgraal.com/docs\n// API key: sg_live_...\n// Domain: ${domain}, Action: ${action}`;
}

export default function CodeGeneratorPage() {
  const [fw, setFw] = useState<Framework>("Python (requests)");
  const [domain, setDomain] = useState("fintech");
  const [action, setAction] = useState("irreversible");
  const [entries, setEntries] = useState(3);
  const [heal, setHeal] = useState(false);
  const [batch, setBatch] = useState(false);
  const [copied, setCopied] = useState(false);

  const code = useMemo(() => gen(fw, domain, action, entries, heal, batch), [fw, domain, action, entries, heal, batch]);

  const apiKey = typeof window !== "undefined" ? localStorage.getItem("sgraal_api_key") || "" : "";

  const copyCode = () => {
    // Insert real key only into clipboard, never in DOM
    const withKey = apiKey ? code.replace(/sg_live_\.\.\./g, apiKey) : code;
    navigator.clipboard.writeText(withKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Code Generator</h1>
      <p className="text-muted text-sm mb-6">Generate working Sgraal integration code for your framework.</p>

      <div className="flex flex-wrap gap-2 mb-6">
        {FRAMEWORKS.map(f => (
          <button key={f} onClick={() => setFw(f)} className={`text-xs px-3 py-1.5 rounded border ${fw === f ? "bg-gold text-background border-gold" : "bg-surface border-surface-light text-muted"}`}>
            {f}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        <div>
          <label className="text-xs text-muted block mb-1">Domain</label>
          <select value={domain} onChange={e => setDomain(e.target.value)} className="bg-surface border border-surface-light rounded px-3 py-2 text-sm w-full">
            {DOMAINS.map(d => <option key={d} value={d}>{d}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs text-muted block mb-1">Action</label>
          <select value={action} onChange={e => setAction(e.target.value)} className="bg-surface border border-surface-light rounded px-3 py-2 text-sm w-full">
            {ACTIONS.map(a => <option key={a} value={a}>{a}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs text-muted block mb-1">Entries</label>
          <select value={entries} onChange={e => setEntries(+e.target.value)} className="bg-surface border border-surface-light rounded px-3 py-2 text-sm w-full">
            {[1, 3, 5].map(n => <option key={n} value={n}>{n}</option>)}
          </select>
        </div>
        <div className="flex items-end gap-4">
          <label className="text-xs text-muted flex items-center gap-1">
            <input type="checkbox" checked={heal} onChange={e => setHeal(e.target.checked)} /> Heal
          </label>
          <label className="text-xs text-muted flex items-center gap-1">
            <input type="checkbox" checked={batch} onChange={e => setBatch(e.target.checked)} /> Batch
          </label>
        </div>
      </div>

      <div className="relative">
        <button onClick={copyCode} className="absolute top-3 right-3 text-xs bg-gold text-background px-3 py-1 rounded font-semibold hover:bg-gold-dim transition z-10">
          {copied ? "Copied!" : "Copy"}
        </button>
        <pre className="bg-surface border border-surface-light rounded-xl p-5 text-xs font-mono text-foreground/80 overflow-x-auto max-h-96 overflow-y-auto whitespace-pre-wrap">
          {code}
        </pre>
      </div>

      <div className="mt-4 flex gap-3">
        <a href="https://sgraal.com/playground" className="text-xs text-gold hover:underline">Run in Playground →</a>
        <a href="https://api.sgraal.com/docs/postman" className="text-xs text-muted hover:underline">Postman Collection →</a>
      </div>
    </div>
  );
}
