"use client";

import { useState, useEffect, useCallback } from "react";
import { getApiKey, getApiUrl } from "../../lib/storage";
import { LoadingSkeleton, ConnectKeyState } from "../../components/LoadingSkeleton";

const CARD = "bg-surface border border-surface-light rounded-xl p-5";

export default function TracesPage() {
  const [mounted, setMounted] = useState(false);
  const [hasKey, setHasKey] = useState(false);
  const [loading, setLoading] = useState(true);
  const [traces, setTraces] = useState<Record<string, unknown> | null>(null);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  useEffect(() => { if (toast) { const t = setTimeout(() => setToast(null), 3000); return () => clearTimeout(t); } }, [toast]);

  const load = useCallback(async () => {
    setMounted(true);
    const apiKey = getApiKey();
    setHasKey(!!apiKey);
    if (!apiKey) { setLoading(false); return; }
    try {
      const res = await fetch(`${getApiUrl()}/v1/traces/export`, { headers: { Authorization: `Bearer ${apiKey}` } });
      if (res.ok) setTraces(await res.json());
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  async function exportFormat(format: string) {
    try {
      const endpoint = format === "otlp" ? "/v1/traces/export" : `/v1/traces/export/${format}`;
      const res = await fetch(`${getApiUrl()}${endpoint}`, { headers: { Authorization: `Bearer ${getApiKey()}` } });
      if (!res.ok) { setToast({ message: `Export failed: ${res.status}`, type: "error" }); return; }
      const data = await res.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a"); a.href = url; a.download = `sgraal-traces-${format}.json`; a.click();
      URL.revokeObjectURL(url);
      setToast({ message: `${format.toUpperCase()} exported`, type: "success" });
    } catch { setToast({ message: "Export failed", type: "error" }); }
  }

  if (!mounted) return null;
  if (!hasKey) return (<div><h1 className="text-2xl font-bold mb-1">Trace Export</h1><p className="text-muted text-sm mb-6">OpenTelemetry trace export for your observability stack.</p><ConnectKeyState /></div>);
  if (loading) return (<div><h1 className="text-2xl font-bold mb-1">Trace Export</h1><p className="text-muted text-sm mb-6">OpenTelemetry trace export for your observability stack.</p><LoadingSkeleton rows={3} /></div>);

  const spanCount = traces ? Number((traces.spans as unknown[])?.length ?? traces.count ?? 0) : 0;
  const format = traces ? String(traces.format ?? "otlp") : "otlp";

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Trace Export</h1>
      <p className="text-muted text-sm mb-6">OpenTelemetry trace export for your observability stack.</p>

      <div className={`${CARD} mb-6`}>
        <h2 className="text-lg font-semibold mb-3">Current Traces</h2>
        <div className="flex items-center gap-6 mb-4">
          <div><p className="text-xs text-muted uppercase mb-1">Spans</p><p className="text-2xl font-bold">{spanCount}</p></div>
          <div><p className="text-xs text-muted uppercase mb-1">Format</p><p className="text-sm font-mono">{format}</p></div>
        </div>
        <div className="flex gap-3">
          <button onClick={() => exportFormat("otlp")} className="text-sm font-semibold px-4 py-1.5 rounded bg-gold text-background hover:bg-gold-dim transition">Export OTLP</button>
          <button onClick={() => exportFormat("zipkin")} className="text-sm px-4 py-1.5 rounded border border-surface-light text-muted hover:text-foreground transition">Export Zipkin</button>
          <button onClick={() => exportFormat("jaeger")} className="text-sm px-4 py-1.5 rounded border border-surface-light text-muted hover:text-foreground transition">Export Jaeger</button>
        </div>
      </div>

      <div className={CARD}>
        <p className="text-sm text-muted">Every preflight call generates an OpenTelemetry span with api_key_id, decision, omega_score, and duration_ms. Export traces to Datadog, Grafana, or any OTLP-compatible backend.</p>
      </div>

      {toast && <div style={{ position: "fixed", bottom: 24, right: 24, background: toast.type === "success" ? "#16a34a" : "#dc2626", color: "white", padding: "12px 24px", borderRadius: 8, fontSize: 14, fontWeight: 600, boxShadow: "0 4px 12px rgba(0,0,0,0.15)", zIndex: 100 }}>{toast.message}</div>}
    </div>
  );
}
