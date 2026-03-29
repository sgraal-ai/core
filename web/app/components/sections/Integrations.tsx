"use client";

import { useState } from "react";

const badges = [
  "LangChain", "CrewAI", "AutoGen", "LlamaIndex",
  "mem0", "MCP", "OpenAI", "Anthropic",
];

const installs: Record<string, { label: string; cmd: string }> = {
  python: { label: "Python", cmd: "pip install sgraal" },
  langchain: { label: "LangChain", cmd: "pip install langchain-sgraal" },
  mcp: { label: "MCP / Node", cmd: "npm install @sgraal/mcp" },
};

export function Integrations() {
  const [active, setActive] = useState<string>("python");

  return (
    <section className="px-6 py-20 max-w-5xl mx-auto">
      <h2 className="text-3xl sm:text-4xl font-bold text-center mb-4">
        Works with your <span className="text-gold">stack</span>
      </h2>
      <p className="text-muted text-center max-w-2xl mx-auto mb-10">
        REST API, Python SDK, Node MCP server, or framework-specific wrappers.
      </p>

      <div className="flex flex-wrap justify-center gap-3 mb-10">
        {badges.map((b) => (
          <span key={b} className="border border-surface-light bg-surface px-4 py-2 rounded-lg text-sm text-foreground/80 font-medium">
            {b}
          </span>
        ))}
      </div>

      <div className="max-w-lg mx-auto">
        <div className="flex justify-center gap-2 mb-4">
          {Object.entries(installs).map(([key, val]) => (
            <button
              key={key}
              onClick={() => setActive(key)}
              className={`font-mono text-sm px-5 py-2 rounded-lg transition ${
                active === key
                  ? "bg-gold text-background"
                  : "bg-surface text-muted hover:text-foreground"
              }`}
            >
              {val.label}
            </button>
          ))}
        </div>
        <pre className="bg-surface border border-surface-light rounded-xl p-5 text-sm font-mono text-center text-foreground/80">
          {installs[active].cmd}
        </pre>
      </div>
    </section>
  );
}
