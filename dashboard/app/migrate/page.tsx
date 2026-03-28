"use client";

import { useState } from "react";

const SOURCES = [
  { id: "mem0", name: "Mem0", docs: "pip install mem0-sgraal" },
  { id: "zep", name: "Zep", docs: "sgraal migrate-from-zep --zep-url URL --zep-api-key KEY" },
  { id: "letta", name: "Letta", docs: "sgraal migrate-from-letta --letta-url URL --letta-api-key KEY" },
];

export default function MigratePage() {
  const [selected, setSelected] = useState<string | null>(null);
  const [step, setStep] = useState(1);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Memory Migration Wizard</h1>
      <p className="text-muted mb-8">Import your existing agent memories from Mem0, Zep, or Letta with automatic health auditing.</p>

      {step === 1 && (
        <div>
          <h2 className="text-lg font-semibold mb-4">Step 1: Select Source</h2>
          <div className="grid grid-cols-3 gap-4">
            {SOURCES.map((s) => (
              <button
                key={s.id}
                onClick={() => { setSelected(s.id); setStep(2); }}
                className={`border rounded-lg p-6 text-left transition hover:border-gold ${
                  selected === s.id ? "border-gold bg-surface" : "border-surface-light"
                }`}
                data-testid={`source-${s.id}`}
              >
                <p className="font-bold text-foreground">{s.name}</p>
                <p className="text-sm text-muted mt-1">Click to start migration</p>
              </button>
            ))}
          </div>
        </div>
      )}

      {step === 2 && selected && (
        <div>
          <h2 className="text-lg font-semibold mb-4">Step 2: Configure {SOURCES.find((s) => s.id === selected)?.name}</h2>
          <pre className="bg-zinc-900 p-4 rounded-lg text-sm mb-4 font-mono">
            {SOURCES.find((s) => s.id === selected)?.docs}
          </pre>
          <div className="flex gap-3">
            <button onClick={() => setStep(1)} className="px-4 py-2 border border-surface-light rounded hover:bg-surface transition">Back</button>
            <button onClick={() => setStep(3)} className="px-4 py-2 bg-gold text-black rounded font-medium hover:bg-gold/80 transition">Run Migration</button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div>
          <h2 className="text-lg font-semibold mb-4">Step 3: Migration Complete</h2>
          <div className="border border-surface-light rounded-lg p-6">
            <p className="text-green-400 font-semibold mb-2">Migration wizard ready</p>
            <p className="text-muted text-sm">Run the CLI command above to start the actual migration with a retrospective health audit.</p>
            <p className="text-muted text-sm mt-2">Use <code className="text-gold">--dry-run</code> to preview without storing entries.</p>
          </div>
          <button onClick={() => { setStep(1); setSelected(null); }} className="mt-4 px-4 py-2 border border-surface-light rounded hover:bg-surface transition">Start Over</button>
        </div>
      )}
    </div>
  );
}
