"use client";

import { useState, useEffect, useCallback } from "react";
import { getApiKey, getApiUrl } from "../lib/storage";
import { LoadingSkeleton, ConnectKeyState } from "../components/LoadingSkeleton";

interface Member { email: string; role: string; joined: string; status: string; isYou?: boolean; }
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
  const [mounted, setMounted] = useState(false);
  const [members, setMembers] = useState<Member[]>([]);
  const [hasKey, setHasKey] = useState(false);
  const [storedKey, setStoredKey] = useState("");
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("developer");
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);
  const [copied, setCopied] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [teamKeys, setTeamKeys] = useState<Array<Record<string, unknown>>>([]);
  const [newKeyName, setNewKeyName] = useState("");

  useEffect(() => { if (toast) { const t = setTimeout(() => setToast(null), 3000); return () => clearTimeout(t); } }, [toast]);

  function apiHeaders(): Record<string, string> {
    const apiKey = getApiKey();
    return { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" };
  }

  function apiUrl(): string {
    return getApiUrl();
  }

  const load = useCallback(async () => {
    setMounted(true);
    const apiKey = getApiKey();
    setHasKey(!!apiKey);
    setStoredKey(apiKey);
    if (!apiKey) { setLoading(false); return; }
    try {
      const [mRes, kRes] = await Promise.all([
        fetch(`${apiUrl()}/v1/team/members`, { headers: apiHeaders() }),
        fetch(`${apiUrl()}/v1/api-keys`, { headers: apiHeaders() }),
      ]);
      if (mRes.ok) { const d = await mRes.json(); setMembers(Array.isArray(d) ? d : d.members ?? []); }
      if (kRes.ok) { const d = await kRes.json(); setTeamKeys(Array.isArray(d) ? d : d.keys ?? []); }
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  async function sendInvite() {
    if (!inviteEmail) return;
    try {
      const res = await fetch(`${apiUrl()}/v1/team/invite`, {
        method: "POST", headers: apiHeaders(),
        body: JSON.stringify({ email: inviteEmail, role: inviteRole }),
      });
      if (!res.ok) return;
    } catch { return; }
    setMembers((prev) => [...prev, { email: inviteEmail, role: ROLES.find((r) => r.id === inviteRole)?.label ?? inviteRole, joined: "Just now", status: "Pending" }]);
    setShowInviteModal(false);
    setInviteEmail("");
    setInviteRole("developer");
    setToast({ message: `Invite sent to ${inviteEmail}`, type: "success" });
  }

  async function removeMember(email: string) {
    try {
      await fetch(`${apiUrl()}/v1/team/members/${encodeURIComponent(email)}`, {
        method: "DELETE",
        headers: apiHeaders(),
      });
    } catch {}
    setMembers((prev) => prev.filter((m) => m.email !== email));
    setToast({ message: `Removed ${email}`, type: "success" });
  }

  if (!mounted) return null;

  if (!hasKey) return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Team</h1>
      <p className="text-muted text-sm mb-6">Manage access to your Sgraal workspace.</p>
      <ConnectKeyState />
    </div>
  );

  if (loading) return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Team</h1>
      <p className="text-muted text-sm mb-6">Manage access to your Sgraal workspace.</p>
      <LoadingSkeleton rows={3} />
    </div>
  );

  return (
    <div>
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold mb-1">Team</h1>
          <p className="text-muted text-sm">Manage access to your Sgraal workspace.</p>
        </div>
        <button onClick={() => setShowInviteModal(true)} style={BTN_GOLD}>+ Invite Member</button>
      </div>

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

      {/* Team API Keys */}
      <div style={{ ...CARD, marginBottom: "24px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
          <h2 style={{ fontSize: "16px", fontWeight: 700 }}>Team API Keys</h2>
          <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
            <input value={newKeyName} onChange={(e) => setNewKeyName(e.target.value)} placeholder="Key name" style={{ ...INPUT, width: "160px", padding: "6px 10px", fontSize: "13px" }} />
            <button onClick={async () => {
              if (!newKeyName.trim()) return;
              try {
                const res = await fetch(`${apiUrl()}/v1/api-keys/generate`, { method: "POST", headers: apiHeaders(), body: JSON.stringify({ name: newKeyName.trim() }) });
                if (res.ok) {
                  const d = await res.json();
                  setTeamKeys(prev => [...prev, { id: d.id, name: d.name, key_truncated: d.key_truncated, created: d.created, active: true }]);
                  setNewKeyName("");
                  setToast({ message: `Key "${d.name}" created`, type: "success" });
                } else { setToast({ message: `Failed: ${res.status}`, type: "error" }); }
              } catch { setToast({ message: "Failed to create key", type: "error" }); }
            }} style={{ ...BTN_GOLD, padding: "6px 14px", fontSize: "13px" }}>Create Key</button>
          </div>
        </div>
        {teamKeys.length > 0 ? (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead><tr>
              {["Name", "Key", "Created", "Actions"].map(h => <th key={h} style={TH}>{h}</th>)}
            </tr></thead>
            <tbody>
              {teamKeys.map((k, i) => (
                <tr key={String(k.id ?? i)}>
                  <td style={{ ...TD, fontWeight: 600 }}>{String(k.name ?? "Key")}</td>
                  <td style={{ ...TD, fontFamily: "monospace", fontSize: "13px", color: "#c9a962" }}>{String(k.key_truncated ?? "")}</td>
                  <td style={{ ...TD, color: "#6b7280", fontSize: "13px" }}>{String(k.created ?? k.created_at ?? "")}</td>
                  <td style={TD}>
                    <button onClick={async () => {
                      try {
                        await fetch(`${apiUrl()}/v1/api-keys/${String(k.id)}`, { method: "DELETE", headers: apiHeaders() });
                        setTeamKeys(prev => prev.filter(key => key.id !== k.id));
                        setToast({ message: "Key revoked", type: "success" });
                      } catch {}
                    }} style={{ fontSize: "13px", color: "#dc2626", cursor: "pointer", background: "none", border: "none" }}>Revoke</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p style={{ fontSize: "13px", color: "#6b7280" }}>No team API keys. Create one above.</p>
        )}
      </div>

      {/* Your API Key */}
      <h2 style={{ fontSize: "20px", fontWeight: 700, marginBottom: "4px" }}>Your API Key</h2>
      <p style={{ fontSize: "13px", color: "#6b7280", marginBottom: "16px" }}>Use this key to authenticate API requests.</p>
      {hasKey ? (
        <div>
          <div style={{
            background: "rgba(201,169,98,0.08)", border: "1px solid rgba(201,169,98,0.2)",
            borderRadius: "8px", padding: "16px 20px",
            display: "flex", justifyContent: "space-between", alignItems: "center",
          }}>
            <span style={{ fontFamily: "monospace", fontSize: "15px", color: "#c9a962" }}>
              {storedKey.length > 16 ? storedKey.slice(0, 12) + "..." + storedKey.slice(-4) : storedKey}
            </span>
            {storedKey && (
              <button
                onClick={() => { try { navigator.clipboard.writeText(storedKey); } catch {} setCopied("apikey"); setTimeout(() => setCopied(null), 2000); }}
                style={{ fontSize: "13px", color: copied === "apikey" ? "#c9a962" : "#6b7280", cursor: "pointer", background: "none", border: "none", fontWeight: 500 }}
              >
                {copied === "apikey" ? "Copied!" : "Copy"}
              </button>
            )}
          </div>
          <p style={{ fontSize: "13px", color: "#6b7280", marginTop: "10px" }}>
            {"Lost your key? "}
            <a href="https://sgraal.com" style={{ color: "#c9a962" }}>Request a new one at sgraal.com &rarr;</a>
          </p>
        </div>
      ) : (
        <div style={{ ...CARD }}>
          <p style={{ fontSize: "14px", color: "#6b7280" }}>No API key connected.</p>
          <p style={{ fontSize: "13px", marginTop: "6px" }}>
            <a href="https://sgraal.com" style={{ color: "#c9a962" }}>Get your free API key at sgraal.com &rarr;</a>
          </p>
        </div>
      )}

      {/* Invite Modal */}
      {/* TODO: Add focus trap for accessibility */}
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

      {toast && (
        <div role="alert" aria-live="polite" style={{ position: "fixed", bottom: "24px", right: "24px", background: toast.type === "success" ? "#16a34a" : "#dc2626", color: "white", padding: "12px 24px", borderRadius: "8px", fontSize: "14px", fontWeight: 600, boxShadow: "0 4px 12px rgba(0,0,0,0.15)", zIndex: 100 }}>
          {toast.message}
        </div>
      )}
    </div>
  );
}
