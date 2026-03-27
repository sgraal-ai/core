"use client";
import { useState } from "react";
const FUNCTIONS = ["weibull", "gompertz", "power_law", "exponential"] as const;
export default function DecayConfigPage() {
  const [memType, setMemType] = useState("semantic");
  const [fn, setFn] = useState<typeof FUNCTIONS[number]>("weibull");
  const [lambda, setLambda] = useState(0.1);
  const [k, setK] = useState(1.5);
  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Custom Decay Functions</h1>
      <p className="text-muted text-sm mb-6">Configure per-memory-type decay curves.</p>
      <div className="bg-surface border border-surface-light rounded-xl p-5 grid grid-cols-2 gap-4">
        <div>
          <label className="text-xs text-muted block mb-1">Memory Type</label>
          <select value={memType} onChange={e => setMemType(e.target.value)} className="bg-background border border-surface-light rounded px-3 py-2 text-sm w-full">
            {["semantic","episodic","tool_state","preference","policy","identity"].map(t => <option key={t}>{t}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs text-muted block mb-1">Decay Function</label>
          <select value={fn} onChange={e => setFn(e.target.value as typeof FUNCTIONS[number])} className="bg-background border border-surface-light rounded px-3 py-2 text-sm w-full">
            {FUNCTIONS.map(f => <option key={f}>{f}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs text-muted block mb-1">Lambda: {lambda}</label>
          <input type="range" min={0.01} max={1} step={0.01} value={lambda} onChange={e => setLambda(+e.target.value)} className="w-full accent-gold" />
        </div>
        <div>
          <label className="text-xs text-muted block mb-1">k: {k}</label>
          <input type="range" min={0.1} max={5} step={0.1} value={k} onChange={e => setK(+e.target.value)} className="w-full accent-gold" />
        </div>
      </div>
      <button className="mt-4 bg-gold text-background font-semibold px-4 py-2 rounded text-sm">Save Config</button>
    </div>
  );
}
