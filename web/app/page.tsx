"use client";

import { useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "https://api.sgraal.com";

function PipCopy() {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => { navigator.clipboard.writeText("pip install sgraal"); setCopied(true); setTimeout(() => setCopied(false), 2000); }}
      className="border border-gold text-gold font-mono px-8 py-3 rounded-lg hover:bg-gold/10 transition text-sm"
    >
      {copied ? "Copied!" : "pip install sgraal"}
    </button>
  );
}

function Hero() {
  return (
    <section className="flex flex-col items-center justify-center text-center px-6 pt-32 pb-20">
      <p className="text-gold font-mono text-sm tracking-widest uppercase mb-6">
        Memory Governance Protocol
      </p>
      <h1 className="text-4xl sm:text-6xl font-bold max-w-3xl leading-tight">
        Your AI agent doesn&apos;t know{" "}
        <span className="text-gold">it&apos;s forgetting.</span>
      </h1>
      <p className="text-muted text-lg sm:text-xl max-w-2xl mt-6">
        Stale memory. Conflicting sources. Silent drift. Sgraal catches it
        before your agent acts — in under 10&nbsp;ms.
      </p>
      <div className="mt-10 flex flex-wrap justify-center gap-4">
        <a href="/playground" className="bg-gold text-background font-semibold px-8 py-3 rounded-lg hover:bg-gold-dim transition">
          Try it now — no signup
        </a>
        <PipCopy />
      </div>
      <p className="mt-6 text-muted text-sm">
        <a href="/benchmark" className="text-gold hover:underline">See benchmark →</a>
        <span className="mx-2">&middot;</span>
        <a href="/roi" className="hover:text-foreground transition">ROI Calculator</a>
        <span className="mx-2">&middot;</span>
        <a href="https://github.com/sgraal-ai/core/tree/main/examples" className="hover:text-foreground transition">Examples</a>
      </p>
    </section>
  );
}

