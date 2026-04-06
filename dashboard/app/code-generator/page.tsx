"use client";
import { useState, useMemo } from "react";
import { getApiKey, getApiUrl, setApiKey as saveApiKey, setApiUrl as saveApiUrl, removeApiKey, removeApiUrl, getItem, setItem, removeItem } from "../lib/storage";

const FRAMEWORKS = ["Python (requests)", "Python (sgraal)", "Node.js", "LangChain", "LangGraph", "CrewAI", "AutoGen", "Vercel AI", "Claude MCP", "Vanilla JS"] as const;
type Framework = typeof FRAMEWORKS[number];

const DOMAINS = ["general", "fintech", "medical", "legal", "coding"] as const;
const ACTIONS = ["reversible", "irreversible", "destructive"] as const;

const DOMAIN_ENTRIES: Record<string, { content: string; type: string; age: number; trust: number; conflict: number; downstream: number }[]> = {
  fintech: [
    { content: "Account balance: $50,000", type: "tool_state", age: 3, trust: 0.92, conflict: 0.08, downstream: 5 },
    { content: "Transfer approval limit: $25,000", type: "policy", age: 10, trust: 0.88, conflict: 0.12, downstream: 3 },
    { content: "KYC verified 2025-11-10", type: "semantic", age: 45, trust: 0.95, conflict: 0.05, downstream: 2 },
    { content: "Portfolio risk rating: moderate", type: "semantic", age: 7, trust: 0.85, conflict: 0.15, downstream: 4 },
    { content: "Last transaction: wire transfer $12,000 on 2025-12-20", type: "episodic", age: 14, trust: 0.90, conflict: 0.10, downstream: 1 },
  ],
  legal: [
    { content: "Liability clause §7.2 capped at €500K", type: "semantic", age: 30, trust: 0.85, conflict: 0.15, downstream: 4 },
    { content: "Contract renewal deadline: 2026-06-01", type: "tool_state", age: 5, trust: 0.95, conflict: 0.05, downstream: 3 },
    { content: "Governing law: EU", type: "policy", age: 60, trust: 0.90, conflict: 0.10, downstream: 6 },
    { content: "Data processing agreement signed 2025-09-01", type: "semantic", age: 90, trust: 0.80, conflict: 0.20, downstream: 2 },
    { content: "Non-compete clause: 12 months post-termination", type: "semantic", age: 45, trust: 0.88, conflict: 0.12, downstream: 3 },
  ],
  medical: [
    { content: "Patient allergies: penicillin", type: "semantic", age: 5, trust: 0.95, conflict: 0.05, downstream: 8 },
    { content: "Last checkup: 2025-09-15", type: "tool_state", age: 120, trust: 0.80, conflict: 0.20, downstream: 3 },
    { content: "DrugX dosage: 10mg daily", type: "policy", age: 15, trust: 0.90, conflict: 0.10, downstream: 5 },
    { content: "Blood pressure: 130/85 mmHg", type: "tool_state", age: 30, trust: 0.85, conflict: 0.15, downstream: 2 },
    { content: "Family history: type 2 diabetes", type: "semantic", age: 200, trust: 0.92, conflict: 0.08, downstream: 1 },
  ],
  coding: [
    { content: "Use React for all frontend", type: "policy", age: 10, trust: 0.90, conflict: 0.10, downstream: 3 },
    { content: "API rate limit: 1000/min", type: "tool_state", age: 2, trust: 0.95, conflict: 0.05, downstream: 5 },
    { content: "Database: PostgreSQL 16", type: "semantic", age: 30, trust: 0.92, conflict: 0.08, downstream: 4 },
    { content: "CI pipeline: pytest with 80% coverage gate", type: "policy", age: 15, trust: 0.88, conflict: 0.12, downstream: 2 },
    { content: "Docker images tagged with git SHA", type: "tool_state", age: 5, trust: 0.93, conflict: 0.07, downstream: 3 },
  ],
  general: [
    { content: "User preference: email notifications", type: "preference", age: 20, trust: 0.90, conflict: 0.10, downstream: 2 },
    { content: "Last login: 2025-12-01", type: "tool_state", age: 30, trust: 0.85, conflict: 0.15, downstream: 1 },
    { content: "Account tier: pro", type: "semantic", age: 60, trust: 0.92, conflict: 0.08, downstream: 3 },
    { content: "Language: English", type: "preference", age: 90, trust: 0.95, conflict: 0.05, downstream: 1 },
    { content: "Timezone: UTC+1", type: "preference", age: 45, trust: 0.93, conflict: 0.07, downstream: 1 },
  ],
};

