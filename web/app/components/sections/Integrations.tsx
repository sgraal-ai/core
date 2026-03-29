"use client";

import { useState } from "react";

const badges = [
  "LangChain", "CrewAI", "AutoGen", "LlamaIndex",
  "mem0", "MCP", "OpenAI", "Anthropic",
];

const tabs = [
  { key: "python", label: "Python", cmd: "pip install sgraal" },
  { key: "langchain", label: "LangChain", cmd: "pip install langchain-sgraal" },
  { key: "mcp", label: "MCP / Node", cmd: "npm install @sgraal/mcp" },
];

export function Integrations() {
  const [active, setActive] = useState("python");
  const [copied, setCopied] = useState(false);

  const currentCmd = tabs.find((t) => t.key === active)?.cmd ?? "";

  function handleCopy() {
    navigator.clipboard.writeText(currentCmd);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <section className="px-6 py-16 max-w-5xl mx-auto">
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
          {tabs.map((t) => (
            <button
              key={t.key}
              onClick={() => setActive(t.key)}
              className={`font-mono text-sm px-5 py-2 rounded-lg transition ${
                active === t.key
                  ? "bg-gold text-background"
                  : "bg-surface text-muted hover:text-foreground"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
        <div className="relative">
          <pre className="bg-surface border border-surface-light rounded-xl p-5 text-sm font-mono text-center text-foreground/80 pr-12">
            {currentCmd}
          </pre>
          <button
            onClick={handleCopy}
            className="absolute top-3 right-3 text-muted hover:text-foreground transition p-1.5 rounded-md hover:bg-surface-light"
            title="Copy to clipboard"
          >
            {copied ? (
              <span className="text-green-400 text-xs font-mono">Copied!</span>
            ) : (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
              </svg>
            )}
          </button>
        </div>
      </div>
    </section>
  );
}