function HowItWorks() {
  const steps = [
    {
      label: "USE_MEMORY",
      color: "text-green-400",
      border: "border-green-400/30",
      description: "Memory is fresh and consistent. Proceed with confidence.",
    },
    {
      label: "WARN",
      color: "text-yellow-400",
      border: "border-yellow-400/30",
      description: "Some staleness or conflict detected. Log and monitor.",
    },
    {
      label: "BLOCK",
      color: "text-red-400",
      border: "border-red-400/30",
      description: "High risk of acting on bad data. Stop. Ask. Verify.",
    },
  ];

  return (
    <section id="how-it-works" className="px-6 py-20 max-w-5xl mx-auto">
      <h2 className="text-3xl sm:text-4xl font-bold text-center mb-4">
        One preflight call. <span className="text-gold">Three outcomes.</span>
      </h2>
      <p className="text-muted text-center max-w-2xl mx-auto mb-14">
        Before every memory-based decision, Sgraal scores the risk and tells
        your agent what to do.
      </p>
      <div className="grid md:grid-cols-3 gap-6">
        {steps.map((s) => (
          <div
            key={s.label}
            className={`border ${s.border} bg-surface rounded-xl p-8 text-center`}
          >
            <p className={`font-mono text-xl font-bold mb-3 ${s.color}`}>
              {s.label}
            </p>
            <p className="text-muted text-sm">{s.description}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function InTheWild() {
  return (
    <section className="px-6 py-16 max-w-3xl mx-auto">
      <h2 className="text-3xl sm:text-4xl font-bold text-center mb-10">
        In the <span className="text-gold">wild</span>
      </h2>
      <div className="border border-gold/30 bg-surface rounded-xl p-8">
        <div className="flex items-start gap-4">
          <div className="text-gold text-3xl font-mono font-bold shrink-0">&ldquo;</div>
          <div>
            <p className="text-foreground/90 leading-relaxed mb-4">
              @grok ran 250 steps with zero drift using GrokGuard v2 + /v1/heal.
              healing_counter locked idempotent. 0.0% error rate.
            </p>
            <div className="flex items-center gap-3">
              <span className="text-gold font-mono text-sm font-semibold">@grok</span>
              <span className="text-muted text-xs">Field report — GrokGuard v2</span>
            </div>
          </div>
        </div>
      </div>
      <p className="text-center mt-6 text-sm">
        <a href="/failures" className="text-gold hover:underline">See failure gallery →</a>
        <span className="text-muted mx-2">·</span>
        <span className="text-muted">5 failure patterns Sgraal catches before they happen</span>
      </p>
    </section>
  );
}

function AnyStack() {
  return (
    <section className="px-6 py-20 max-w-5xl mx-auto">
      <h2 className="text-3xl sm:text-4xl font-bold text-center mb-4">
        Any AI. Any memory. <span className="text-gold">Any stack.</span>
      </h2>
      <p className="text-muted text-center max-w-2xl mx-auto mb-12">
        Sgraal sits between your memory layer and your agent. One API call. Standard headers on every response.
      </p>

      <div className="grid md:grid-cols-3 gap-6 mb-10">
        <div className="border border-surface-light bg-surface rounded-xl p-6 text-center">
          <p className="text-gold font-mono text-sm font-semibold mb-3">AI Agents</p>
          <p className="text-foreground/80 text-sm">Claude &middot; GPT &middot; Grok &middot; Gemini &middot; MCP</p>
        </div>
        <div className="border border-surface-light bg-surface rounded-xl p-6 text-center">
          <p className="text-gold font-mono text-sm font-semibold mb-3">Frameworks</p>
          <p className="text-foreground/80 text-sm">LangChain &middot; LlamaIndex &middot; CrewAI &middot; AutoGen &middot; <a href="/compatibility" className="text-gold hover:underline">+10 more</a></p>
        </div>
        <div className="border border-surface-light bg-surface rounded-xl p-6 text-center">
          <p className="text-gold font-mono text-sm font-semibold mb-3">Memory Stores</p>
          <p className="text-foreground/80 text-sm">Mem0 &middot; Zep &middot; Letta &middot; Pinecone &middot; any vector DB</p>
        </div>
      </div>

      <div className="bg-surface border border-surface-light rounded-xl p-5 text-center">
        <p className="font-mono text-sm text-foreground/80 mb-2">
          <span className="text-gold">X-Sgraal-Score:</span> 67 &nbsp;&middot;&nbsp;
          <span className="text-red-400">X-Sgraal-Decision:</span> BLOCK &nbsp;&middot;&nbsp;
          <span className="text-red-400">X-Sgraal-Checkpoint:</span> failed
        </p>
        <p className="text-muted text-xs">Standard headers on every response. Works as middleware — no code changes needed.</p>
      </div>
    </section>
  );
}

function Quickstart() {
  const [active, setActive] = useState<"mcp" | "python" | "node" | "curl">("mcp");

  const examples: Record<string, string> = {
    mcp: `// Add to Claude Desktop or Cursor MCP config:
{
  "mcpServers": {
    "sgraal": {
      "command": "npx",
      "args": ["-y", "@sgraal/mcp"],
      "env": { "SGRAAL_API_KEY": "sg_demo_playground" }
    }
  }
}
// Works immediately with demo key — no signup.`,
    python: `pip install sgraal

from sgraal import SgraalClient

client = SgraalClient(api_key="sg_demo_playground")

result = client.preflight(
    memory_state=[{
        "id": "mem_001",
        "content": "User prefers metric units",
        "type": "preference",
        "timestamp_age_days": 45,
        "source_trust": 0.9,
        "source_conflict": 0.2,
        "downstream_count": 3,
    }],
    action_type="irreversible",
    domain="fintech",
)
print(result.recommended_action)  # USE_MEMORY / WARN / BLOCK`,
    node: `npm install @sgraal/mcp

import { createGuard } from "@sgraal/mcp";

const guard = createGuard(); // reads SGRAAL_API_KEY from env

const result = await guard({
  memory_state: [{
    id: "mem_001",
    content: "User prefers metric units",
    type: "preference",
    timestamp_age_days: 45,
    source_trust: 0.9,
    source_conflict: 0.2,
    downstream_count: 3,
  }],
  action_type: "irreversible",
  domain: "fintech",
});
// Throws SgraalBlockedError on BLOCK`,
    curl: `curl -X POST https://api.sgraal.com/v1/preflight \\
  -H "Authorization: Bearer sg_demo_playground" \\
  -H "Content-Type: application/json" \\
  -d '{
    "memory_state": [{
      "id": "mem_001",
      "content": "User prefers metric units",
      "type": "preference",
      "timestamp_age_days": 45,
      "source_trust": 0.9,
      "source_conflict": 0.2,
      "downstream_count": 3
    }],
    "action_type": "irreversible",
    "domain": "fintech"
  }'`,
  };

  const tabs = [
    { key: "mcp" as const, label: "MCP (Claude/Cursor)" },
    { key: "python" as const, label: "Python" },
    { key: "node" as const, label: "Node.js" },
    { key: "curl" as const, label: "REST API" },
  ];

  const installs: Record<string, string> = {
    mcp: "Add to Claude Desktop config. Works immediately with demo key.",
    python: "pip install sgraal",
    node: "npm install @sgraal/mcp",
    curl: "No SDK needed — works with any language",
  };

  return (
    <section id="quickstart" className="px-6 py-20 max-w-4xl mx-auto">
      <h2 className="text-3xl sm:text-4xl font-bold text-center mb-4">
        Quickstart — <span className="text-gold">four ways</span>
      </h2>
      <p className="text-muted text-center max-w-2xl mx-auto mb-2">
        MCP, Python, Node.js, or REST — pick your stack.
      </p>
      <p className="text-center mb-10">
        <a href="/compatibility" className="text-gold text-sm hover:underline">Works with your stack &rarr; 14 frameworks supported</a>
      </p>

      <div className="flex justify-center gap-2 mb-2">
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

      <p className="text-center text-muted text-xs mb-6 font-mono">
        {installs[active]}
      </p>

      <pre className="bg-surface border border-surface-light rounded-xl p-5 text-sm overflow-x-auto leading-relaxed text-foreground/80">
        {examples[active]}
      </pre>
    </section>
  );
}

function ApiDemo() {
  const curlExample = `curl -X POST ${API_BASE}/v1/preflight \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "memory_state": [{
      "id": "mem_001",
      "content": "User prefers metric units",
      "type": "preference_memory",
      "timestamp_age_days": 45,
      "source_trust": 0.9,
      "source_conflict": 0.2,
      "downstream_count": 3
    }],
    "action_type": "irreversible",
    "domain": "fintech"
  }'`;

  const responseExample = `{
  "omega_mem_final": 42.1,
  "recommended_action": "WARN",
  "assurance_score": 70,
  "explainability_note": "Highest risk: s_freshness (54.0/100).",
  "component_breakdown": {
    "s_freshness": 54.0,
    "s_drift": 33.6,
    "s_provenance": 10.0,
    "s_propagation": 24.0,
    "r_recall": 36.4,
    "r_encode": 5.0,
    "s_interference": 20.0,
    "s_recovery": 73.0
  }
}`;

  return (
    <section id="api-demo" className="px-6 py-20 max-w-4xl mx-auto">
      <h2 className="text-3xl sm:text-4xl font-bold text-center mb-4">
        Live API <span className="text-gold">Demo</span>
      </h2>
      <p className="text-muted text-center max-w-2xl mx-auto mb-12">
        A single POST. Instant risk score. Full explainability.
      </p>

      <div className="grid md:grid-cols-2 gap-6">
        <div>
          <p className="font-mono text-sm text-gold mb-3">Request</p>
          <pre className="bg-surface border border-surface-light rounded-xl p-5 text-sm overflow-x-auto leading-relaxed text-foreground/80">
            {curlExample}
          </pre>
        </div>
        <div>
          <p className="font-mono text-sm text-green-400 mb-3">Response</p>
          <pre className="bg-surface border border-surface-light rounded-xl p-5 text-sm overflow-x-auto leading-relaxed text-foreground/80">
            {responseExample}
          </pre>
        </div>
      </div>
    </section>
  );
}

function Pricing() {
  return (
    <section id="pricing" className="px-6 py-20 max-w-5xl mx-auto">
      <h2 className="text-3xl sm:text-4xl font-bold text-center mb-4">
        Simple <span className="text-gold">pricing</span>
      </h2>
      <p className="text-muted text-center max-w-xl mx-auto mb-14">
        No signup required to start. Add an email when you&apos;re ready to scale.
      </p>

      <div className="grid md:grid-cols-3 gap-6">
        <div className="border border-surface-light bg-surface rounded-xl p-8">
          <p className="font-mono text-gold text-sm tracking-wider uppercase mb-2">Free</p>
          <p className="text-4xl font-bold mb-1">$0</p>
          <p className="text-muted text-sm mb-6">10,000 decisions / month</p>
          <ul className="text-sm text-muted space-y-2">
            <li>Compact response (score + action + repair)</li>
            <li>Demo key — immediate, no signup</li>
            <li>All 10 risk components</li>
          </ul>
          <p className="text-muted text-xs mt-4 italic">Perfect for 1 agent.</p>
        </div>

        <div className="border border-gold/30 bg-surface rounded-xl p-8">
          <p className="font-mono text-gold text-sm tracking-wider uppercase mb-2">Pro</p>
          <p className="text-4xl font-bold mb-1">
            $0.001<span className="text-lg text-muted font-normal"> / decision</span>
          </p>
          <p className="text-muted text-sm mb-6">After 10,000 free decisions</p>
          <ul className="text-sm text-muted space-y-2">
            <li>Full explainability + Shapley attribution</li>
            <li>Complete repair plan with success probability</li>
            <li>Decision readiness dashboard</li>
          </ul>
          <p className="text-muted text-xs mt-4 italic">Scales with your fleet.</p>
        </div>

        <div className="border border-surface-light bg-surface rounded-xl p-8">
          <p className="font-mono text-gold text-sm tracking-wider uppercase mb-2">Enterprise</p>
          <p className="text-4xl font-bold mb-1">Custom</p>
          <p className="text-muted text-sm mb-6">For regulated industries</p>
          <ul className="text-sm text-muted space-y-2">
            <li>EU AI Act / HIPAA / FDA 510(k) compliance</li>
            <li>Full audit trail + SIEM export</li>
            <li>On-prem deployment option</li>
            <li>SLA + dedicated support</li>
          </ul>
          <p className="text-muted text-xs mt-4 italic">For regulated industries.</p>
        </div>
      </div>
    </section>
  );
}

function DemoKey() {
  const [copied, setCopied] = useState(false);
  return (
    <section className="px-6 py-16 max-w-2xl mx-auto">
      <h2 className="text-3xl sm:text-4xl font-bold text-center mb-4">
        Start <span className="text-gold">now</span>
      </h2>
      <p className="text-muted text-center mb-8">No signup required. Use the demo key immediately.</p>

      <div className="bg-surface border border-gold/30 rounded-xl p-6 text-center mb-4">
        <p className="text-muted text-xs uppercase tracking-wider mb-2">Your demo key</p>
        <button
          onClick={() => { navigator.clipboard.writeText("sg_demo_playground"); setCopied(true); setTimeout(() => setCopied(false), 2000); }}
          className="font-mono text-gold text-lg hover:text-gold-dim transition cursor-pointer"
        >
          {copied ? "Copied!" : "sg_demo_playground"}
        </button>
        <p className="text-muted text-sm mt-3">10,000 free decisions/month &middot; No signup needed</p>
      </div>

      <div className="border border-yellow-400/30 bg-surface rounded-lg p-4 text-center mb-8">
        <p className="text-yellow-400/80 text-xs">
          This is a shared demo key — rate limited to 10 calls/min per IP.<br />
          For production use, <a href="#signup-form" className="text-gold hover:underline">get your own free key &darr;</a>
        </p>
      </div>
    </section>
  );
}

function Signup() {
  const [email, setEmail] = useState("");
  const [result, setResult] = useState<{
    api_key: string;
    customer_id: string;
  } | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setResult(null);
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/v1/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(data?.detail ?? `Signup failed (${res.status})`);
      }

      const data = await res.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section id="signup-form" className="px-6 py-16 max-w-xl mx-auto">
      <h2 className="text-2xl font-bold text-center mb-2">
        Get your <span className="text-gold">own key</span>
      </h2>
      <p className="text-muted text-center text-sm mb-8">
        Optional — for production use, higher rate limits, and your own dashboard.
      </p>

      {!result ? (
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <input
            type="email"
            required
            placeholder="you@company.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="bg-surface border border-surface-light rounded-lg px-5 py-3 text-foreground placeholder:text-muted focus:outline-none focus:border-gold transition"
          />
          <button
            type="submit"
            disabled={loading}
            className="bg-gold text-background font-semibold px-8 py-3 rounded-lg hover:bg-gold-dim transition disabled:opacity-50"
          >
            {loading ? "Creating..." : "Get API Key"}
          </button>
          {error && (
            <p className="text-red-400 text-sm text-center">{error}</p>
          )}
        </form>
      ) : (
        <div className="bg-surface border border-gold/30 rounded-xl p-6">
          <p className="text-green-400 font-mono text-sm mb-4">
            Your API key (save it — shown only once):
          </p>
          <pre className="bg-background rounded-lg p-4 text-gold font-mono text-sm break-all">
            {result.api_key}
          </pre>
          <p className="text-muted text-xs mt-4">
            Customer ID: {result.customer_id}
          </p>
        </div>
      )}
    </section>
  );
}

function Footer() {
  return (
    <footer className="border-t border-surface-light py-10 mt-10">
      <div className="max-w-5xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-6">
        <p className="font-mono text-gold text-lg font-bold">Sgraal</p>
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-muted">
          <a href="mailto:hello@sgraal.com" className="hover:text-foreground transition">Contact</a>
          <a href="/security" className="hover:text-foreground transition">Security</a>
          <a href="/partners" className="hover:text-foreground transition">Partners</a>
          <a href="/compatibility" className="hover:text-foreground transition">Compatibility</a>
          <a href="/failures" className="hover:text-foreground transition">Failures</a>
          <a href="/privacy" className="hover:text-foreground transition">Privacy Policy</a>
          <a href="/terms" className="hover:text-foreground transition">Terms of Service</a>
        </div>
        <p className="text-muted text-sm">
          Free to start &middot; No signup required &middot; Apache 2.0
        </p>
      </div>
    </footer>
  );
}

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "Sgraal",
  description:
    "Memory governance protocol for AI agents. Evaluates whether agent memory is reliable before acting — returning a risk score and recommended action in under 10ms.",
  url: "https://sgraal.com",
  applicationCategory: "DeveloperApplication",
  operatingSystem: "Any",
  offers: [
    {
      "@type": "Offer",
      price: "0",
      priceCurrency: "USD",
      description: "Free tier: 10,000 API calls per month",
    },
    {
      "@type": "Offer",
      price: "0.001",
      priceCurrency: "USD",
      description: "Usage-based: $0.001 per call after free tier",
    },
  ],
  author: {
    "@type": "Organization",
    name: "Sgraal",
    url: "https://sgraal.com",
    email: "hello@sgraal.com",
  },
  license: "https://www.apache.org/licenses/LICENSE-2.0",
};

export default function Home() {
  return (
    <main className="flex-1">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <Hero />
      <HowItWorks />
      <InTheWild />
      <AnyStack />
      <Quickstart />
      <ApiDemo />
      <Pricing />
      <DemoKey />
      <Signup />
      <Footer />
    </main>
  );
}
