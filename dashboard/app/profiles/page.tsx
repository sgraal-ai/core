"use client";
import { useState } from "react";

export default function ProfilesPage() {
  const [name, setName] = useState("");
  const [domain, setDomain] = useState("general");
  const [warn, setWarn] = useState(40);
  const [block, setBlock] = useState(80);
  const [profiles, setProfiles] = useState<Array<{ name: string; domain: string; warn: number; block: number }>>([]);
  const [msg, setMsg] = useState("");

  const create = () => {
    if (!name) return;
    setProfiles([...profiles, { name, domain, warn, block }]);
    setMsg(`Profile "${name}" created`);
    setName("");
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Domain Profiles</h1>
      <p className="text-muted text-sm mb-6">Create custom scoring profiles per domain with tunable thresholds.</p>

      <div className="bg-surface border border-surface-light rounded-xl p-5 mb-6">
        <h2 className="text-sm font-semibold mb-3">New Profile</h2>
        <div className="grid grid-cols-2 gap-3 mb-3">
          <input value={name} onChange={e => setName(e.target.value)} placeholder="Profile name" className="bg-background border border-surface-light rounded px-3 py-2 text-sm" />
          <select value={domain} onChange={e => setDomain(e.target.value)} className="bg-background border border-surface-light rounded px-3 py-2 text-sm">
            {["general", "fintech", "medical", "legal"].map(d => <option key={d} value={d}>{d}</option>)}
          </select>
        </div>
        <div className="grid grid-cols-2 gap-3 mb-3">
          <div>
            <label className="text-xs text-muted">WARN threshold: {warn}</label>
            <input type="range" min={10} max={90} value={warn} onChange={e => setWarn(+e.target.value)} className="w-full accent-yellow-400" />
          </div>
          <div>
            <label className="text-xs text-muted">BLOCK threshold: {block}</label>
            <input type="range" min={20} max={100} value={block} onChange={e => setBlock(+e.target.value)} className="w-full accent-red-400" />
          </div>
        </div>
        <button onClick={create} className="bg-gold text-background font-semibold px-4 py-2 rounded text-sm">Create Profile</button>
        {msg && <p className="text-xs text-green-400 mt-2">{msg}</p>}
      </div>

      <div className="bg-surface border border-surface-light rounded-xl p-5">
        <h2 className="text-sm font-semibold mb-3">Your Profiles ({profiles.length})</h2>
        {profiles.map((p, i) => (
          <div key={i} className="flex justify-between items-center py-2 border-b border-surface-light last:border-0">
            <span className="text-sm font-semibold">{p.name}</span>
            <div className="flex gap-3 text-xs text-muted">
              <span>{p.domain}</span>
              <span className="text-yellow-400">W:{p.warn}</span>
              <span className="text-red-400">B:{p.block}</span>
            </div>
          </div>
        ))}
        {profiles.length === 0 && <p className="text-xs text-muted">No profiles yet. Create one above to customize scoring.</p>}
      </div>
    </div>
  );
}
