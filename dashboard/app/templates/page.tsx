"use client";

import { useState, useEffect, useRef } from "react";

interface Template {
  id: string;
  title: string;
  description: string;
  language: string;
  category: string;
  maturity: "starter" | "production" | "advanced";
  code: string;
}

const MATURITY_BADGE: Record<string, { bg: string; color: string; label: string }> = {
  starter: { bg: "#dcfce7", color: "#166534", label: "Starter" },
  production: { bg: "#dbeafe", color: "#1e40af", label: "Production" },
  advanced: { bg: "#f3e8ff", color: "#6b21a8", label: "Advanced" },
};

const TEMPLATES: Template[] = [
  {
    id: "python-basic", title: "Python — Basic Preflight", language: "python", category: "Getting Started", maturity: "starter",
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
    id: "python-guard", title: "Python — @guard Decorator", language: "python", category: "Production Patterns", maturity: "production",
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
    id: "ts-fetch", title: "TypeScript — Fetch API", language: "typescript", category: "Getting Started", maturity: "starter",
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
    action_type: "irreversible",
    domain: "fintech",
  }),
});

const { omega_mem_final, recommended_action } = await res.json();`,
  },
  {
    id: "langchain", title: "LangChain — Memory Guard", language: "typescript", category: "Production Patterns", maturity: "production",
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
    id: "curl", title: "cURL — Quick Test", language: "bash", category: "Getting Started", maturity: "starter",
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
    id: "compliance", title: "EU AI Act — Compliance Check", language: "python", category: "Production Patterns", maturity: "production",
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
  {
    id: "langchain-memory", title: "LangChain Memory Guard", language: "python", category: "Production Patterns", maturity: "production",
    description: "Wrap LangChain memory with Sgraal preflight validation.",
    code: `import os
from langchain.memory import ConversationBufferMemory
from sgraal import SgraalClient

client = SgraalClient(api_key=os.environ["SGRAAL_API_KEY"])
memory = ConversationBufferMemory()

def safe_recall(query: str) -> str:
    entries = memory.load_memory_variables({})
    result = client.preflight(
        memory_state=[{"content": v, "type": "semantic",
                       "timestamp_age_days": 1, "source_trust": 0.9}
                      for v in entries.values()],
        action_type="reversible", domain="general"
    )
    if result["recommended_action"] == "BLOCK":
        return "[Memory blocked by Sgraal — unsafe to recall]"
    return query`,
  },
  {
    id: "langgraph", title: "LangGraph Agent Guard", language: "python", category: "Advanced / Multi-Agent", maturity: "advanced",
    description: "Validate memory state before each LangGraph node fires.",
    code: `import os
from sgraal import SgraalClient

client = SgraalClient(api_key=os.environ["SGRAAL_API_KEY"])

def preflight_node(state: dict) -> dict:
    \"\"\"Guard node — runs before any tool or LLM call.\"\"\"
    result = client.preflight(
        memory_state=state.get("memory", []),
        action_type="irreversible", domain="fintech"
    )
    if result["recommended_action"] == "BLOCK":
        raise RuntimeError(f"Sgraal blocked: omega={result['omega_mem_final']}")
    state["sgraal_decision"] = result["recommended_action"]
    return state`,
  },
  {
    id: "crewai", title: "CrewAI Memory Validation", language: "python", category: "Production Patterns", maturity: "production",
    description: "Guard CrewAI agent memory before task execution.",
    code: `import os
from crewai import Task
from sgraal import SgraalClient

client = SgraalClient(api_key=os.environ["SGRAAL_API_KEY"])

def guarded_task(agent, description: str, memory: list) -> Task:
    result = client.preflight(
        memory_state=memory,
        action_type="reversible", domain="general"
    )
    if result["recommended_action"] in ("BLOCK", "ASK_USER"):
        print(f"Task blocked: omega={result['omega_mem_final']}")
        return None
    return Task(description=description, agent=agent)`,
  },
  {
    id: "autogen", title: "AutoGen Safe Memory", language: "python", category: "Advanced / Multi-Agent", maturity: "advanced",
    description: "Intercept AutoGen memory reads with Sgraal validation.",
    code: `import os
from sgraal import SgraalClient

client = SgraalClient(api_key=os.environ["SGRAAL_API_KEY"])

def safe_memory_hook(memory_entries: list, agent_name: str) -> list:
    \"\"\"Called before AutoGen agent reads memory.\"\"\"
    result = client.preflight(
        memory_state=memory_entries,
        action_type="irreversible",
        domain="coding"
    )
    action = result["recommended_action"]
    if action == "BLOCK":
        print(f"[{agent_name}] Memory blocked — omega={result['omega_mem_final']}")
        return []  # Return empty, agent proceeds without memory
    return memory_entries`,
  },
  {
    id: "async-python", title: "Async Python Preflight", language: "python", category: "Production Patterns", maturity: "production",
    description: "Non-blocking preflight for high-throughput async agent pipelines.",
    code: `import asyncio, aiohttp, os

