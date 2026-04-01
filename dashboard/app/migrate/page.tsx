"use client";

import { useState } from "react";

const SOURCES = [
  { id: "mem0", name: "Mem0", icon: "M", desc: "Import memories from Mem0 with automatic health scoring.", cmd: "pip install mem0-sgraal", docs: "from mem0_sgraal import SafeMemory\n\nsafe = SafeMemory(\n    mem0_api_key=\"m0-...\",\n    sgraal_api_key=\"sg_live_...\",\n    on_block=\"warn\",  # or raise/skip/heal\n)\n\n# All Mem0 operations now have preflight guards\nsafe.add(\"User prefers dark mode\", user_id=\"u1\")\nresult = safe.search(\"preferences\", user_id=\"u1\")" },
  { id: "zep", name: "Zep", icon: "Z", desc: "Migrate Zep memory store with full provenance tracking.", cmd: "sgraal migrate-from-zep --zep-url URL --zep-api-key KEY", docs: "# Step 1: Export from Zep\nsgraal migrate-from-zep \\\n  --zep-url https://zep.example.com \\\n  --zep-api-key zep_... \\\n  --sgraal-key sg_live_... \\\n  --dry-run  # Preview first\n\n# Step 2: Run health audit\nsgraal audit --source zep --report" },
  { id: "letta", name: "Letta", icon: "L", desc: "Import Letta agent memories with conflict detection.", cmd: "sgraal migrate-from-letta --letta-url URL --letta-api-key KEY", docs: "# Step 1: Export from Letta\nsgraal migrate-from-letta \\\n  --letta-url https://letta.example.com \\\n  --letta-api-key letta_... \\\n  --sgraal-key sg_live_... \\\n  --dry-run\n\n# Step 2: Run health audit\nsgraal audit --source letta --report" },
  { id: "custom", name: "Custom JSON", icon: "{}", desc: "Import any memory source using the MemCube JSON format.", cmd: "sgraal import --file memories.json --sgraal-key sg_live_...", docs: "# MemCube format (memories.json):\n[\n  {\n    \"id\": \"mem_001\",\n    \"content\": \"User prefers dark mode\",\n    \"type\": \"preference\",\n    \"timestamp_age_days\": 3,\n    \"source_trust\": 0.95,\n    \"source_conflict\": 0.05,\n    \"downstream_count\": 2\n  }\n]\n\n# Import with health audit\nsgraal import \\\n  --file memories.json \\\n  --sgraal-key sg_live_... \\\n  --audit" },
];

const CARD: React.CSSProperties = { background: "#ffffff", borderRadius: "8px", padding: "24px", boxShadow: "0 1px 3px rgba(0,0,0,0.06)" };

