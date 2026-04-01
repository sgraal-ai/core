"use client";

import { useState } from "react";

interface Template {
  id: string;
  title: string;
  description: string;
  language: string;
  category: string;
  code: string;
}

const TEMPLATES: Template[] = [
  {
    id: "python-basic", title: "Python — Basic Preflight", language: "python", category: "Getting Started",
    description: "Minimal preflight check before an agent action. Returns omega score and recommended action.",
    code: `from sgraal import SgraalClient

client = SgraalClient(api_key="sg_live_...")

result = client.preflight(
    memory_state=[{
        "id": "mem_001",
        "content": "User prefers dark mode",
        "type": "preference",
        "timestamp_age_days": 3,
        "source_trust": 0.95,
        "source_conflict": 0.05,
        "downstream_count": 2,
    }],
    action_type="read",
    domain="general",
)

if result.recommended_action == "BLOCK":
    print("Memory too risky — do not proceed")
else:
    print(f"Safe to act. Omega: {result.omega_mem_final}")`,
  },
  {
    id: "python-guard", title: "Python — @guard Decorator", language: "python", category: "Getting Started",
    description: "Wrap any function with automatic preflight checks. Blocks execution when memory is unreliable.",
    code: `from sgraal import SgraalClient, guard

client = SgraalClient(api_key="sg_live_...")

@guard(client, block_on=["BLOCK", "ASK_USER"])
def execute_trade(memory, amount):
    # This only runs if memory passes preflight
    return process_payment(amount)

# Raises SgraalBlockedError if memory is stale/conflicting
execute_trade(memory=my_memory, amount=12500)`,
  },
  {
    id: "ts-fetch", title: "TypeScript — Fetch API", language: "typescript", category: "Getting Started",
    description: "Direct HTTP call to the Sgraal API. Works in any Node.js or browser environment.",
    code: `const res = await fetch("https://api.sgraal.com/v1/preflight", {
  method: "POST",
  headers: {
    Authorization: "Bearer sg_live_...",
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    memory_state: [{
      id: "mem_001",
      content: "EUR/USD rate: 1.0821",
      type: "tool_state",
      timestamp_age_days: 8,
      source_trust: 0.6,
      source_conflict: 0.4,
      downstream_count: 5,
    }],
    action_type: "financial",
    domain: "fintech",
  }),
});

const { omega_mem_final, recommended_action } = await res.json();`,
  },
  {
    id: "langchain", title: "LangChain — Memory Guard", language: "typescript", category: "Integrations",
    description: "Add Sgraal as middleware in your LangChain pipeline. Intercepts tool calls with stale memory.",
    code: `import { createGuard } from "@sgraal/mcp";

const guard = createGuard({
  apiKey: process.env.SGRAAL_API_KEY,
  blockOn: ["BLOCK"],
  warnOn: ["WARN", "ASK_USER"],
});

const safeTool = guard.wrap(myTool, {
  domain: "fintech",
  actionType: "financial",
});

await safeTool.invoke({ query: "Execute trade" });`,
  },
  {
    id: "curl", title: "cURL — Quick Test", language: "bash", category: "Getting Started",
    description: "Test the API from your terminal. Great for debugging and exploration.",
    code: `curl -X POST https://api.sgraal.com/v1/preflight \\
  -H "Authorization: Bearer sg_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "memory_state": [{
      "id": "test_001",
      "content": "Test memory entry",
      "type": "semantic",
      "timestamp_age_days": 1,
      "source_trust": 0.9,
      "source_conflict": 0.1,
      "downstream_count": 3
    }],
    "action_type": "read",
    "domain": "general"
  }'`,
  },
  {
    id: "compliance", title: "EU AI Act — Compliance Check", language: "python", category: "Compliance",
    description: "Run preflight with EU AI Act compliance profile. Auto-blocks non-compliant irreversible actions.",
    code: `result = client.preflight(
    memory_state=[entry],
    action_type="irreversible",
    domain="medical",
    compliance_profile="EU_AI_ACT",
)

if result.compliance_result:
    for v in result.compliance_result.get("violations", []):
        print(f"Violation: {v['article']} — {v['description']}")`,
  },
];

const CATEGORIES = ["All", "Getting Started", "Integrations", "Compliance"];
const CARD: React.CSSProperties = { background: "#ffffff", borderRadius: "8px", boxShadow: "0 1px 3px rgba(0,0,0,0.06)", overflow: "hidden" };

export default function TemplatesPage() {
  const [category, setCategory] = useState("All");
  const [copied, setCopied] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);

  const filtered = category === "All" ? TEMPLATES : TEMPLATES.filter((t) => t.category === category);

  function copyCode(id: string, code: string) {
    navigator.clipboard.writeText(code);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Code Templates</h1>
      <p className="text-muted text-sm mb-6">Copy-paste integration snippets for Python, TypeScript, cURL, and more.</p>

      <div style={{ display: "flex", gap: "8px", marginBottom: "24px" }}>
        {CATEGORIES.map((c) => (
          <button key={c} onClick={() => setCategory(c)} style={{
            padding: "6px 16px", borderRadius: "20px", fontSize: "13px", fontWeight: 500, cursor: "pointer",
            background: category === c ? "#c9a962" : "transparent", color: category === c ? "#0B0F14" : "#6b7280",
            border: category === c ? "none" : "1px solid #e5e7eb",
          }}>{c}</button>
        ))}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
        {filtered.map((t) => (
          <div key={t.id} style={CARD}>
            <div style={{ padding: "20px 24px", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                  <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#0B0F14" }}>{t.title}</h3>
                  <span style={{ background: "rgba(201,169,98,0.1)", color: "#c9a962", borderRadius: "20px", padding: "2px 8px", fontSize: "11px" }}>{t.language}</span>
                </div>
                <p style={{ fontSize: "13px", color: "#6b7280" }}>{t.description}</p>
              </div>
              <div style={{ display: "flex", gap: "8px", marginLeft: "16px" }}>
                <button onClick={() => copyCode(t.id, t.code)} style={{ background: "#c9a962", color: "#0B0F14", fontWeight: 600, padding: "6px 16px", borderRadius: "6px", fontSize: "13px", border: "none", cursor: "pointer" }}>
                  {copied === t.id ? "Copied!" : "Copy"}
                </button>
                <button onClick={() => setExpanded(expanded === t.id ? null : t.id)} style={{ padding: "6px 16px", borderRadius: "6px", fontSize: "13px", border: "1px solid #e5e7eb", cursor: "pointer", background: "transparent", color: "#6b7280" }}>
                  {expanded === t.id ? "Hide" : "View"}
                </button>
              </div>
            </div>
            {expanded === t.id && (
              <pre style={{ background: "#0B0F14", color: "#e2e8f0", padding: "20px 24px", fontSize: "13px", fontFamily: "monospace", lineHeight: 1.6, overflowX: "auto", margin: 0, borderTop: "1px solid #e5e7eb" }}>
                {t.code}
              </pre>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
