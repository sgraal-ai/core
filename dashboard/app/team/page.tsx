"use client";

import { useState, useEffect, useCallback } from "react";

interface Member { email: string; role: string; joined: string; status: string; isYou?: boolean; }
interface ApiKey { id: string; name: string; key_truncated: string; created: string; last_used: string; }

const ROLES = [
  { id: "admin", label: "Admin", desc: "Full access including billing and team management" },
  { id: "developer", label: "Developer", desc: "API access, dashboard, no billing" },
  { id: "viewer", label: "Viewer", desc: "Read-only dashboard access" },
  { id: "auditor", label: "Auditor", desc: "Audit log access only" },
];

const CARD: React.CSSProperties = { background: "#ffffff", borderRadius: "8px", padding: "24px", boxShadow: "0 1px 3px rgba(0,0,0,0.06)" };
const TH: React.CSSProperties = { fontSize: "12px", color: "#6b7280", textTransform: "uppercase", padding: "8px 16px", textAlign: "left", borderBottom: "1px solid #e5e7eb", letterSpacing: "0.05em" };
const TD: React.CSSProperties = { fontSize: "14px", color: "#0B0F14", padding: "12px 16px", borderBottom: "1px solid #f5f4f0" };
const BTN_GOLD: React.CSSProperties = { background: "#c9a962", color: "#0B0F14", fontWeight: 600, padding: "8px 20px", borderRadius: "6px", fontSize: "14px", border: "none", cursor: "pointer" };
const INPUT: React.CSSProperties = { width: "100%", background: "#ffffff", border: "1px solid #e5e7eb", borderRadius: "6px", padding: "10px 14px", fontSize: "14px", color: "#0B0F14" };

