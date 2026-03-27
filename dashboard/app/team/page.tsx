"use client";
import { useState } from "react";

const ROLES = ["admin", "developer", "viewer", "auditor"] as const;

export default function TeamPage() {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<typeof ROLES[number]>("developer");
  const [members, setMembers] = useState<Array<{ email: string; role: string; status: string }>>([]);
  const [msg, setMsg] = useState("");

  const invite = () => {
    if (!email) return;
    setMembers([...members, { email, role, status: "pending" }]);
    setMsg(`Invited ${email} as ${role}`);
    setEmail("");
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Team Management</h1>
      <p className="text-muted text-sm mb-6">Manage team members and RBAC roles.</p>

      <div className="bg-surface border border-surface-light rounded-xl p-5 mb-6">
        <h2 className="text-sm font-semibold mb-3">Invite Member</h2>
        <div className="flex gap-3">
          <input value={email} onChange={e => setEmail(e.target.value)} placeholder="email@company.com" className="bg-background border border-surface-light rounded px-3 py-2 text-sm flex-1" />
          <select value={role} onChange={e => setRole(e.target.value as typeof ROLES[number])} className="bg-background border border-surface-light rounded px-3 py-2 text-sm">
            {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
          </select>
          <button onClick={invite} className="bg-gold text-background font-semibold px-4 py-2 rounded text-sm">Invite</button>
        </div>
        {msg && <p className="text-xs text-green-400 mt-2">{msg}</p>}
      </div>

      <div className="bg-surface border border-surface-light rounded-xl p-5">
        <h2 className="text-sm font-semibold mb-3">Members ({members.length})</h2>
        <div className="text-xs text-muted mb-2">admin: all | developer: preflight+heal | viewer: read-only | auditor: audit logs</div>
        {members.map((m, i) => (
          <div key={i} className="flex justify-between items-center py-2 border-b border-surface-light last:border-0">
            <span className="text-sm font-mono">{m.email}</span>
            <div className="flex gap-2 items-center">
              <span className="text-xs text-muted">{m.role}</span>
              <span className={`text-xs px-2 py-0.5 rounded ${m.status === "active" ? "bg-green-400/10 text-green-400" : "bg-yellow-400/10 text-yellow-400"}`}>{m.status}</span>
            </div>
          </div>
        ))}
        {members.length === 0 && <p className="text-xs text-muted">No members yet. Invite your team above.</p>}
      </div>
    </div>
  );
}