export default function MigratePage() {
  const [selected, setSelected] = useState<string | null>(null);
  const [step, setStep] = useState(1);
  const [copied, setCopied] = useState(false);

  const source = SOURCES.find((s) => s.id === selected);

  function copyCmd() {
    if (!source) return;
    navigator.clipboard.writeText(source.cmd);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Memory Migration Wizard</h1>
      <p className="text-muted text-sm mb-6">Import your existing agent memories from Mem0, Zep, Letta, or custom JSON with automatic health auditing.</p>

      {/* Progress */}
      <div style={{ display: "flex", gap: "4px", marginBottom: "32px" }}>
        {[1, 2, 3].map((s) => (
          <div key={s} style={{ flex: 1, height: "4px", borderRadius: "2px", background: s <= step ? "#c9a962" : "#e5e7eb", transition: "background 0.3s" }} />
        ))}
      </div>

      {step === 1 && (
        <div>
          <h2 style={{ fontSize: "18px", fontWeight: 700, marginBottom: "16px" }}>Step 1: Select Source</h2>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
            {SOURCES.map((s) => (
              <button
                key={s.id}
                onClick={() => { setSelected(s.id); setStep(2); }}
                style={{
                  ...CARD, textAlign: "left", cursor: "pointer", border: "2px solid transparent",
                  borderColor: selected === s.id ? "#c9a962" : "transparent",
                  transition: "border-color 0.2s",
                }}
                onMouseEnter={(e) => { if (selected !== s.id) e.currentTarget.style.borderColor = "rgba(201,169,98,0.3)"; }}
                onMouseLeave={(e) => { if (selected !== s.id) e.currentTarget.style.borderColor = "transparent"; }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "8px" }}>
                  <span style={{ width: "36px", height: "36px", borderRadius: "8px", background: "rgba(201,169,98,0.1)", color: "#c9a962", fontWeight: 700, fontSize: "14px", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "monospace" }}>{s.icon}</span>
                  <span style={{ fontSize: "16px", fontWeight: 700, color: "#0B0F14" }}>{s.name}</span>
                </div>
                <p style={{ fontSize: "13px", color: "#6b7280", lineHeight: 1.5 }}>{s.desc}</p>
              </button>
            ))}
          </div>
        </div>
      )}

      {step === 2 && source && (
        <div>
          <h2 style={{ fontSize: "18px", fontWeight: 700, marginBottom: "16px" }}>Step 2: Configure {source.name}</h2>
          <div style={CARD}>
            <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "8px" }}>Install & Run</p>
            <div style={{ display: "flex", alignItems: "center", gap: "12px", background: "#0B0F14", borderRadius: "8px", padding: "16px 20px", marginBottom: "16px" }}>
              <code style={{ flex: 1, color: "#e2e8f0", fontSize: "14px", fontFamily: "monospace" }}>{source.cmd}</code>
              <button onClick={copyCmd} style={{ color: copied ? "#c9a962" : "#6b7280", fontSize: "13px", cursor: "pointer", background: "none", border: "none", whiteSpace: "nowrap" }}>
                {copied ? "Copied!" : "Copy"}
              </button>
            </div>

            <p style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "8px" }}>Full Example</p>
            <pre style={{ background: "#0B0F14", color: "#e2e8f0", borderRadius: "8px", padding: "20px", fontSize: "13px", fontFamily: "monospace", lineHeight: 1.6, overflowX: "auto" }}>
              {source.docs}
            </pre>
          </div>

          <div style={{ display: "flex", gap: "12px", marginTop: "20px" }}>
            <button onClick={() => setStep(1)} style={{ padding: "8px 20px", borderRadius: "6px", border: "1px solid #e5e7eb", fontSize: "14px", cursor: "pointer", background: "#ffffff" }}>Back</button>
            <button onClick={() => setStep(3)} style={{ background: "#c9a962", color: "#0B0F14", fontWeight: 600, padding: "8px 20px", borderRadius: "6px", fontSize: "14px", border: "none", cursor: "pointer" }}>I{"'"}ve run the migration</button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div>
          <h2 style={{ fontSize: "18px", fontWeight: 700, marginBottom: "16px" }}>Step 3: Migration Complete</h2>
          <div style={{ ...CARD, textAlign: "center", padding: "48px" }}>
            <p style={{ fontSize: "36px", color: "#16a34a", marginBottom: "12px" }}>✓</p>
            <h3 style={{ fontSize: "20px", fontWeight: 700, color: "#0B0F14", marginBottom: "8px" }}>Migration wizard complete</h3>
            <p style={{ fontSize: "14px", color: "#6b7280", maxWidth: "400px", margin: "0 auto 8px" }}>
              Your memories are now governed by Sgraal. Every preflight call will score them for freshness, drift, and provenance.
            </p>
            <p style={{ fontSize: "13px", color: "#6b7280" }}>
              Use <code style={{ color: "#c9a962" }}>--dry-run</code> to preview without storing entries.
            </p>
          </div>
          <div style={{ display: "flex", gap: "12px", marginTop: "20px" }}>
            <button onClick={() => { setStep(1); setSelected(null); }} style={{ padding: "8px 20px", borderRadius: "6px", border: "1px solid #e5e7eb", fontSize: "14px", cursor: "pointer", background: "#ffffff" }}>Start Over</button>
            <a href="/" style={{ background: "#c9a962", color: "#0B0F14", fontWeight: 600, padding: "8px 20px", borderRadius: "6px", fontSize: "14px", textDecoration: "none", display: "inline-block" }}>Go to Dashboard</a>
          </div>
        </div>
      )}
    </div>
  );
}
