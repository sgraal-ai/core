export default function Page() {
  return (<div className="min-h-screen bg-[#0B0F14] text-white px-4 py-12 max-w-4xl mx-auto">
    <h1 className="text-3xl font-bold mb-4">Sgraal Memory Risk Score (SMRS)</h1>
    <p className="text-gray-400 mb-8">The standardized score for AI agent memory reliability.</p>
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 text-sm text-gray-300 space-y-2">
      <p>Range: 0 (perfect) to 100 (critical risk)</p>
      <p>USE_MEMORY: 0-25 | WARN: 25-50 | ASK_USER: 50-75 | BLOCK: 75-100</p>
      <p>Computed from 10+ weighted risk components with Weibull decay.</p>
    </div>
  </div>);
}
