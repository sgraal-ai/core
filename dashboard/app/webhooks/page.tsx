"use client";

import { useState, useEffect, useCallback } from "react";
import { getApiKey, getApiUrl } from "../lib/storage";
import { LoadingSkeleton, ConnectKeyState } from "../components/LoadingSkeleton";

interface Webhook { id: string; url: string; events: string[]; active: boolean; last_triggered: string; }

const ALL_EVENTS = ["decision.block", "decision.warn", "decision.ask_user", "memory.healed", "sleeper.detected", "poisoning.suspected", "atc.conflict"];
const DEFAULT_CHECKED = ["decision.block", "decision.warn"];

const CARD: React.CSSProperties = { background: "#ffffff", borderRadius: "8px", padding: "24px", boxShadow: "0 1px 3px rgba(0,0,0,0.06)" };
const TH: React.CSSProperties = { fontSize: "12px", color: "#6b7280", textTransform: "uppercase", padding: "8px 16px", textAlign: "left", borderBottom: "1px solid #e5e7eb", letterSpacing: "0.05em" };
const TD: React.CSSProperties = { fontSize: "14px", color: "#0B0F14", padding: "12px 16px", borderBottom: "1px solid #f5f4f0" };
const BTN_GOLD: React.CSSProperties = { background: "#c9a962", color: "#0B0F14", fontWeight: 600, padding: "8px 20px", borderRadius: "6px", fontSize: "14px", border: "none", cursor: "pointer" };

