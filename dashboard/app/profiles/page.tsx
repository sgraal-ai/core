"use client";

import { useState, useEffect, useCallback } from "react";
import { getApiKey, getApiUrl, setApiKey as saveApiKey, setApiUrl as saveApiUrl, removeApiKey, removeApiUrl, getItem, setItem, removeItem } from "../lib/storage";
import { LoadingSkeleton, ConnectKeyState } from "../components/LoadingSkeleton";

interface Profile {
  id: string;
  title: string;
  description: string;
  active: boolean;
  rules: Record<string, string>;
}

const CARD: React.CSSProperties = { background: "#ffffff", borderRadius: "8px", padding: "24px", boxShadow: "0 1px 3px rgba(0,0,0,0.06)" };
const BTN_GOLD: React.CSSProperties = { background: "#c9a962", color: "#0B0F14", fontWeight: 600, padding: "8px 20px", borderRadius: "6px", fontSize: "14px", border: "none", cursor: "pointer" };
const BTN_OUTLINE: React.CSSProperties = { background: "transparent", color: "#6b7280", fontWeight: 500, padding: "8px 16px", borderRadius: "6px", fontSize: "13px", border: "1px solid #e5e7eb", cursor: "pointer" };

export default function ProfilesPage() {
  const [mounted, setMounted] = useState(false);
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [hasKey, setHasKey] = useState(false);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  useEffect(() => { if (toast) { const t = setTimeout(() => setToast(null), 3000); return () => clearTimeout(t); } }, [toast]);

  const load = useCallback(async () => {
    setMounted(true);
    const apiKey = getApiKey();
    setHasKey(!!apiKey);
    if (!apiKey) { setLoading(false); return; }
    const apiUrl = getApiUrl();
    try {
      const res = await fetch(`${apiUrl}/v1/compliance/profiles`, { headers: { Authorization: `Bearer ${apiKey}` } });
      if (res.ok) { const d = await res.json(); if (Array.isArray(d)) setProfiles(d); else if (d.profiles) setProfiles(d.profiles); }
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  function toggleProfile(id: string) {
    setProfiles((prev) => prev.map((p) => p.id === id ? { ...p, active: !p.active } : p));
    const p = profiles.find((p) => p.id === id);
    setToast({ message: p?.active ? `${p.title} deactivated` : `${p?.title} activated`, type: "success" });
  }

  if (!mounted) return null;

  if (!hasKey) return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Compliance Profiles</h1>
      <p className="text-muted text-sm mb-6">Configure memory governance rules per domain.</p>
      <ConnectKeyState />
    </div>
  );

  if (loading) return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Compliance Profiles</h1>
      <p className="text-muted text-sm mb-6">Configure memory governance rules per domain.</p>
      <LoadingSkeleton rows={4} />
    </div>
  );

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Compliance Profiles</h1>
      <p className="text-muted text-sm mb-6">Configure memory governance rules per domain.</p>

      {/* Active Profiles Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginBottom: "40px" }}>
        {profiles.map((p) => (
          <div key={p.id} style={{ ...CARD, borderLeft: `4px solid ${p.active ? "#c9a962" : "#d1d5db"}` }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
              <h3 style={{ fontSize: "18px", fontWeight: 700, color: "#0B0F14" }}>{p.title}</h3>
              <span style={{
                background: p.active ? "#dcfce7" : "#f3f4f6",
                color: p.active ? "#16a34a" : "#6b7280",
                borderRadius: "20px", padding: "2px 10px", fontSize: "12px", fontWeight: 600,
              }}>
                {p.active ? "ACTIVE" : "INACTIVE"}
              </span>
            </div>
            <p style={{ fontSize: "14px", color: "#6b7280", lineHeight: 1.6, marginBottom: "12px" }}>{p.description}</p>
            {Object.keys(p.rules).length > 0 && (
              <div style={{ marginBottom: "16px" }}>
                {Object.entries(p.rules).map(([k, v]) => (
                  <div key={k} style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", padding: "4px 0", borderBottom: "1px solid #f5f4f0" }}>
                    <span style={{ color: "#6b7280", fontFamily: "monospace" }}>{k}</span>
                    <span style={{ color: "#0B0F14", fontWeight: 600 }}>{v}</span>
                  </div>
                ))}
              </div>
            )}
            <div style={{ display: "flex", gap: "8px" }}>
              {p.active ? (
                <>
                  <button style={BTN_OUTLINE}>Configure</button>
                  <button onClick={() => toggleProfile(p.id)} style={{ ...BTN_OUTLINE, color: "#dc2626", borderColor: "#fca5a5" }}>Deactivate</button>
                </>
              ) : (
                <button onClick={() => toggleProfile(p.id)} style={BTN_GOLD}>Activate</button>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Custom Profiles */}
      <h2 style={{ fontSize: "20px", fontWeight: 700, color: "#0B0F14", marginBottom: "16px" }}>Custom Profiles</h2>
      <div style={{ ...CARD, textAlign: "center", padding: "40px" }}>
        <p style={{ fontSize: "14px", color: "#6b7280", marginBottom: "16px" }}>No custom profiles yet. Create one to define your own memory governance rules.</p>
        <button style={BTN_GOLD}>+ Create Profile</button>
      </div>

      {toast && (
        <div style={{ position: "fixed", bottom: "24px", right: "24px", background: toast.type === "success" ? "#16a34a" : "#dc2626", color: "white", padding: "12px 24px", borderRadius: "8px", fontSize: "14px", fontWeight: 600, boxShadow: "0 4px 12px rgba(0,0,0,0.15)", zIndex: 100 }}>
          {toast.message}
        </div>
      )}
    </div>
  );
}
