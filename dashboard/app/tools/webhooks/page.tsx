"use client";

import { useState, useEffect, useCallback } from "react";
import { getApiKey, getApiUrl } from "../../lib/storage";
import { LoadingSkeleton, ConnectKeyState } from "../../components/LoadingSkeleton";

const CARD = "bg-surface border border-surface-light rounded-xl p-5";
const EVENTS = ["outcome", "heal", "block", "warn", "ask_user", "sleeper_detected"];

interface Webhook { id?: string; url: string; events: string[]; created_at?: string; }

export default function ToolsWebhooksPage() {
  const [mounted, setMounted] = useState(false);
  const [hasKey, setHasKey] = useState(false);
  const [loading, setLoading] = useState(true);
  const [hooks, setHooks] = useState<Webhook[]>([]);
  const [url, setUrl] = useState("");
  const [selectedEvents, setSelectedEvents] = useState<string[]>(["outcome", "heal", "block"]);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  useEffect(() => { if (toast) { const t = setTimeout(() => setToast(null), 3000); return () => clearTimeout(t); } }, [toast]);

  const load = useCallback(async () => {
    setMounted(true);
    const apiKey = getApiKey();
    setHasKey(!!apiKey);
    if (!apiKey) { setLoading(false); return; }
    try {
      const res = await fetch(`${getApiUrl()}/v1/webhooks`, { headers: { Authorization: `Bearer ${apiKey}` } });
      if (res.ok) { const d = await res.json(); setHooks(Array.isArray(d) ? d : d.webhooks ?? []); }
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  async function register() {
    if (!url.startsWith("https://")) { setToast({ message: "URL must start with https://", type: "error" }); return; }
    try {
      const res = await fetch(`${getApiUrl()}/v1/webhooks/learning-events`, {
        method: "POST",
        headers: { Authorization: `Bearer ${getApiKey()}`, "Content-Type": "application/json" },
        body: JSON.stringify({ url, events: selectedEvents }),
      });
      if (res.ok) {
        const data = await res.json();
        setHooks(prev => [...prev, { id: data.id, url, events: selectedEvents, created_at: new Date().toISOString() }]);
        setToast({ message: "Webhook registered", type: "success" }); setUrl("");
      }
      else setToast({ message: `Failed: ${res.status}`, type: "error" });
    } catch { setToast({ message: "Registration failed", type: "error" }); }
  }

  if (!mounted) return null;
  if (!hasKey) return (<div><h1 className="text-2xl font-bold mb-1">Learning Webhooks</h1><p className="text-muted text-sm mb-6">Receive real-time notifications when Sgraal blocks, heals, or records an outcome.</p><ConnectKeyState /></div>);
  if (loading) return (<div><h1 className="text-2xl font-bold mb-1">Learning Webhooks</h1><p className="text-muted text-sm mb-6">Receive real-time notifications when Sgraal blocks, heals, or records an outcome.</p><LoadingSkeleton rows={3} /></div>);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Learning Webhooks</h1>
      <p className="text-muted text-sm mb-6">Receive real-time notifications when Sgraal blocks, heals, or records an outcome.</p>

      <div className={`${CARD} mb-6`}>
        <h2 className="text-lg font-semibold mb-3">Register Webhook</h2>
        <div className="flex gap-3 mb-3">
          <input value={url} onChange={e => setUrl(e.target.value)} placeholder="https://your-server.com/webhook" className="flex-1 bg-background border border-surface-light rounded-lg px-4 py-2 text-sm font-mono text-foreground placeholder:text-muted focus:outline-none focus:border-gold transition" />
          <button onClick={register} className="text-sm font-semibold px-4 py-2 rounded bg-gold text-background hover:bg-gold-dim transition">Register</button>
        </div>
        <div className="flex flex-wrap gap-3">
          {EVENTS.map(ev => (
            <label key={ev} className="flex items-center gap-2 text-sm cursor-pointer">
              <input type="checkbox" checked={selectedEvents.includes(ev)} onChange={() => setSelectedEvents(prev => prev.includes(ev) ? prev.filter(e => e !== ev) : [...prev, ev])} style={{ accentColor: "#c9a962" }} />
              <span className="font-mono text-xs">{ev}</span>
            </label>
          ))}
        </div>
      </div>

      <div className={CARD}>
        <h2 className="text-lg font-semibold mb-3">Registered Webhooks</h2>
        {hooks.length > 0 ? hooks.map((h, i) => (
          <div key={i} className="flex justify-between items-center py-2 border-b border-surface-light last:border-0 text-sm">
            <div>
              <p className="font-mono text-xs">{h.url}</p>
              <div className="flex gap-1 mt-1">{(h.events ?? []).map(e => <span key={e} className="text-xs bg-gold/10 text-gold px-2 py-0.5 rounded">{e}</span>)}</div>
            </div>
            {h.created_at && <span className="text-xs text-muted">{h.created_at}</span>}
          </div>
        )) : <p className="text-sm text-muted">No webhooks registered yet.</p>}
      </div>

      {toast && <div style={{ position: "fixed", bottom: 24, right: 24, background: toast.type === "success" ? "#16a34a" : "#dc2626", color: "white", padding: "12px 24px", borderRadius: 8, fontSize: 14, fontWeight: 600, boxShadow: "0 4px 12px rgba(0,0,0,0.15)", zIndex: 100 }}>{toast.message}</div>}
    </div>
  );
}
