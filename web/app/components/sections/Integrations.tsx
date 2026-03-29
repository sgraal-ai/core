"use client";

import { useState } from "react";

const badges = [
  "LangChain", "CrewAI", "AutoGen", "LlamaIndex",
  "mem0", "MCP", "OpenAI", "Anthropic",
];

const commands = [
  "pip install sgraal",
  "pip install langchain-sgraal",
  "npm install @sgraal/mcp",
];

function CopyRow({ cmd }: { cmd: string }) {
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText(cmd);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="flex items-center justify-between bg-surface border border-surface-light rounded-lg px-4 py-3">
      <span className="font-mono text-sm text-foreground/80">{cmd}</span>
      <button onClick={handleCopy} className="text-muted hover:text-foreground transition p-1 rounded shrink-0 ml-3" title="Copy">
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
  );
}

export function Integrations() {
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

      <div className="max-w-lg mx-auto space-y-3">
        {commands.map((cmd) => (
          <CopyRow key={cmd} cmd={cmd} />
        ))}
      </div>
    </section>
  );
}
