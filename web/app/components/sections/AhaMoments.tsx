"use client";

import { useState } from "react";

const moments = [
  {
    title: "Preflight decision gate",
    description: "One API call before any memory-based action. Your agent asks permission before it acts.",
    expanded: "POST /v1/preflight \u2014 called before any memory-based action. Returns USE_MEMORY / WARN / ASK_USER / BLOCK + omega_mem_final risk score 0\u2013100.",
  },
  {
    title: "Compliance engine",
    description: "EU AI Act \u00b7 HIPAA \u00b7 MiFID2 \u00b7 Basel4 built in. One field in the request.",
    expanded: "Built-in profiles: EU AI Act (Article 9, 12, 13), HIPAA \u00a7164.312, MiFID2, Basel4. Non-compliant + irreversible action = automatic BLOCK. Full audit trail with SHA256 hash chain.",
  },
  {
    title: "Weibull decay",
    description: "Probabilistic freshness, not a simple timestamp cutoff. Tool state decays in hours. Identity persists for years.",
    expanded: "Freshness is not binary. Tool state decays in hours, identity memory persists for years. Weibull shape parameter \u03b2 is tuned per memory type. Timestamp alone is never enough.",
  },
  {
    title: "Action checkpoint",
    description: "Same memory, different risk. Read: 1.0\u00d7. Irreversible: 1.8\u00d7. Destructive: 2.5\u00d7.",
    expanded: "Same memory entry, different risk multiplier. read: 0.5\u00d7 \u00b7 write: 1.0\u00d7 \u00b7 delete: 1.5\u00d7 \u00b7 financial: 2.0\u00d7 \u00b7 irreversible: 2.5\u00d7. The action context changes everything.",
  },
  {
    title: "Entry Shapley",
    description: "Pinpoints the exact memory entry causing the block. Not just \u201chigh risk\u201d \u2014 which entry and why.",
    expanded: "Not just \u2018memory is risky\u2019 \u2014 but which exact entry, and by how much. omega_without_entry shows the counterfactual: remove entry #3, risk drops from 67 to 34.",
  },
  {
    title: "Zero-friction entry",
    description: "pip install sgraal. 3 lines of code. No signup. Demo key works immediately.",
    expanded: "pip install sgraal \u00b7 3 lines of code \u00b7 demo API key works immediately, no signup. SgraalClient handles retries, rate limits, and type safety out of the box.",
  },
];

export function AhaMoments() {
  const [open, setOpen] = useState<number | null>(null);

  return (
    <section className="px-6 py-16 max-w-5xl mx-auto">
      <h2 className="text-3xl sm:text-4xl font-bold text-center mb-14">
        Six things that make developers{" "}
        <span className="text-gold">stop and re-read.</span>
      </h2>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {moments.map((m, i) => (
          <button
            key={m.title}
            onClick={() => setOpen(open === i ? null : i)}
            className="border border-surface-light bg-surface rounded-xl p-6 hover:bg-surface-light transition text-left w-full"
          >
            <div className="flex items-start justify-between gap-2">
              <p className="font-semibold text-gold mb-2">{m.title}</p>
              <span className={`text-muted text-xs mt-1 transition-transform ${open === i ? "rotate-180" : ""}`}>&#9660;</span>
            </div>
            <p className="text-muted text-sm leading-relaxed">{m.description}</p>
            {open === i && (
              <p className="text-foreground/70 text-xs leading-relaxed mt-3 pt-3 border-t border-surface-light">
                {m.expanded}
              </p>
            )}
          </button>
        ))}
      </div>
    </section>
  );
}