async def preflight_async(memory_state: list) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.sgraal.com/v1/preflight",
            headers={"Authorization": f"Bearer {os.environ['SGRAAL_API_KEY']}"},
            json={"memory_state": memory_state,
                  "action_type": "irreversible", "domain": "fintech"}
        ) as resp:
            return await resp.json()

async def main():
    result = await preflight_async([
        {"id": "mem_001", "content": "Account balance: $50,000",
         "type": "tool_state", "timestamp_age_days": 3, "source_trust": 0.92}
    ])
    print(result["recommended_action"])

asyncio.run(main())`,
  },
  {
    id: "llamaindex", title: "LlamaIndex Memory Guard", language: "python", category: "Production Patterns", maturity: "production",
    description: "Validate LlamaIndex retrieved nodes with Sgraal before passing to the query engine.",
    code: `import os
from llama_index.core import VectorStoreIndex
from sgraal import SgraalClient

client = SgraalClient(api_key=os.environ["SGRAAL_API_KEY"])

def safe_query(index: VectorStoreIndex, query: str) -> str:
    nodes = index.as_retriever().retrieve(query)
    memory_state = [
        {"id": f"node_{i}", "content": node.text, "type": "semantic",
         "timestamp_age_days": 7, "source_trust": node.score or 0.8}
        for i, node in enumerate(nodes)
    ]
    result = client.preflight(
        memory_state=memory_state,
        action_type="reversible", domain="general"
    )
    if result["recommended_action"] == "BLOCK":
        return "[Blocked by Sgraal — retrieved context is unsafe]"
    return str(index.as_query_engine().query(query))`,
  },
];

const CATEGORIES = ["All", "Getting Started", "Production Patterns", "Advanced / Multi-Agent"];
const CARD: React.CSSProperties = { background: "#ffffff", borderRadius: "8px", boxShadow: "0 1px 3px rgba(0,0,0,0.06)", overflow: "hidden" };

export default function TemplatesPage() {
  const [category, setCategory] = useState("All");
  const [copied, setCopied] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => setDebouncedSearch(search), 300);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [search]);

  const filtered = TEMPLATES.filter((t) => {
    if (category !== "All" && t.category !== category) return false;
    if (debouncedSearch) {
      const q = debouncedSearch.toLowerCase();
      if (!t.title.toLowerCase().includes(q) && !t.description.toLowerCase().includes(q) && !t.language.toLowerCase().includes(q) && !t.category.toLowerCase().includes(q)) return false;
    }
    return true;
  });

  function copyCode(id: string, code: string) {
    try { navigator.clipboard.writeText(code); } catch {}
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Code Templates</h1>
      <p className="text-muted text-sm mb-6">Copy-paste integration snippets for Python, TypeScript, cURL, and more.</p>

      <div style={{ position: "relative", marginBottom: "16px" }}>
        <input type="text" placeholder="Search templates..." value={search} onChange={e => setSearch(e.target.value)}
          style={{ width: "100%", maxWidth: "360px", background: "#ffffff", border: "1px solid #e5e7eb", borderRadius: "6px", padding: "8px 32px 8px 12px", fontSize: "14px", color: "#0B0F14" }} />
        {search && <button onClick={() => setSearch("")} style={{ position: "absolute", left: "332px", top: "50%", transform: "translateY(-50%)", background: "none", border: "none", cursor: "pointer", fontSize: "16px", color: "#6b7280" }} aria-label="Clear search">&times;</button>}
      </div>

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
        {filtered.length === 0 && <p style={{ textAlign: "center", color: "#6b7280", padding: "40px 0", fontSize: "14px" }}>No templates found.</p>}
        {filtered.map((t) => (
          <div key={t.id} style={{ ...CARD, position: "relative" }}>
            {(() => { const m = MATURITY_BADGE[t.maturity]; return m ? <span style={{ position: "absolute", top: "12px", right: "12px", background: m.bg, color: m.color, borderRadius: "4px", padding: "1px 8px", fontSize: "10px", fontWeight: 600 }}>{m.label}</span> : null; })()}
            <div style={{ padding: "20px 24px", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                  <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#0B0F14" }}>{t.title}</h3>
                  <span style={{ background: "rgba(201,169,98,0.1)", color: "#c9a962", borderRadius: "20px", padding: "2px 8px", fontSize: "11px" }}>{t.language}</span>
                  {t.id === "python-basic" && <span style={{ background: "#16a34a", color: "#ffffff", borderRadius: "4px", padding: "2px 8px", fontSize: "11px", fontWeight: 600 }}>Start here</span>}
                </div>
                <p style={{ fontSize: "13px", color: "#6b7280" }}>{t.description}</p>
                <pre style={{ background: "#f8f8f8", borderRadius: "6px", padding: "10px 12px", fontSize: "12px", fontFamily: "monospace", color: "#6b7280", lineHeight: 1.5, marginTop: "8px", overflow: "hidden", whiteSpace: "pre", maxHeight: "90px" }}>
                  {t.code.split("\n").slice(0, 5).join("\n")}{t.code.split("\n").length > 5 ? "\n..." : ""}
                </pre>
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
