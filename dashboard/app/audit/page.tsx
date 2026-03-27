"use client";
import { useState } from "react";

const FORMATS = ["splunk", "datadog", "elastic"] as const;

export default function AuditPage() {
  const [decision, setDecision] = useState("");
  const [entries, setEntries] = useState<Array<Record<string, unknown>>>([]);
  const [exportFmt, setExportFmt] = useState<typeof FORMATS[number]>("splunk");

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Audit Log</h1>
      <p className="text-muted text-sm mb-6">View, search, and export preflight decision history. SIEM-ready formats.</p>

      <div className="flex gap-3 mb-6">
        <select value={decision} onChange={e => setDecision(e.target.value)} className="bg-surface border border-surface-light rounded px-3 py-2 text-sm">
          <option value="">All decisions</option>
          <option value="USE_MEMORY">USE_MEMORY</option>
          <option value="WARN">WARN</option>
          <option value="ASK_USER">ASK_USER</option>
          <option value="BLOCK">BLOCK</option>
        </select>
        <div className="flex gap-1">
          {FORMATS.map(f => (
            <button key={f} onClick={() => setExportFmt(f)} className={`text-xs px-3 py-2 rounded border ${exportFmt === f ? "bg-gold text-background border-gold" : "bg-surface border-surface-light text-muted"}`}>
              {f}
            </button>
          ))}
        </div>
        <button className="bg-gold text-background text-sm font-semibold px-4 py-2 rounded">Export</button>
      </div>

      <div className="bg-surface border border-surface-light rounded-xl p-5">
        <p className="text-xs text-muted mb-3">Connect API key via Settings to load audit data. Supports Splunk, Datadog, and Elasticsearch export.</p>
        {entries.length === 0 && <p className="text-xs text-muted">No audit entries loaded. Enter API key in Settings panel.</p>}
        {entries.map((e, i) => (
          <div key={i} className="flex justify-between py-1 border-b border-surface-light text-xs font-mono">
            <span className="text-muted">{String(e.created_at)}</span>
            <span>{String(e.decision)}</span>
            <span>Ω={String(e.omega_score)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
