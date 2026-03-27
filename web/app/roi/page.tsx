"use client";
import { useState, useMemo } from "react";

const DOMAINS: Record<string, { multiplier: number; rationale: string }> = {
  general: { multiplier: 1.0, rationale: "Baseline operational cost" },
  fintech: { multiplier: 3.5, rationale: "Regulatory fines, trade reversal costs, compliance penalties" },
  healthcare: { multiplier: 5.0, rationale: "Liability exposure, patient safety incidents, HIPAA fines" },
  legal: { multiplier: 4.0, rationale: "Malpractice risk, compliance violations, contract damages" },
};

export default function ROIPage() {
  const [calls, setCalls] = useState(100000);
  const [decisions, setDecisions] = useState(5000);
  const [memPct, setMemPct] = useState(60);
  const [costWrong, setCostWrong] = useState(50);
  const [domain, setDomain] = useState("general");

  const roi = useMemo(() => {
    const mult = DOMAINS[domain].multiplier;
    const memDecisions = decisions * 30 * (memPct / 100);
    const failRate = 0.03;
    const prevented = Math.round(memDecisions * failRate);
    const savings = prevented * costWrong * mult;
    const sgraalCost = Math.max(0, (calls - 10000)) * 0.001;
    const roiMultiple = sgraalCost > 0 ? savings / sgraalCost : Infinity;
    const paybackDays = sgraalCost > 0 ? Math.ceil(sgraalCost / (savings / 30)) : 0;
    return { prevented, savings, sgraalCost, roiMultiple, paybackDays };
  }, [calls, decisions, memPct, costWrong, domain]);

  const shareUrl = typeof window !== "undefined"
    ? `${window.location.origin}/roi?calls=${calls}&decisions=${decisions}&mem=${memPct}&cost=${costWrong}&domain=${domain}` : "";

  return (
    <div className="min-h-screen bg-[#0B0F14] text-white px-4 py-12 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-2">ROI Calculator</h1>
      <p className="text-gray-400 text-sm mb-8">Estimate your return on investment with Sgraal memory governance.</p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-10">
        <div className="space-y-6">
          <div>
            <label className="text-xs text-gray-500 block mb-1">Monthly API calls: {calls.toLocaleString()}</label>
            <input type="range" min={1000} max={10000000} step={1000} value={calls} onChange={e => setCalls(+e.target.value)} className="w-full accent-[#C9A962]" />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Avg agent decisions/day: {decisions.toLocaleString()}</label>
            <input type="range" min={100} max={100000} step={100} value={decisions} onChange={e => setDecisions(+e.target.value)} className="w-full accent-[#C9A962]" />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">% decisions involving memory: {memPct}%</label>
            <input type="range" min={10} max={100} step={5} value={memPct} onChange={e => setMemPct(+e.target.value)} className="w-full accent-[#C9A962]" />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Avg cost of wrong decision ($)</label>
            <input type="number" min={1} max={100000} value={costWrong} onChange={e => setCostWrong(+e.target.value)} className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm w-full" />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Domain</label>
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(DOMAINS).map(([k, v]) => (
                <button key={k} onClick={() => setDomain(k)} title={v.rationale}
                  className={`text-xs px-3 py-2 rounded border ${domain === k ? "bg-[#C9A962] text-black border-[#C9A962]" : "bg-gray-800 border-gray-700 text-gray-400"}`}>
                  {k} <span className="text-[10px]">{v.multiplier}x</span>
                </button>
              ))}
            </div>
            <p className="text-[10px] text-gray-600 mt-1">{DOMAINS[domain].rationale}</p>
          </div>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-4">
          <h2 className="text-sm font-semibold text-gray-400 mb-4">Monthly Estimate</h2>
          <div className="flex justify-between items-center">
            <span className="text-gray-400 text-sm">Failures prevented</span>
            <span className="text-2xl font-bold text-green-400">{roi.prevented.toLocaleString()}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-gray-400 text-sm">Cost savings</span>
            <span className="text-2xl font-bold text-[#C9A962]">${roi.savings.toLocaleString()}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-gray-400 text-sm">Sgraal cost</span>
            <span className="text-lg font-mono text-gray-300">${roi.sgraalCost.toLocaleString()}</span>
          </div>
          <hr className="border-gray-800" />
          <div className="flex justify-between items-center">
            <span className="text-gray-400 text-sm">ROI multiple</span>
            <span className="text-3xl font-bold text-green-400">{roi.roiMultiple === Infinity ? "∞" : `${roi.roiMultiple.toFixed(0)}x`}</span>
          </div>
          <div className="text-center mt-4 p-3 bg-[#C9A962]/10 rounded-lg">
            <p className="text-[#C9A962] text-sm font-semibold">
              At your scale, Sgraal pays for itself in {roi.paybackDays === 0 ? "< 1" : roi.paybackDays} days.
            </p>
          </div>
          <div className="flex gap-2 mt-4">
            <button onClick={() => navigator.clipboard.writeText(shareUrl)} className="text-xs bg-gray-800 border border-gray-700 px-3 py-1.5 rounded hover:bg-gray-700">
              Share ROI report
            </button>
            <button onClick={() => window.print()} className="text-xs bg-gray-800 border border-gray-700 px-3 py-1.5 rounded hover:bg-gray-700">
              Export PDF
            </button>
          </div>
        </div>
      </div>

      <div className="text-center">
        <a href="/#signup" className="bg-[#C9A962] text-black font-semibold px-8 py-3 rounded-lg hover:bg-[#d4b872] transition">
          Start saving → Get API Key
        </a>
      </div>
    </div>
  );
}