function generateEntry(i: number, domain: string) {
  const pool = DOMAIN_ENTRIES[domain] ?? DOMAIN_ENTRIES.general;
  const e = pool[(i - 1) % pool.length];
  return `  {"id": "mem_${String(i).padStart(3, "0")}", "content": "${e.content}", "type": "${e.type}", "timestamp_age_days": ${e.age}, "source_trust": ${e.trust}, "source_conflict": ${e.conflict}, "downstream_count": ${e.downstream}}`;
}

function gen(fw: Framework, domain: string, action: string, entries: number, heal: boolean, _batch: boolean): string {
  const e = Array.from({ length: entries }, (_, i) => generateEntry(i + 1, domain)).join(",\n");
  const comment = "# Keep your API key secret — never commit it to source control";

  if (fw === "Python (requests)") {
    let code = `${comment}\nimport os\nimport requests\n\nAPI_KEY = os.environ.get("SGRAAL_API_KEY", "sg_live_...")  # Set env var: export SGRAAL_API_KEY=your_key\n\nresp = requests.post(\n  "https://api.sgraal.com/v1/preflight",\n  headers={"Authorization": f"Bearer {API_KEY}"},\n  json={\n    "memory_state": [\n${e}\n    ],\n    "domain": "${domain}",\n    "action_type": "${action}"\n  }\n)\nresult = resp.json()\n\n# Handle decision\naction = result.get("recommended_action")\n\nif action == "BLOCK":\n    raise RuntimeError(f"Sgraal blocked execution: omega={result.get('omega_mem_final')}")\nelif action == "WARN":\n    print(f"Warning: proceed with caution. Omega={result.get('omega_mem_final')}")\nelif action == "ASK_USER":\n    print("Human approval required before proceeding.")\nelse:\n    print(f"Safe to proceed. Omega={result.get('omega_mem_final')}")`;
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

  const apiKey = getApiKey();

  const copyCode = () => {
    // Insert real key only into clipboard, never in DOM
    const withKey = apiKey ? code.replace(/sg_live_\.\.\./g, apiKey) : code;
    try { navigator.clipboard.writeText(withKey); } catch {}
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
          <div>
            <label className="text-xs text-muted flex items-center gap-1">
              <input type="checkbox" checked={heal} onChange={e => setHeal(e.target.checked)} /> Heal
            </label>
            {heal && <p style={{ fontSize: "10px", color: "#6b7280", fontStyle: "italic", marginTop: "2px" }}>Repair plan for blocked memory: DELETE/REFRESH/VERIFY per entry.</p>}
          </div>
          <div>
            <label className="text-xs text-muted flex items-center gap-1">
              <input type="checkbox" checked={batch} onChange={e => setBatch(e.target.checked)} /> Batch
            </label>
            {batch && <p style={{ fontSize: "10px", color: "#6b7280", fontStyle: "italic", marginTop: "2px" }}>Validate up to 500 entries in one call. Returns portfolio_risk.</p>}
          </div>
        </div>
      </div>

      {/* Auth warning */}
      <p style={{ fontSize: "11px", color: "#a16207", marginBottom: "8px" }}>
        &#x26A0;&#xFE0F; Never hardcode API keys in source code. Use environment variables: <code style={{ fontFamily: "monospace" }}>os.environ[&apos;SGRAAL_API_KEY&apos;]</code> or <code style={{ fontFamily: "monospace" }}>process.env.SGRAAL_API_KEY</code>
      </p>

      {/* What this code does */}
      <div style={{ fontSize: "13px", color: "#6b7280", marginBottom: "12px", lineHeight: 1.6 }}>
        <p>1. Sends your memory state to Sgraal for preflight validation.</p>
        <p>2. Returns USE_MEMORY / WARN / ASK_USER / BLOCK with full explanation.</p>
        <p>3. Act on the decision: block the action, request human approval, or proceed safely.</p>
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