export default function WebhooksPage() {
  const [mounted, setMounted] = useState(false);
  const [hooks, setHooks] = useState<Webhook[]>([]);
  const [hasKey, setHasKey] = useState(false);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [newUrl, setNewUrl] = useState("");
  const [newEvents, setNewEvents] = useState<string[]>(DEFAULT_CHECKED);
  const [newSecret, setNewSecret] = useState("");
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  useEffect(() => { if (toast) { const t = setTimeout(() => setToast(null), 3000); return () => clearTimeout(t); } }, [toast]);

  const load = useCallback(async () => {
    setMounted(true);
    const apiKey = getApiKey();
    setHasKey(!!apiKey);
    if (!apiKey) { setLoading(false); return; }
    const apiUrl = getApiUrl();
    try {
      const res = await fetch(`${apiUrl}/v1/webhooks`, { headers: { Authorization: `Bearer ${apiKey}` } });
      if (res.ok) { const d = await res.json(); if (Array.isArray(d)) setHooks(d); else if (d.webhooks) setHooks(d.webhooks); }
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  function toggleEvent(ev: string) {
    setNewEvents((prev) => prev.includes(ev) ? prev.filter((e) => e !== ev) : [...prev, ev]);
  }

  async function saveWebhook() {
    if (!newUrl.startsWith("https://")) { setToast({ message: "URL must start with https://", type: "error" }); return; }
    const apiKey = getApiKey();
    if (apiKey) {
      const apiUrl = getApiUrl();
      try {
        const res = await fetch(`${apiUrl}/v1/webhooks/learning-events`, {
          method: "POST",
          headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
          body: JSON.stringify({ url: newUrl, events: newEvents, secret: newSecret || undefined }),
        });
        if (!res.ok) return;
      } catch { return; }
    }
    setHooks((prev) => [...prev, { id: `wh_${Date.now()}`, url: newUrl, events: newEvents, active: true, last_triggered: "Never" }]);
    setShowModal(false);
    setNewUrl("");
    setNewEvents(DEFAULT_CHECKED);
    setNewSecret("");
    setToast({ message: "Webhook added", type: "success" });
  }

  async function deleteWebhook(id: string) {
    const apiKey = getApiKey();
    if (apiKey) {
      const apiUrl = getApiUrl();
      try { await fetch(`${apiUrl}/v1/webhooks/${id}`, { method: "DELETE", headers: { Authorization: `Bearer ${apiKey}` } }); } catch {}
    }
    setHooks((prev) => prev.filter((h) => h.id !== id));
    setToast({ message: "Webhook deleted", type: "success" });
  }

  const INPUT: React.CSSProperties = { width: "100%", background: "#ffffff", border: "1px solid #e5e7eb", borderRadius: "6px", padding: "10px 14px", fontSize: "14px", color: "#0B0F14" };

  if (!mounted) return null;

  if (!hasKey) return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Webhooks</h1>
      <p className="text-muted text-sm mb-6">Receive real-time events when Sgraal makes decisions.</p>
      <ConnectKeyState />
    </div>
  );

  if (loading) return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Webhooks</h1>
      <p className="text-muted text-sm mb-6">Receive real-time events when Sgraal makes decisions.</p>
      <LoadingSkeleton rows={3} />
    </div>
  );

  return (
    <div>
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold mb-1">Webhooks</h1>
          <p className="text-muted text-sm">Receive real-time events when Sgraal makes decisions.</p>
        </div>
        <button onClick={() => setShowModal(true)} style={BTN_GOLD}>+ Add Webhook</button>
      </div>

      {/* Active Webhooks */}
      <div style={{ ...CARD, marginBottom: "32px", padding: 0, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              {["URL", "Events", "Status", "Last Triggered", "Actions"].map((h) => <th key={h} style={TH}>{h}</th>)}
            </tr>
          </thead>
          <tbody>
            {hooks.map((h) => (
              <tr key={h.id}>
                <td style={{ ...TD, fontFamily: "monospace", fontSize: "13px" }}>{h.url}</td>
                <td style={TD}>
                  <div style={{ display: "flex", gap: "4px", flexWrap: "wrap" }}>
                    {h.events.map((e) => (
                      <span key={e} style={{ background: "rgba(201,169,98,0.1)", color: "#c9a962", borderRadius: "20px", padding: "2px 8px", fontSize: "11px" }}>{e.replace("decision.", "")}</span>
                    ))}
                  </div>
                </td>
                <td style={TD}>
                  <span style={{ background: h.active ? "#dcfce7" : "#fee2e2", color: h.active ? "#16a34a" : "#dc2626", borderRadius: "20px", padding: "2px 10px", fontSize: "12px", fontWeight: 600 }}>
                    {h.active ? "Active" : "Inactive"}
                  </span>
                </td>
                <td style={{ ...TD, color: "#6b7280", fontSize: "13px" }}>{h.last_triggered}</td>
                <td style={TD}>
                  <div style={{ display: "flex", gap: "8px" }}>
                    <button onClick={() => deleteWebhook(h.id)} style={{ fontSize: "13px", color: "#dc2626", cursor: "pointer", background: "none", border: "none" }}>Delete</button>
                  </div>
                </td>
              </tr>
            ))}
            {hooks.length === 0 && (
              <tr><td colSpan={5} style={{ ...TD, textAlign: "center", color: "#6b7280" }}>No webhooks configured. Click &quot;+ Add Webhook&quot; to get started.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Delivery Log */}
      <div style={CARD}>
        <h2 style={{ fontSize: "18px", fontWeight: 700, marginBottom: "12px" }}>Delivery Log</h2>
        <p className="text-sm text-muted">Delivery logs available via API — <code className="text-gold font-mono text-xs">GET /v1/webhooks/delivery-log</code></p>
      </div>

      {/* Add Webhook Modal */}
      {showModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }} onClick={() => setShowModal(false)}>
          <div style={{ background: "#ffffff", borderRadius: "12px", padding: "32px", width: "480px", maxHeight: "90vh", overflowY: "auto", boxShadow: "0 8px 32px rgba(0,0,0,0.15)" }} onClick={(e) => e.stopPropagation()}>
            <h3 style={{ fontSize: "20px", fontWeight: 700, marginBottom: "24px" }}>Add Webhook</h3>

            <div style={{ marginBottom: "16px" }}>
              <label style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", display: "block", marginBottom: "6px" }}>Endpoint URL</label>
              <input value={newUrl} onChange={(e) => setNewUrl(e.target.value)} placeholder="https://..." style={INPUT} />
            </div>

            <div style={{ marginBottom: "16px" }}>
              <label style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", display: "block", marginBottom: "8px" }}>Events to Subscribe</label>
              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                {ALL_EVENTS.map((ev) => (
                  <label key={ev} style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "14px", cursor: "pointer" }}>
                    <input type="checkbox" checked={newEvents.includes(ev)} onChange={() => toggleEvent(ev)} style={{ accentColor: "#c9a962" }} />
                    <span style={{ fontFamily: "monospace", fontSize: "13px" }}>{ev}</span>
                  </label>
                ))}
              </div>
            </div>

            <div style={{ marginBottom: "24px" }}>
              <label style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", display: "block", marginBottom: "6px" }}>Secret (optional, for HMAC signature)</label>
              <input value={newSecret} onChange={(e) => setNewSecret(e.target.value)} placeholder="whsec_..." style={INPUT} />
            </div>

            <div style={{ display: "flex", gap: "12px", justifyContent: "flex-end" }}>
              <button onClick={() => setShowModal(false)} style={{ padding: "8px 20px", borderRadius: "6px", border: "1px solid #e5e7eb", fontSize: "14px", cursor: "pointer", background: "#ffffff" }}>Cancel</button>
              <button onClick={saveWebhook} style={BTN_GOLD}>Save</button>
            </div>
          </div>
        </div>
      )}

      {toast && (
        <div style={{ position: "fixed", bottom: "24px", right: "24px", background: toast.type === "success" ? "#16a34a" : "#dc2626", color: "white", padding: "12px 24px", borderRadius: "8px", fontSize: "14px", fontWeight: 600, boxShadow: "0 4px 12px rgba(0,0,0,0.15)", zIndex: 100 }}>
          {toast.message}
        </div>
      )}
    </div>
  );
}