export default function TeamPage() {
  const [members, setMembers] = useState<Member[]>([]);
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [hasKey, setHasKey] = useState(false);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [showNewKeyModal, setShowNewKeyModal] = useState(false);
  const [newKeyValue, setNewKeyValue] = useState("");
  const [newKeyCopied, setNewKeyCopied] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("developer");
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  useEffect(() => { if (toast) { const t = setTimeout(() => setToast(null), 3000); return () => clearTimeout(t); } }, [toast]);

  function apiHeaders(): Record<string, string> {
    const apiKey = localStorage.getItem("sgraal_api_key") ?? "";
    return { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" };
  }

  function apiUrl(): string {
    return localStorage.getItem("sgraal_api_url") ?? "https://api.sgraal.com";
  }

  const load = useCallback(async () => {
    const apiKey = localStorage.getItem("sgraal_api_key") ?? "";
    setHasKey(!!apiKey);
    if (!apiKey) { setMembers([]); setKeys([]); return; }
    try {
      const [mRes, kRes] = await Promise.all([
        fetch(`${apiUrl()}/v1/team/members`, { headers: apiHeaders() }),
        fetch(`${apiUrl()}/v1/api-keys`, { headers: apiHeaders() }),
      ]);
      if (mRes.ok) { const d = await mRes.json(); setMembers(Array.isArray(d) ? d : d.members ?? []); }
      if (kRes.ok) { const d = await kRes.json(); setKeys(Array.isArray(d) ? d : d.keys ?? []); }
    } catch {}
  }, []);

  useEffect(() => { load(); }, [load]);

  async function sendInvite() {
    if (!inviteEmail) return;
    try {
      await fetch(`${apiUrl()}/v1/team/invite`, {
        method: "POST", headers: apiHeaders(),
        body: JSON.stringify({ email: inviteEmail, role: inviteRole }),
      });
    } catch {}
    setMembers((prev) => [...prev, { email: inviteEmail, role: ROLES.find((r) => r.id === inviteRole)?.label ?? inviteRole, joined: "Just now", status: "Pending" }]);
    setShowInviteModal(false);
    setInviteEmail("");
    setInviteRole("developer");
    setToast({ message: `Invite sent to ${inviteEmail}`, type: "success" });
  }

  function removeMember(email: string) {
    setMembers((prev) => prev.filter((m) => m.email !== email));
    setToast({ message: `Removed ${email}`, type: "success" });
  }

  async function generateKey() {
    try {
      const res = await fetch(`${apiUrl()}/v1/api-keys/generate`, {
        method: "POST", headers: apiHeaders(),
        body: JSON.stringify({ name: "New Key" }),
      });
      if (res.ok) {
        const data = await res.json();
        const key = data.api_key ?? data.key ?? "";
        setNewKeyValue(key);
        setNewKeyCopied(false);
        setShowNewKeyModal(true);
        load();
      } else {
        setToast({ message: "Failed to generate key", type: "error" });
      }
    } catch {
      setToast({ message: "Failed to generate key", type: "error" });
    }
  }

  async function revokeKey(keyId: string) {
    if (!confirm("Are you sure? This cannot be undone.")) return;
    try {
      const res = await fetch(`${apiUrl()}/v1/api-keys/${keyId}`, {
        method: "DELETE", headers: apiHeaders(),
      });
      if (res.ok) {
        setKeys((prev) => prev.filter((k) => k.id !== keyId));
        setToast({ message: "Key revoked", type: "success" });
      } else {
        setToast({ message: "Failed to revoke key", type: "error" });
      }
    } catch {
      setToast({ message: "Failed to revoke key", type: "error" });
    }
  }

  function copyKey(keyTruncated: string) {
    const full = localStorage.getItem("sgraal_api_key") ?? keyTruncated;
    navigator.clipboard.writeText(full);
    setCopied(keyTruncated);
    setTimeout(() => setCopied(null), 2000);
  }

  function copyNewKey() {
    navigator.clipboard.writeText(newKeyValue);
    setNewKeyCopied(true);
    setTimeout(() => setNewKeyCopied(false), 2000);
  }

  const empty = !hasKey;

  return (
    <div>
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold mb-1">Team</h1>
          <p className="text-muted text-sm">Manage access to your Sgraal workspace.</p>
        </div>
        <button onClick={() => setShowInviteModal(true)} style={BTN_GOLD}>+ Invite Member</button>
      </div>

      {empty && (
        <div className="bg-gold/10 border border-gold/30 rounded-lg px-4 py-3 mb-6 text-sm text-gold">
          <a href="/settings" className="underline">Enter your API key</a> to manage your team.
        </div>
      )}

      {/* Members Table */}
      <div style={{ ...CARD, padding: 0, overflow: "hidden", marginBottom: "24px" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              {["Member", "Role", "Joined", "Status", "Actions"].map((h) => <th key={h} style={TH}>{h}</th>)}
            </tr>
          </thead>
          <tbody>
            {members.length === 0 && (
              <tr><td colSpan={5} style={{ ...TD, textAlign: "center", color: "#6b7280" }}>No team members loaded. Connect your API key to see your team.</td></tr>
            )}
            {members.map((m) => (
              <tr key={m.email}>
                <td style={{ ...TD, fontFamily: "monospace", fontWeight: 600 }}>{m.email}</td>
                <td style={TD}>{m.role}</td>
                <td style={{ ...TD, color: "#6b7280", fontSize: "13px" }}>{m.joined}</td>
                <td style={TD}>
                  <span style={{
                    background: m.status === "Active" ? "#dcfce7" : "#fef9c3",
                    color: m.status === "Active" ? "#16a34a" : "#a16207",
                    borderRadius: "20px", padding: "2px 10px", fontSize: "12px", fontWeight: 600,
                  }}>
                    {m.status}
                  </span>
                </td>
                <td style={TD}>
                  {m.isYou ? (
                    <span style={{ fontSize: "13px", color: "#6b7280" }}>(you)</span>
                  ) : (
                    <button onClick={() => removeMember(m.email)} style={{ fontSize: "13px", color: "#dc2626", cursor: "pointer", background: "none", border: "none" }}>Remove</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Roles Info Box */}
      <div style={{ ...CARD, marginBottom: "32px", background: "#faf9f6" }}>
        <h3 style={{ fontSize: "14px", fontWeight: 700, marginBottom: "12px" }}>Role Permissions</h3>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
          {ROLES.map((r) => (
            <div key={r.id} style={{ fontSize: "13px" }}>
              <span style={{ fontWeight: 600, color: "#0B0F14" }}>{r.label}: </span>
              <span style={{ color: "#6b7280" }}>{r.desc}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Pending Invites */}
      {members.some((m) => m.status === "Pending") ? (
        <div style={{ ...CARD, marginBottom: "32px" }}>
          <h2 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "12px" }}>Pending Invites</h2>
          {members.filter((m) => m.status === "Pending").map((m) => (
            <div key={m.email} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #f5f4f0", fontSize: "14px" }}>
              <span style={{ fontFamily: "monospace" }}>{m.email}</span>
              <span style={{ color: "#6b7280" }}>{m.role} — Pending</span>
            </div>
          ))}
        </div>
      ) : (
        <div style={{ ...CARD, marginBottom: "32px" }}>
          <h2 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "8px" }}>Pending Invites</h2>
          <p style={{ fontSize: "13px", color: "#6b7280" }}>No pending invites.</p>
        </div>
      )}

      {/* API Keys */}
      <h2 style={{ fontSize: "20px", fontWeight: 700, marginBottom: "16px" }}>API Keys</h2>
      <div style={{ ...CARD, padding: 0, overflow: "hidden", marginBottom: "16px" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              {["Name", "Key", "Created", "Last Used", "Actions"].map((h) => <th key={h} style={TH}>{h}</th>)}
            </tr>
          </thead>
          <tbody>
            {keys.length === 0 && (
              <tr><td colSpan={5} style={{ ...TD, textAlign: "center", color: "#6b7280" }}>No API keys loaded. Connect your API key or generate a new one.</td></tr>
            )}
            {keys.map((k) => (
              <tr key={k.id}>
                <td style={{ ...TD, fontWeight: 600 }}>{k.name}</td>
                <td style={{ ...TD, fontFamily: "monospace", fontSize: "13px", color: "#c9a962" }}>{k.key_truncated}</td>
                <td style={{ ...TD, color: "#6b7280", fontSize: "13px" }}>{k.created}</td>
                <td style={{ ...TD, color: "#6b7280", fontSize: "13px" }}>{k.last_used}</td>
                <td style={TD}>
                  <div style={{ display: "flex", gap: "8px" }}>
                    <button onClick={() => copyKey(k.key_truncated)} style={{ fontSize: "13px", color: "#6b7280", cursor: "pointer", background: "none", border: "none" }}>
                      {copied === k.key_truncated ? "Copied!" : "Copy"}
                    </button>
                    <button onClick={() => revokeKey(k.id)} style={{ fontSize: "13px", color: "#dc2626", cursor: "pointer", background: "none", border: "none" }}>Revoke</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <button onClick={generateKey} style={BTN_GOLD}>+ Generate New Key</button>

      {/* Invite Modal */}
      {showInviteModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }} onClick={() => setShowInviteModal(false)}>
          <div style={{ background: "#ffffff", borderRadius: "12px", padding: "32px", width: "440px", boxShadow: "0 8px 32px rgba(0,0,0,0.15)" }} onClick={(e) => e.stopPropagation()}>
            <h3 style={{ fontSize: "20px", fontWeight: 700, marginBottom: "24px" }}>Invite team member</h3>
            <div style={{ marginBottom: "16px" }}>
              <label style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", display: "block", marginBottom: "6px" }}>Email Address</label>
              <input value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} placeholder="name@company.com" style={INPUT} />
            </div>
            <div style={{ marginBottom: "24px" }}>
              <label style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", display: "block", marginBottom: "6px" }}>Role</label>
              <select value={inviteRole} onChange={(e) => setInviteRole(e.target.value)} style={{ ...INPUT, cursor: "pointer" }}>
                {ROLES.map((r) => <option key={r.id} value={r.id}>{r.label}</option>)}
              </select>
            </div>
            <div style={{ display: "flex", gap: "12px", justifyContent: "flex-end" }}>
              <button onClick={() => setShowInviteModal(false)} style={{ padding: "8px 20px", borderRadius: "6px", border: "1px solid #e5e7eb", fontSize: "14px", cursor: "pointer", background: "#ffffff" }}>Cancel</button>
              <button onClick={sendInvite} style={BTN_GOLD}>Send Invite</button>
            </div>
          </div>
        </div>
      )}

      {/* New Key Modal */}
      {showNewKeyModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }}>
          <div style={{ background: "#ffffff", borderRadius: "12px", padding: "32px", width: "520px", boxShadow: "0 8px 32px rgba(0,0,0,0.15)" }}>
            <h3 style={{ fontSize: "20px", fontWeight: 700, marginBottom: "8px" }}>Your new API key</h3>
            <p style={{ fontSize: "14px", color: "#dc2626", fontWeight: 600, marginBottom: "20px" }}>Copy this key now — it won{"'"}t be shown again.</p>
            <div style={{
              background: "rgba(201,169,98,0.08)", border: "1px solid rgba(201,169,98,0.2)",
              borderRadius: "8px", padding: "16px", fontFamily: "monospace", fontSize: "14px",
              color: "#c9a962", wordBreak: "break-all", marginBottom: "20px",
            }}>
              {newKeyValue}
            </div>
            <div style={{ display: "flex", gap: "12px", justifyContent: "flex-end" }}>
              <button onClick={copyNewKey} style={{ ...BTN_GOLD, background: newKeyCopied ? "#16a34a" : "#c9a962", color: newKeyCopied ? "#ffffff" : "#0B0F14" }}>
                {newKeyCopied ? "Copied!" : "Copy Key"}
              </button>
              <button onClick={() => { setShowNewKeyModal(false); setNewKeyValue(""); }} style={{ padding: "8px 20px", borderRadius: "6px", border: "1px solid #e5e7eb", fontSize: "14px", cursor: "pointer", background: "#ffffff" }}>Done</button>
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
