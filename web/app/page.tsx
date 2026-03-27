"use client";

import { useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "https://api.sgraal.com";

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
      <div className="mt-10 flex gap-4">
        <a href="#signup" className="bg-gold text-background font-semibold px-8 py-3 rounded-lg hover:bg-gold-dim transition">
          Get Your API Key
        </a>
        <a href="/playground" className="border border-gold text-gold font-semibold px-8 py-3 rounded-lg hover:bg-gold/10 transition">
          Try it live →
        </a>
      </div>
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
    </section>
  );
}

function Quickstart() {
  const [active, setActive] = useState<"curl" | "python" | "node" | "cdn">("curl");

  const examples: Record<string, string> = {
    cdn: `<!-- Zero-config embed — add to any HTML page -->
<script src="https://sgraal.com/sgraal.auto.js"
        data-api-key="sg_live_..."></script>

<script>
  // Preflight before using agent memory
  const result = await sgraal.preflight([
    { id: "mem_001", content: "User prefers dark mode",
      type: "preference", timestamp_age_days: 5,
      source_trust: 0.9, source_conflict: 0.1,
      downstream_count: 2 }
  ]);
  console.log(result.recommended_action);

  // Guard: wraps any function with preflight
  await sgraal.guard(
    (r) => agent.execute(r),
    memoryState, { domain: "fintech" }
  );
</script>`,
    curl: `curl -X POST https://api.sgraal.com/v1/preflight \\
  -H "Authorization: Bearer sg_live_..." \\
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
    python: `pip install sgraal

from sgraal import SgraalClient

client = SgraalClient(api_key="sg_live_...")

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
  };

  const tabs = [
    { key: "curl" as const, label: "REST API" },
    { key: "python" as const, label: "Python" },
    { key: "node" as const, label: "Node.js" },
    { key: "cdn" as const, label: "CDN / JS" },
  ];

  const installs: Record<string, string> = {
    curl: "No SDK needed — works with any language",
    python: "pip install sgraal",
    node: "npm install @sgraal/mcp",
    cdn: '<script src="https://sgraal.com/sgraal.auto.js">',
  };

  return (
    <section id="quickstart" className="px-6 py-20 max-w-4xl mx-auto">
      <h2 className="text-3xl sm:text-4xl font-bold text-center mb-4">
        Quickstart — <span className="text-gold">three ways</span>
      </h2>
      <p className="text-muted text-center max-w-2xl mx-auto mb-10">
        REST API, Python SDK, or Node.js — pick your stack.
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
    <section id="pricing" className="px-6 py-20 max-w-4xl mx-auto">
      <h2 className="text-3xl sm:text-4xl font-bold text-center mb-4">
        Simple <span className="text-gold">pricing</span>
      </h2>
      <p className="text-muted text-center max-w-xl mx-auto mb-14">
        Start free. Pay only when you scale.
      </p>

      <div className="grid md:grid-cols-2 gap-6 max-w-2xl mx-auto">
        <div className="border border-surface-light bg-surface rounded-xl p-8">
          <p className="font-mono text-gold text-sm tracking-wider uppercase mb-2">
            Free Tier
          </p>
          <p className="text-4xl font-bold mb-1">$0</p>
          <p className="text-muted text-sm mb-6">Up to 10,000 calls / month</p>
          <ul className="text-sm text-muted space-y-2">
            <li>All 8 risk components</li>
            <li>Full explainability</li>
            <li>Unlimited memory entries per call</li>
          </ul>
        </div>

        <div className="border border-gold/30 bg-surface rounded-xl p-8">
          <p className="font-mono text-gold text-sm tracking-wider uppercase mb-2">
            Usage-Based
          </p>
          <p className="text-4xl font-bold mb-1">
            $0.001<span className="text-lg text-muted font-normal"> / call</span>
          </p>
          <p className="text-muted text-sm mb-6">After 10,000 free calls</p>
          <ul className="text-sm text-muted space-y-2">
            <li>Everything in Free</li>
            <li>Priority support</li>
            <li>Usage dashboard</li>
          </ul>
        </div>
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
    <section id="signup" className="px-6 py-20 max-w-xl mx-auto">
      <h2 className="text-3xl sm:text-4xl font-bold text-center mb-4">
        Get your <span className="text-gold">API key</span>
      </h2>
      <p className="text-muted text-center mb-10">
        Enter your email. Get a key. Start calling the API.
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
        <div className="flex items-center gap-6 text-sm text-muted">
          <a href="mailto:hello@sgraal.com" className="hover:text-foreground transition">Contact</a>
          <a href="/privacy" className="hover:text-foreground transition">Privacy Policy</a>
          <a href="/terms" className="hover:text-foreground transition">Terms of Service</a>
        </div>
        <p className="text-muted text-sm">
          Apache 2.0 — Open protocol, free to use and embed.
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
      <Quickstart />
      <ApiDemo />
      <Pricing />
      <Signup />
      <Footer />
    </main>
  );
}
